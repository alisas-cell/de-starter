from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import shutil
import stat
import sys
import unittest
from unittest.mock import patch

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import load_decisions
from destarter_lib.preview import create_preview
from destarter_lib.scanner import scan_project
from destarter_lib.apply import ApplyError, apply_preview


class PreviewApplyTests(unittest.TestCase):
    def test_apply_rejects_wrong_token_and_stale_source_or_preview(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            with self.assertRaisesRegex(ApplyError, "approval token"):
                apply_preview(root, base / "run", "wrong")

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            (root / "messages/en.json").write_text('{"brand":"changed"}', encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "source changed"):
                apply_preview(root, base / "run", manifest.approval_token)

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            (root / "new-safe-file.txt").write_text("added", encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "source changed"):
                apply_preview(root, base / "run", manifest.approval_token)

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            (Path(manifest.preview_root) / "messages/en.json").write_text('{"brand":"tampered"}', encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "preview changed"):
                apply_preview(root, base / "run", manifest.approval_token)

    def test_apply_rejects_new_file_in_delete_tree(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar", "demo"])
            path = base / "decisions.json"
            path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                                        "delete_paths": ["app/demo"]}), encoding="utf-8")
            manifest = create_preview(root, base / "run", audit, load_decisions(path, audit))
            (root / "app" / "demo" / "new-user-file.tsx").write_text("export default 1", encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "delete tree changed"):
                apply_preview(root, base / "run", manifest.approval_token)

    def test_apply_rejects_artifact_manifest_and_rename_tree_tampering(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            (base / "run" / "preview.diff").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "artifact changed"):
                apply_preview(root, base / "run", manifest.approval_token)

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            payload = json.loads((base / "run" / "manifest.json").read_text(encoding="utf-8"))
            payload["brand_mode"] = "real"
            (base / "run" / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "manifest approval token"):
                apply_preview(root, base / "run", manifest.approval_token)

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar", "demo"])
            path = base / "decisions.json"
            path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                                        "rename_paths": {"app/demo": "app/showcase"}}), encoding="utf-8")
            manifest = create_preview(root, base / "run", audit, load_decisions(path, audit))
            (root / "app" / "demo" / "new-user-file.tsx").write_text("export default 1", encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "rename source changed"):
                apply_preview(root, base / "run", manifest.approval_token)

    def test_apply_commits_text_rename_and_delete_with_recovery_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "app" / "examples").mkdir()
            (root / "app" / "examples" / "page.tsx").write_text("export default null\n", encoding="utf-8")
            audit = scan_project(root, ["Northstar", "demo"])
            finding = next(item for item in audit.findings if item.relpath == "messages/en.json" and item.risk.value == "P3")
            path = base / "decisions.json"
            path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [{
                "finding_id": finding.finding_id, "action": "replace", "replacement": "Your Product"}],
                "delete_paths": ["app/examples"], "rename_paths": {"app/demo": "app/showcase"}}), encoding="utf-8")
            manifest = create_preview(root, base / "run", audit, load_decisions(path, audit))
            result = apply_preview(root, base / "run", manifest.approval_token)
            self.assertIn("Your Product", (root / "messages/en.json").read_text(encoding="utf-8"))
            self.assertFalse((root / "app" / "examples").exists())
            self.assertTrue((root / "app" / "showcase" / "page.tsx").exists())
            self.assertFalse((root / "app" / "demo").exists())
            restore = json.loads(Path(result.restore_manifest).read_text(encoding="utf-8"))
            self.assertTrue((Path(result.backup_root) / ".destarter-backup-owner.json").exists())
            self.assertTrue(restore["operations"])
            for operation in restore["operations"]:
                self.assertTrue(Path(operation["backup"]).exists())
            self.assertFalse(any(".destarter-quarantine-" in item.name for item in root.rglob("*")))
            self.assertTrue((base / "run" / "reverse.diff").exists())

    def test_apply_rolls_back_when_a_mutation_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            with patch("destarter_lib.apply._create_outputs", side_effect=OSError("injected failure")):
                with self.assertRaisesRegex(ApplyError, "rolled back"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual((root / "messages/en.json").read_bytes(), original)

    def test_apply_rejects_late_secret_operation_roots_and_mode_changes(self) -> None:
        for operation in ("delete", "rename"):
            with self.subTest(operation=operation), TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = copy_fixture("nextjs-starter", base)
                audit = scan_project(root, ["Northstar", "demo"])
                decisions = {"brand_mode": "placeholder", "brand_profile": {}, "actions": []}
                decisions["{}_paths".format(operation)] = (
                    ["app/demo"] if operation == "delete" else {"app/demo": "app/showcase"}
                )
                path = base / "decisions.json"
                path.write_text(json.dumps(decisions), encoding="utf-8")
                manifest = create_preview(root, base / "run", audit, load_decisions(path, audit))
                (root / "app" / "demo" / ".env").write_text("TOKEN=not-copied", encoding="utf-8")
                with self.assertRaisesRegex(ApplyError, "excluded secret"):
                    apply_preview(root, base / "run", manifest.approval_token)
                self.assertFalse((base / "run" / "backup").exists())

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            target = root / "messages/en.json"
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
            with self.assertRaisesRegex(ApplyError, "source changed"):
                apply_preview(root, base / "run", manifest.approval_token)

    def test_apply_rechecks_standalone_original_at_final_transaction_entry(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_transaction = module._fd_transaction

            def mutate_at_entry(transaction):
                (root / "messages/en.json").write_text("changed after backup", encoding="utf-8")
                return original_transaction(transaction)

            with patch("destarter_lib.apply._fd_transaction", side_effect=mutate_at_entry):
                with self.assertRaisesRegex(ApplyError, "source changed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertFalse((base / "run" / "backup").exists())

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            target = root / "messages/en.json"
            from destarter_lib import apply as module
            original_transaction = module._fd_transaction

            def replace_at_entry(transaction):
                replacement = target.with_name("late-user-file")
                replacement.write_text("late replacement", encoding="utf-8")
                os.replace(str(replacement), str(target))
                return original_transaction(transaction)

            with patch("destarter_lib.apply._fd_transaction", side_effect=replace_at_entry):
                with self.assertRaisesRegex(ApplyError, "source changed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(target.read_text(encoding="utf-8"), "late replacement")
            self.assertFalse((base / "run" / "backup").exists())

    def test_apply_rolls_back_when_success_artifact_write_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_write = module._write_artifact_atomic
            calls = []

            def fail_second_artifact(*args):
                calls.append(args[1])
                if len(calls) == 2:
                    raise OSError("artifact failure")
                return original_write(*args)

            with patch("destarter_lib.apply._write_artifact_atomic", side_effect=fail_second_artifact):
                with self.assertRaisesRegex(ApplyError, "rolled back"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual((root / "messages/en.json").read_bytes(), original)
            self.assertFalse((base / "run" / "restore.json").exists())
            self.assertFalse((base / "run" / "reverse.diff").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_apply_preserves_late_rename_destination_at_final_transaction_entry(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._rename_preview(root, base / "run")
            from destarter_lib import apply as module
            original_transaction = module._fd_transaction

            def create_destination(transaction):
                (root / "app" / "showcase").write_text("user destination", encoding="utf-8")
                return original_transaction(transaction)

            with patch("destarter_lib.apply._fd_transaction", side_effect=create_destination):
                with self.assertRaisesRegex(ApplyError, "destination"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual((root / "app" / "showcase").read_text(encoding="utf-8"), "user destination")
            self.assertTrue((root / "app" / "demo" / "page.tsx").exists())
            self.assertFalse((base / "run" / "backup").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_apply_parent_symlink_swaps_never_touch_outside_data(self) -> None:
        for kind in ("file", "directory"):
            with self.subTest(kind=kind), TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = copy_fixture("nextjs-starter", base)
                outside = base / "outside"
                outside.mkdir()
                guard = outside / "guard.txt"
                guard.write_text("outside", encoding="utf-8")
                if kind == "file":
                    manifest = self._replacement_preview(root, base / "run")
                    parent = root / "messages"
                else:
                    manifest = self._rename_preview(root, base / "run")
                    parent = root / "app"
                displaced = root / (parent.name + "-displaced")
                from destarter_lib import apply as module
                original_transaction = module._fd_transaction

                def swap_parent(transaction):
                    parent.rename(displaced)
                    parent.symlink_to(outside, target_is_directory=True)
                    return original_transaction(transaction)

                with patch("destarter_lib.apply._fd_transaction", side_effect=swap_parent):
                    with self.assertRaisesRegex(ApplyError, "ambient"):
                        apply_preview(root, base / "run", manifest.approval_token)
                self.assertEqual(guard.read_text(encoding="utf-8"), "outside")
                self.assertFalse((base / "run" / "backup").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_apply_reports_failed_rollback_when_ambient_parent_changes_after_mutation(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            outside = base / "outside"
            outside.mkdir()
            guard = outside / "guard.txt"
            guard.write_text("outside", encoding="utf-8")
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_verify = module._verify_success
            changed = []

            def swap_after_mutation(transaction):
                if not changed:
                    parent = root / "messages"
                    parent.rename(root / "messages-displaced")
                    parent.symlink_to(outside, target_is_directory=True)
                    changed.append(True)
                return original_verify(transaction)

            with patch("destarter_lib.apply._verify_success", side_effect=swap_after_mutation):
                with self.assertRaisesRegex(ApplyError, "rollback failed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(guard.read_text(encoding="utf-8"), "outside")
            self.assertTrue((root / "messages-displaced" / "en.json").exists())
            self.assertTrue((base / "run" / "backup").exists())

    def test_apply_rejects_late_secret_at_final_transaction_entry(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._rename_preview(root, base / "run")
            from destarter_lib import apply as module
            original_transaction = module._fd_transaction

            def add_secret(transaction):
                (root / "app" / "demo" / ".env").write_text("TOKEN=late", encoding="utf-8")
                return original_transaction(transaction)

            with patch("destarter_lib.apply._fd_transaction", side_effect=add_secret):
                with self.assertRaisesRegex(ApplyError, "excluded secret"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertTrue((root / "app" / "demo" / ".env").exists())
            self.assertFalse((base / "run" / "backup").exists())

    def test_apply_preserves_byte_identical_new_inode_output_and_backup_on_failed_rollback(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_transaction = module._fd_transaction

            def replace_output(transaction):
                result = original_transaction(transaction)
                target = root / "messages/en.json"
                rendered = target.read_bytes()
                replacement = target.with_name("replacement")
                replacement.write_bytes(rendered)
                os.chmod(replacement, target.stat().st_mode & 0o7777)
                os.replace(str(replacement), str(target))
                return result

            with patch("destarter_lib.apply._fd_transaction", side_effect=replace_output):
                with self.assertRaisesRegex(ApplyError, "rollback failed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertNotEqual((root / "messages/en.json").read_bytes(), original)
            self.assertTrue((base / "run" / "backup").exists())
            self.assertFalse((base / "run" / "restore.json").exists())

    def test_apply_fails_closed_for_unsupported_primitives_and_cross_filesystem(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            with patch("destarter_lib.apply._fd_support", side_effect=ApplyError("unavailable")):
                with self.assertRaisesRegex(ApplyError, "unavailable"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertFalse((base / "run" / "backup").exists())

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            with patch("destarter_lib.apply._same_filesystem", return_value=False):
                with self.assertRaisesRegex(ApplyError, "same filesystem"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertFalse((base / "run" / "backup").exists())

    def test_apply_rejects_duplicate_manifest_json_as_apply_error(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            path = base / "run" / "manifest.json"
            payload = path.read_text(encoding="utf-8")
            path.write_text(payload.replace('"run_id":', '"run_id": "duplicate", "run_id":', 1), encoding="utf-8")
            with self.assertRaisesRegex(ApplyError, "duplicate key"):
                apply_preview(root, base / "run", manifest.approval_token)

    def test_apply_closes_all_descriptors(self) -> None:
        descriptor_root = Path("/dev/fd")
        if not descriptor_root.is_dir():
            self.skipTest("descriptor inventory unavailable")
        before = len(list(descriptor_root.iterdir()))
        for _index in range(3):
            with TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = copy_fixture("nextjs-starter", base)
                manifest = self._replacement_preview(root, base / "run")
                apply_preview(root, base / "run", manifest.approval_token)
        after = len(list(descriptor_root.iterdir()))
        self.assertLessEqual(after, before + 1)

    def test_preview_changes_copy_but_not_source(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_text(encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            finding = next(
                item for item in audit.findings
                if item.relpath == "messages/en.json" and item.risk.value == "P3"
            )
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [{
                    "finding_id": finding.finding_id,
                    "action": "replace",
                    "replacement": "Your Product"
                }]
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            self.assertEqual((root / "messages/en.json").read_text(encoding="utf-8"), original)
            preview = Path(manifest.preview_root) / "messages/en.json"
            self.assertIn("Your Product", preview.read_text(encoding="utf-8"))
            self.assertTrue((base / "run" / "preview.diff").exists())
            self.assertEqual(len(manifest.approval_token), 64)

    def test_preview_replaces_only_the_approved_occurrence(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            target = root / "messages/en.json"
            target.write_text(
                '{"first":"Northstar","second":"Northstar"}\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            findings = [
                item for item in audit.findings
                if item.relpath == "messages/en.json"
            ]
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [{
                    "finding_id": findings[0].finding_id,
                    "action": "replace",
                    "replacement": "Your Product"
                }]
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            rendered = (
                Path(manifest.preview_root) / "messages/en.json"
            ).read_text(encoding="utf-8")
            self.assertEqual(rendered.count("Your Product"), 1)
            self.assertEqual(rendered.count("Northstar"), 1)

    def test_preview_renames_only_inside_the_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [],
                "rename_paths": {"app/demo": "app/showcase"}
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            self.assertTrue((root / "app" / "demo" / "page.tsx").exists())
            self.assertFalse((root / "app" / "showcase").exists())
            self.assertTrue(
                (Path(manifest.preview_root) / "app" / "showcase" / "page.tsx").exists()
            )
            self.assertEqual(manifest.renamed_paths, {"app/demo": "app/showcase"})

    def test_preview_refuses_delete_or_rename_that_contains_secret_files(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "app" / "demo" / ".env").write_text(
                "TOKEN=live-secret",
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [],
                "delete_paths": ["app/demo"]
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret file"):
                create_preview(
                    root,
                    base / "run",
                    audit,
                    load_decisions(decisions_path, audit),
                )

    def test_preview_rejects_run_directory_inside_project(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            decisions = load_decisions(self._decisions(base), audit)
            with self.assertRaisesRegex(ValueError, "outside project"):
                create_preview(root, root / ".preview-run", audit, decisions)

    def test_manifest_binds_brand_mode_and_result_without_profile_values(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            decisions_path = self._decisions(base)
            manifest = create_preview(
                root, base / "run", audit, load_decisions(decisions_path, audit)
            )
            payload = json.loads((base / "run" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["brand_mode"], "placeholder")
            self.assertEqual(len(payload["brand_result_hash"]), 64)
            self.assertNotIn("Your Product", (base / "run" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest.approval_token, payload["approval_token"])

    def test_preview_redacts_secret_on_same_diff_line_without_changing_preview(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            target = root / "messages/en.json"
            secret = "live-token-12345678"
            target.write_text('{"brand":"Northstar", "API_TOKEN":"%s"}\n' % secret, encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            finding = next(item for item in audit.findings if item.relpath == "messages/en.json" and item.matched == "Northstar")
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [{
                "finding_id": finding.finding_id, "action": "replace", "replacement": "Your Product",
                "migration_plan": "display only", "rollback_plan": "restore display",
            }]}), encoding="utf-8")
            manifest = create_preview(root, base / "run", audit, load_decisions(decisions_path, audit))
            self.assertIn(secret, (Path(manifest.preview_root) / "messages/en.json").read_text(encoding="utf-8"))
            for name in ("preview.diff", "preview.md", "binary-changes.json", "placeholders.json", "manifest.json"):
                self.assertNotIn(secret, (base / "run" / name).read_text(encoding="utf-8"))

    def test_preview_rejects_stale_full_inventory_before_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            (root / "new-safe-file.txt").write_text("new", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale audit"):
                create_preview(root, base / "run", audit, load_decisions(self._decisions(base), audit))
            self.assertFalse((base / "run" / "preview").exists())

    def test_preview_rejects_secret_and_ignored_directories_in_operation_roots(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "app" / "demo" / ".env").mkdir()
            (root / "app" / "demo" / ".env" / "credentials").write_text("hidden", encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [], "delete_paths": ["app/demo"]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret file"):
                create_preview(root, base / "run", audit, load_decisions(decisions_path, audit))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_ignores_symlinks_inside_node_modules(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "pnpm-link").symlink_to(base / "elsewhere")
            audit = scan_project(root, ["Northstar"])
            create_preview(root, base / "run", audit, load_decisions(self._decisions(base), audit))

    def test_preview_token_is_deterministic_and_binds_explicit_keep(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            first = create_preview(root, base / "run", audit, load_decisions(self._decisions(base), audit))
            second = create_preview(root, base / "run", audit, load_decisions(self._decisions(base), audit))
            finding = next(item for item in audit.findings if item.risk.value == "P3")
            keep_path = base / "keep.json"
            keep_path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [{
                "finding_id": finding.finding_id, "action": "keep",
            }]}), encoding="utf-8")
            kept = create_preview(root, base / "keep-run", audit, load_decisions(keep_path, audit))
            self.assertEqual(first.approval_token, second.approval_token)
            self.assertNotEqual(first.approval_token, kept.approval_token)

    def test_preview_ignores_root_git_file_like_a_worktree(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / ".git").write_text("gitdir: /outside/worktree\n", encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            manifest = create_preview(root, base / "run", audit, load_decisions(self._decisions(base), audit))
            self.assertFalse((Path(manifest.preview_root) / ".git").exists())

    def test_preview_refuses_operation_root_with_nested_git_file(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "app" / "demo" / ".git").write_text("gitdir: /outside/module\n", encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            path = base / "decisions.json"
            path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [], "delete_paths": ["app/demo"]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ignored metadata"):
                create_preview(root, base / "run", audit, load_decisions(path, audit))

    def test_placeholder_artifact_uses_neutral_values_and_aggregates_identifiers(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            target = root / "messages/en.json"
            target.write_text('{"brand":"Northstar", "support":"hello@northstar.example"}\n', encoding="utf-8")
            audit = scan_project(root, ["Northstar", "hello@northstar.example"])
            brand = next(item for item in audit.findings if item.relpath == "messages/en.json" and item.matched == "Northstar")
            support = next(item for item in audit.findings if item.relpath == "messages/en.json" and item.matched == "hello@northstar.example")
            path = base / "decisions.json"
            path.write_text(json.dumps({"brand_mode": "placeholder", "brand_profile": {}, "actions": [
                {"finding_id": brand.finding_id, "action": "replace", "replacement": "Your Product",
                 "migration_plan": "display only", "rollback_plan": "restore display"},
                {"finding_id": support.finding_id, "action": "replace", "replacement": "support@example.com",
                 "migration_plan": "display only", "rollback_plan": "restore display"},
            ]}), encoding="utf-8")
            create_preview(root, base / "run", audit, load_decisions(path, audit))
            payload = json.loads((base / "run" / "placeholders.json").read_text(encoding="utf-8"))
            by_value = {item["value"]: item for item in payload}
            self.assertEqual(by_value["Your Product"]["identifiers"], ["product_name", "short_name"])
            self.assertEqual(by_value["Your Product"]["status"], "present")
            self.assertIn("messages/en.json", [item["path"] for item in by_value["Your Product"]["locations"]])
            self.assertGreaterEqual(by_value["Your Product"]["occurrences"], 1)
            self.assertEqual(by_value["support@example.com"]["status"], "present")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_refuses_symlink_that_escapes_project(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            outside = base / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (root / "escaped-link").symlink_to(outside)
            audit = scan_project(root, ["Northstar"])
            decisions = load_decisions(self._decisions(base), audit)
            with self.assertRaisesRegex(ValueError, "symlink"):
                create_preview(root, base / "run", audit, decisions)

    def _decisions(self, base: Path) -> Path:
        path = base / "decisions.json"
        path.write_text(json.dumps({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
        }), encoding="utf-8")
        return path

    def _replacement_preview(self, root: Path, run: Path):
        audit = scan_project(root, ["Northstar"])
        finding = next(
            item for item in audit.findings
            if item.relpath == "messages/en.json" and item.risk.value == "P3"
        )
        decisions_path = run.parent / "decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [{
                "finding_id": finding.finding_id, "action": "replace", "replacement": "Your Product",
            }],
        }), encoding="utf-8")
        return create_preview(root, run, audit, load_decisions(decisions_path, audit))

    def _rename_preview(self, root: Path, run: Path):
        audit = scan_project(root, ["Northstar", "demo"])
        decisions_path = run.parent / "decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
            "rename_paths": {"app/demo": "app/showcase"},
        }), encoding="utf-8")
        return create_preview(root, run, audit, load_decisions(decisions_path, audit))


if __name__ == "__main__":
    unittest.main()
