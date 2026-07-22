from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
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
from destarter_lib.models import DecisionSet
from destarter_lib import apply as apply_module
from destarter_lib import preview as preview_module
from destarter_lib.preview import create_preview
from destarter_lib.scanner import scan_project
from destarter_lib.apply import ApplyError, apply_preview


class PreviewApplyTests(unittest.TestCase):
    def test_preview_applies_semantic_edit_only_to_external_copy(self) -> None:
        root, run, audit = self.semantic_fixture()
        original = (root / "app/page.tsx").read_bytes()
        decisions = self.semantic_decisions(
            root,
            audit,
            replacement=(
                "export default function Page() {\n"
                "  return <main>Neutral</main>;\n"
                "}\n"
            ),
        )
        manifest = create_preview(root, run, audit, decisions)
        self.assertEqual((root / "app/page.tsx").read_bytes(), original)
        self.assertIn(
            "Neutral",
            (Path(manifest.preview_root) / "app/page.tsx").read_text(),
        )
        metadata = json.loads((run / "semantic-edits.json").read_text())
        record = metadata["edits"][0]
        self.assertEqual(record["path"], "app/page.tsx")
        self.assertEqual(set(record), {
            "path", "start_line", "end_line", "reason",
            "before_sha256", "after_sha256", "p1_migration_protected",
        })
        self.assertEqual(
            record["before_sha256"],
            next(
                item.sha256 for item in audit.files
                if item.relpath == "app/page.tsx"
            ),
        )
        self.assertEqual(
            record["after_sha256"],
            manifest.preview_hashes["app/page.tsx"],
        )
        self.assertNotIn("Neutral", json.dumps(metadata))

    def test_semantic_edit_token_binds_reason_range_and_replacement(self) -> None:
        root, run, audit = self.semantic_fixture()
        whole_replacement = (
            "export default function Page() {\n"
            "  return <main>Neutral</main>;\n"
            "}\n"
        )
        first = create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(root, audit, whole_replacement),
        )
        changed_reason = create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(
                root,
                audit,
                whole_replacement,
                reason="Use approved neutral presentation",
            ),
        )
        changed_replacement = create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(
                root,
                audit,
                whole_replacement.replace("Neutral", "Generic"),
            ),
        )
        changed_range = create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(
                root,
                audit,
                "  return <main>Neutral</main>;\n",
                start_line=2,
                end_line=2,
            ),
        )
        self.assertNotEqual(first.approval_token, changed_reason.approval_token)
        self.assertNotEqual(first.approval_token, changed_replacement.approval_token)
        self.assertNotEqual(first.approval_token, changed_range.approval_token)

    def test_apply_rejects_semantic_artifact_project_and_preview_drift(self) -> None:
        root, run, audit = self.semantic_fixture()
        manifest = self._semantic_preview(root, run, audit)
        (run / "semantic-edits.json").write_text('{"edits": []}\n', encoding="utf-8")
        with self.assertRaisesRegex(ApplyError, "artifact changed"):
            apply_preview(root, run, manifest.approval_token)

        root, run, audit = self.semantic_fixture()
        manifest = self._semantic_preview(root, run, audit)
        (root / "app/page.tsx").write_text("project drift\n", encoding="utf-8")
        with self.assertRaisesRegex(ApplyError, "source changed"):
            apply_preview(root, run, manifest.approval_token)

        root, run, audit = self.semantic_fixture()
        manifest = self._semantic_preview(root, run, audit)
        (Path(manifest.preview_root) / "app/page.tsx").write_text(
            "preview drift\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ApplyError, "preview changed"):
            apply_preview(root, run, manifest.approval_token)

    def test_apply_semantic_edit_preserves_mode_and_rolls_back_bytes(self) -> None:
        root, run, audit = self.semantic_fixture(mode=0o744)
        manifest = self._semantic_preview(root, run, audit)
        result = apply_preview(root, run, manifest.approval_token)
        target = root / "app/page.tsx"
        self.assertIn("Neutral", target.read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o744)
        self.assertIn("app/page.tsx", result.changed_paths)

        root, run, audit = self.semantic_fixture(mode=0o744)
        target = root / "app/page.tsx"
        original = target.read_bytes()
        manifest = self._semantic_preview(root, run, audit)
        with patch(
            "destarter_lib.apply._create_outputs",
            side_effect=OSError("injected semantic failure"),
        ):
            with self.assertRaisesRegex(ApplyError, "rolled back"):
                apply_preview(root, run, manifest.approval_token)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o744)

    def test_semantic_replacement_is_absent_from_safe_metadata(self) -> None:
        root, run, audit = self.semantic_fixture()
        private = "private replacement value 7d8805"
        create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(root, audit, private + "\n"),
        )
        safe_metadata = "\n".join(
            (run / name).read_text(encoding="utf-8")
            for name in (
                "semantic-edits.json",
                "manifest.json",
                "preview.md",
                "binary-changes.json",
                "placeholders.json",
            )
        )
        self.assertNotIn(private, safe_metadata)

    def test_p1_semantic_edit_marks_migration_protection_without_replacement(self) -> None:
        root, run, _audit = self.semantic_fixture()
        target = root / "settings.py"
        target.write_text('PLAN_KEY = "starter_monthly"\n', encoding="utf-8")
        audit = scan_project(root, ["starter"])
        record = next(item for item in audit.files if item.relpath == "settings.py")
        decisions_path = root.parent / "p1-semantic-decisions.json"
        private = "private_replacement_value_7d8805"
        migration = "Migrate stored plan keys before deploying"
        rollback = "Restore the old key and audited file bytes"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "text_edits": [{
                "path": "settings.py",
                "expected_sha256": record.sha256,
                "start_line": 1,
                "end_line": 1,
                "replacement": 'PLAN_KEY = "{}"\n'.format(private),
                "reason": "Migrate the approved persisted plan identifier",
                "migration_plan": migration,
                "rollback_plan": rollback,
            }],
        }), encoding="utf-8")

        manifest = create_preview(
            root,
            run,
            audit,
            load_decisions(decisions_path, audit, root),
        )

        metadata_text = (run / "semantic-edits.json").read_text(encoding="utf-8")
        metadata = json.loads(metadata_text)
        record = metadata["edits"][0]
        self.assertTrue(record["p1_migration_protected"])
        self.assertNotIn(private, metadata_text)
        self.assertNotIn(migration, metadata_text)
        self.assertNotIn(rollback, metadata_text)
        self.assertIn(private, (Path(manifest.preview_root) / "settings.py").read_text())
        preview_report = (run / "preview.md").read_text(encoding="utf-8")
        self.assertIn("P1 migration-protected semantic edits: `1`", preview_report)
        self.assertNotIn(private, preview_report)
        self.assertNotIn(migration, preview_report)
        self.assertNotIn(rollback, preview_report)

        changed_payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        changed_payload["text_edits"][0]["migration_plan"] = (
            "Migrate stored plan keys in a different approved sequence"
        )
        decisions_path.write_text(json.dumps(changed_payload), encoding="utf-8")
        changed_plan_manifest = create_preview(
            root,
            root.parent / "run-with-changed-plan",
            audit,
            load_decisions(decisions_path, audit, root),
        )
        self.assertNotEqual(
            manifest.approval_token,
            changed_plan_manifest.approval_token,
        )

    def test_p1_semantic_edit_can_delete_approved_multiline_display_block(self) -> None:
        root, run, _audit = self.semantic_fixture()
        target = root / "components/legacy-offer.tsx"
        target.parent.mkdir(exist_ok=True)
        original = (
            "export const legacyOffer = {\n"
            '  planKey: "starter_monthly",\n'
            '  label: "Legacy course offer",\n'
            "};\n"
        )
        target.write_text(original, encoding="utf-8")
        audit = scan_project(root, ["starter"])
        record = next(
            item for item in audit.files
            if item.relpath == "components/legacy-offer.tsx"
        )
        decisions_path = root.parent / "p1-block-decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "text_edits": [{
                "path": "components/legacy-offer.tsx",
                "expected_sha256": record.sha256,
                "start_line": 1,
                "end_line": 4,
                "replacement": "",
                "reason": "Remove the approved obsolete display block",
                "migration_plan": "Redirect the old offer before deploying",
                "rollback_plan": "Restore the block from the audited backup",
            }],
        }), encoding="utf-8")

        manifest = create_preview(
            root,
            run,
            audit,
            load_decisions(decisions_path, audit, root),
        )

        self.assertEqual(target.read_text(encoding="utf-8"), original)
        self.assertEqual(
            (Path(manifest.preview_root) / "components/legacy-offer.tsx").read_text(),
            "",
        )
        metadata = json.loads((run / "semantic-edits.json").read_text())
        self.assertTrue(metadata["edits"][0]["p1_migration_protected"])

    def test_semantic_edit_rechecks_preimage_after_finding_replacement(self) -> None:
        root, run, _audit = self.semantic_fixture()
        target = root / "app/page.tsx"
        target.write_text(
            "// Northstar\n"
            "export default function Page() {\n"
            "  return <main>Starter</main>;\n"
            "}\n",
            encoding="utf-8",
        )
        audit = scan_project(root, ["Northstar", "starter"])
        finding = next(
            item for item in audit.findings
            if item.relpath == "app/page.tsx" and item.matched == "Northstar"
        )
        record = next(item for item in audit.files if item.relpath == "app/page.tsx")
        decisions_path = root.parent / "semantic-decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{
                "finding_id": finding.finding_id,
                "action": "replace",
                "replacement": "Your Product",
            }],
            "text_edits": [{
                "path": "app/page.tsx",
                "expected_sha256": record.sha256,
                "start_line": 2,
                "end_line": 4,
                "replacement": (
                    "export default function Page() {\n"
                    "  return <main>Neutral</main>;\n"
                    "}\n"
                ),
                "reason": "Replace starter presentation",
            }],
        }), encoding="utf-8")
        decisions = load_decisions(decisions_path, audit, root)
        from destarter_lib import preview as module
        real_write = module.safe_write_text

        def tamper_after_finding(path, text, mode=None):
            if mode is None:
                real_write(path, text)
            else:
                real_write(path, text, mode)
            if (
                Path(path).as_posix().endswith("/preview/app/page.tsx")
                and "// Your Product" in text
            ):
                Path(path).write_text(text + "tampered\n", encoding="utf-8")

        with patch(
            "destarter_lib.preview.safe_write_text",
            side_effect=tamper_after_finding,
        ):
            with self.assertRaisesRegex(ValueError, "preview preimage changed"):
                create_preview(root, run, audit, decisions)

    def test_preview_rejects_multiline_finding_replacement_with_semantic_edit(self) -> None:
        root, run, _audit = self.semantic_fixture()
        target = root / "app/page.tsx"
        target.write_text(
            'const brand = "Northstar";\n'
            'const second = "second";\n'
            'const third = "third";\n'
            'const fourth = "fourth";\n',
            encoding="utf-8",
        )
        original = target.read_bytes()
        audit = scan_project(root, ["Northstar"])
        finding = next(
            item for item in audit.findings
            if item.relpath == "app/page.tsx" and item.matched == "Northstar"
        )
        record = next(item for item in audit.files if item.relpath == "app/page.tsx")
        decisions_path = root.parent / "semantic-decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{
                "finding_id": finding.finding_id,
                "action": "replace",
                "replacement": "Your Product\nInjected line",
            }],
            "text_edits": [{
                "path": "app/page.tsx",
                "expected_sha256": record.sha256,
                "start_line": 4,
                "end_line": 4,
                "replacement": 'const fourth = "neutral";\n',
                "reason": "Replace the approved fourth line",
            }],
        }), encoding="utf-8")
        decisions = load_decisions(decisions_path, audit, root)

        with self.assertRaisesRegex(
            ValueError,
            "line-count-changing finding replacement",
        ):
            create_preview(root, run, audit, decisions)
        self.assertEqual(target.read_bytes(), original)

    def test_preview_applies_two_disjoint_semantic_ranges_bottom_up(self) -> None:
        root, run, _audit = self.semantic_fixture()
        target = root / "app/page.tsx"
        target.write_text(
            "one\ntwo\nthree\nfour\nfive\nsix\n",
            encoding="utf-8",
        )
        original = target.read_bytes()
        audit = scan_project(root, ["Northstar"])
        record = next(item for item in audit.files if item.relpath == "app/page.tsx")
        decisions_path = root.parent / "semantic-decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "text_edits": [{
                "path": "app/page.tsx",
                "expected_sha256": record.sha256,
                "start_line": 2,
                "end_line": 2,
                "replacement": "two-a\ntwo-b\n",
                "reason": "Expand the approved second line",
            }, {
                "path": "app/page.tsx",
                "expected_sha256": record.sha256,
                "start_line": 4,
                "end_line": 5,
                "replacement": "four-five\n",
                "reason": "Collapse the approved fourth and fifth lines",
            }],
        }), encoding="utf-8")
        decisions = load_decisions(decisions_path, audit, root)

        manifest = create_preview(root, run, audit, decisions)

        expected = b"one\ntwo-a\ntwo-b\nthree\nfour-five\nsix\n"
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(
            (Path(manifest.preview_root) / "app/page.tsx").read_bytes(),
            expected,
        )
        metadata = json.loads((run / "semantic-edits.json").read_text())
        self.assertEqual(
            [
                (item["start_line"], item["end_line"])
                for item in metadata["edits"]
            ],
            [(2, 2), (4, 5)],
        )
        self.assertTrue(all(
            item["before_sha256"] == record.sha256
            for item in metadata["edits"]
        ))
        final_hash = sha256(expected).hexdigest()
        self.assertTrue(all(
            item["after_sha256"] == final_hash
            for item in metadata["edits"]
        ))
        self.assertEqual(manifest.preview_hashes["app/page.tsx"], final_hash)

    def test_apply_rejects_late_semantic_artifact_change_at_pinned_verification(self) -> None:
        root, run, audit = self.semantic_fixture()
        target = root / "app/page.tsx"
        original = target.read_bytes()
        manifest = self._semantic_preview(root, run, audit)
        from destarter_lib import apply as module
        original_verify = module._verify_pinned_approval
        changed = []

        def change_artifact_at_pinned_verification(transaction):
            if not changed:
                (run / "semantic-edits.json").write_text(
                    '{"edits": []}\n', encoding="utf-8"
                )
                changed.append(True)
            return original_verify(transaction)

        with patch(
            "destarter_lib.apply._verify_pinned_approval",
            side_effect=change_artifact_at_pinned_verification,
        ):
            with self.assertRaisesRegex(ApplyError, "artifact changed"):
                apply_preview(root, run, manifest.approval_token)
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse((run / "backup").exists())

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

    def test_apply_creates_missing_parent_for_approved_nested_rename(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            audit = scan_project(root, ["Northstar", "demo"])
            path = base / "decisions.json"
            path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [],
                "rename_paths": {"app/demo": "public/product/demo"},
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(path, audit),
            )
            preview_parent_mode = stat.S_IMODE(
                (Path(manifest.preview_root) / "public/product").stat().st_mode
            )

            result = apply_preview(
                root, base / "run", manifest.approval_token
            )

            self.assertFalse((root / "app/demo").exists())
            self.assertTrue((root / "public/product/demo/page.tsx").is_file())
            self.assertEqual(
                stat.S_IMODE((root / "public/product").stat().st_mode),
                preview_parent_mode,
            )
            restore = json.loads(
                Path(result.restore_manifest).read_text(encoding="utf-8")
            )
            self.assertEqual(
                restore["created_parent_dirs"], ["public/product"]
            )

    def test_nested_rename_failure_removes_only_created_empty_parents(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            original = (root / "app/demo/page.tsx").read_bytes()
            manifest = self._nested_rename_preview(root, base / "run")

            with patch(
                "destarter_lib.apply._create_outputs",
                side_effect=OSError("injected nested rename failure"),
            ):
                with self.assertRaisesRegex(ApplyError, "rolled back"):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

            self.assertEqual(
                (root / "app/demo/page.tsx").read_bytes(), original
            )
            self.assertFalse((root / "public/product").exists())

    def test_nested_parent_open_and_fchmod_failures_leave_no_dir_or_fd(self) -> None:
        for failure in ("open", "fchmod"):
            with self.subTest(failure=failure), TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = copy_fixture("nextjs-starter", base)
                (root / "public").mkdir()
                manifest = self._nested_rename_preview(root, base / "run")
                descriptor_root = Path("/dev/fd")
                before = (
                    len(list(descriptor_root.iterdir()))
                    if descriptor_root.is_dir() else None
                )
                injected = []

                if failure == "open":
                    real = os.open

                    def fail_once(path, flags, *args, **kwargs):
                        if (
                            not injected
                            and path == "product"
                            and (root / "public/product").is_dir()
                        ):
                            injected.append(True)
                            raise OSError("injected parent open failure")
                        return real(path, flags, *args, **kwargs)

                    patcher = patch(
                        "destarter_lib.apply.os.open", side_effect=fail_once
                    )
                else:
                    real = os.fchmod

                    def fail_once(descriptor, mode):
                        product = root / "public/product"
                        if (
                            not injected
                            and product.is_dir()
                            and os.fstat(descriptor).st_ino
                            == product.stat().st_ino
                        ):
                            injected.append(True)
                            raise OSError("injected parent fchmod failure")
                        return real(descriptor, mode)

                    patcher = patch(
                        "destarter_lib.apply.os.fchmod", side_effect=fail_once
                    )

                with patcher, patch(
                    "destarter_lib.apply._fd_support", return_value=None
                ):
                    with self.assertRaisesRegex(
                        ApplyError, "refused before mutation"
                    ):
                        apply_preview(
                            root, base / "run", manifest.approval_token
                        )

                self.assertTrue(injected)
                self.assertFalse((root / "public/product").exists())
                self.assertTrue((root / "app/demo/page.tsx").is_file())
                self.assertFalse((base / "run/backup").exists())
                if before is not None:
                    self.assertLessEqual(
                        len(list(descriptor_root.iterdir())), before
                    )

    def test_nested_parent_cleanup_failure_is_reported_as_rollback_failure(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            manifest = self._nested_rename_preview(root, base / "run")
            real_fchmod = os.fchmod
            injected = []

            def add_content_then_fail(descriptor, mode):
                product = root / "public/product"
                if (
                    not injected
                    and product.is_dir()
                    and os.fstat(descriptor).st_ino == product.stat().st_ino
                ):
                    (product / "user.txt").write_text(
                        "user data", encoding="utf-8"
                    )
                    injected.append(True)
                    raise OSError("injected parent fchmod failure")
                return real_fchmod(descriptor, mode)

            with patch(
                "destarter_lib.apply.os.fchmod",
                side_effect=add_content_then_fail,
            ):
                with self.assertRaisesRegex(
                    ApplyError, "rollback failed.*cleanup failed"
                ):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

            self.assertTrue(injected)
            self.assertEqual(
                (root / "public/product/user.txt").read_text(encoding="utf-8"),
                "user data",
            )
            self.assertTrue((root / "app/demo/page.tsx").is_file())

    def test_nested_parent_cleanup_never_deletes_replacement_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            manifest = self._nested_rename_preview(root, base / "run")
            real_fchmod = os.fchmod
            injected = []
            replacement_identity = []

            def replace_then_fail(descriptor, mode):
                product = root / "public/product"
                if (
                    not injected
                    and product.is_dir()
                    and os.fstat(descriptor).st_ino == product.stat().st_ino
                ):
                    product.rename(root / "public/product-displaced")
                    product.mkdir()
                    replacement_identity.append(product.stat().st_ino)
                    injected.append(True)
                    raise OSError("injected parent replacement")
                return real_fchmod(descriptor, mode)

            with patch(
                "destarter_lib.apply.os.fchmod",
                side_effect=replace_then_fail,
            ):
                with self.assertRaisesRegex(
                    ApplyError, "rollback failed.*raced or replaced"
                ):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

            self.assertEqual(
                (root / "public/product").stat().st_ino,
                replacement_identity[0],
            )
            self.assertTrue((root / "public/product-displaced").is_dir())
            self.assertTrue((root / "app/demo/page.tsx").is_file())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_nested_rename_never_follows_parent_symlink_race(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            outside = base / "outside"
            outside.mkdir()
            guard = outside / "guard.txt"
            guard.write_text("outside", encoding="utf-8")
            manifest = self._nested_rename_preview(root, base / "run")
            from destarter_lib import apply as module
            real_create = module._create_output_parents

            def inject_symlink(transaction):
                (root / "public/product").symlink_to(
                    outside, target_is_directory=True
                )
                return real_create(transaction)

            with patch(
                "destarter_lib.apply._create_output_parents",
                side_effect=inject_symlink,
            ):
                with self.assertRaisesRegex(ApplyError, "parent"):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

            self.assertTrue((root / "public/product").is_symlink())
            self.assertEqual(guard.read_text(encoding="utf-8"), "outside")
            self.assertTrue((root / "app/demo/page.tsx").is_file())
            self.assertFalse((base / "run/backup").exists())

    def test_nested_rename_preserves_file_and_directory_parent_conflicts(self) -> None:
        for kind in ("file", "directory"):
            with self.subTest(kind=kind), TemporaryDirectory() as tmp:
                base = Path(tmp)
                root = copy_fixture("nextjs-starter", base)
                (root / "public").mkdir()
                manifest = self._nested_rename_preview(root, base / "run")
                conflict = root / "public/product"
                if kind == "file":
                    conflict.write_text("user file", encoding="utf-8")
                else:
                    conflict.mkdir()

                with self.assertRaisesRegex(ApplyError, "source changed"):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

                if kind == "file":
                    self.assertEqual(
                        conflict.read_text(encoding="utf-8"), "user file"
                    )
                else:
                    self.assertTrue(conflict.is_dir())
                self.assertTrue((root / "app/demo/page.tsx").is_file())
                self.assertFalse((base / "run/backup").exists())

    def test_nested_rename_rollback_preserves_foreign_parent_content(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "public").mkdir()
            original = (root / "app/demo/page.tsx").read_bytes()
            manifest = self._nested_rename_preview(root, base / "run")

            def inject_foreign_content(_transaction):
                (root / "public/product/user.txt").write_text(
                    "user data", encoding="utf-8"
                )
                raise OSError("injected output failure")

            with patch(
                "destarter_lib.apply._create_outputs",
                side_effect=inject_foreign_content,
            ):
                with self.assertRaisesRegex(
                    ApplyError, "rollback failed.*not empty"
                ):
                    apply_preview(
                        root, base / "run", manifest.approval_token
                    )

            self.assertEqual(
                (root / "app/demo/page.tsx").read_bytes(), original
            )
            self.assertEqual(
                (root / "public/product/user.txt").read_text(encoding="utf-8"),
                "user data",
            )

    def test_apply_rolls_back_when_a_mutation_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            with patch("destarter_lib.apply._create_outputs", side_effect=OSError("injected failure")):
                with self.assertRaisesRegex(ApplyError, "rolled back.*backup retained"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual((root / "messages/en.json").read_bytes(), original)
            retained = list((base / "run" / "backup" / "original").iterdir())
            self.assertEqual(len(retained), 1)
            self.assertEqual(retained[0].read_bytes(), original)
            self.assertNotEqual(
                retained[0].stat().st_ino,
                (root / "messages/en.json").stat().st_ino,
            )

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "app" / "demo" / "page.tsx").read_bytes()
            manifest = self._rename_preview(root, base / "run")
            with patch("destarter_lib.apply._create_outputs", side_effect=OSError("injected failure")):
                with self.assertRaisesRegex(ApplyError, "rolled back"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(
                (root / "app" / "demo" / "page.tsx").read_bytes(),
                original,
            )
            self.assertFalse((root / "app" / "showcase").exists())
            retained = list((base / "run" / "backup" / "original").iterdir())
            self.assertEqual(len(retained), 1)
            self.assertEqual((retained[0] / "page.tsx").read_bytes(), original)
            self.assertNotEqual(
                retained[0].stat().st_ino,
                (root / "app" / "demo").stat().st_ino,
            )

    def test_apply_preserves_backup_when_restored_file_is_replaced_after_verification(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_restore = module._restore_file_no_replace
            original_state_at = module._state_at
            restoring = []
            replaced = []

            def mark_restore(*args):
                restoring.append(True)
                try:
                    return original_restore(*args)
                finally:
                    restoring.pop()

            def replace_after_verification(parent_fd, name):
                state = original_state_at(parent_fd, name)
                if restoring and name == "en.json" and not replaced:
                    os.unlink(name, dir_fd=parent_fd)
                    descriptor = os.open(
                        name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=parent_fd,
                    )
                    try:
                        os.write(descriptor, b"late replacement after verify")
                    finally:
                        os.close(descriptor)
                    replaced.append(True)
                return state

            with patch(
                "destarter_lib.apply._create_outputs",
                side_effect=OSError("force rollback"),
            ), patch(
                "destarter_lib.apply._restore_file_no_replace",
                side_effect=mark_restore,
            ), patch(
                "destarter_lib.apply._state_at",
                side_effect=replace_after_verification,
            ):
                with self.assertRaisesRegex(ApplyError, "rollback failed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(
                (root / "messages/en.json").read_bytes(),
                b"late replacement after verify",
            )
            retained = list((base / "run" / "backup" / "original").iterdir())
            self.assertEqual(len(retained), 1)
            self.assertEqual(retained[0].read_bytes(), original)

    def test_apply_never_overwrites_a_late_restore_target(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            real_open = os.open
            raced = []

            def inject_restore_target(path, flags, *args, **kwargs):
                if (
                    not raced
                    and path == "en.json"
                    and flags & os.O_EXCL
                ):
                    descriptor = real_open(
                        path,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=kwargs["dir_fd"],
                    )
                    try:
                        os.write(descriptor, b"late user restore target")
                    finally:
                        os.close(descriptor)
                    raced.append(True)
                return real_open(path, flags, *args, **kwargs)

            with patch(
                "destarter_lib.apply._fd_support",
                return_value=None,
            ), patch(
                "destarter_lib.apply._create_outputs",
                side_effect=OSError("force rollback"),
            ), patch(
                "destarter_lib.apply.os.open",
                side_effect=inject_restore_target,
            ):
                with self.assertRaisesRegex(ApplyError, "rollback failed"):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(
                (root / "messages/en.json").read_bytes(),
                b"late user restore target",
            )
            self.assertTrue((base / "run" / "backup" / "original").is_dir())
            self.assertTrue(any((base / "run" / "backup" / "original").iterdir()))

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

    def test_apply_does_not_claim_or_remove_replaced_restore_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_bytes()
            manifest = self._replacement_preview(root, base / "run")
            from destarter_lib import apply as module
            original_state_at = module._state_at
            replaced = []

            def replace_after_link(parent_fd, name):
                if name == "restore.json" and not replaced:
                    os.unlink(name, dir_fd=parent_fd)
                    descriptor = os.open(
                        name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=parent_fd,
                    )
                    try:
                        os.write(descriptor, b"late user artifact")
                    finally:
                        os.close(descriptor)
                    replaced.append(True)
                return original_state_at(parent_fd, name)

            with patch("destarter_lib.apply._state_at", side_effect=replace_after_link):
                with self.assertRaises(ApplyError):
                    apply_preview(root, base / "run", manifest.approval_token)
            self.assertEqual(
                (base / "run" / "restore.json").read_bytes(),
                b"late user artifact",
            )
            self.assertEqual((root / "messages/en.json").read_bytes(), original)
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

    def test_preview_removes_only_an_explicitly_approved_empty_directory(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )

        self.assertTrue((root / "public/starter").is_dir())
        self.assertFalse((Path(manifest.preview_root) / "public/starter").exists())
        self.assertTrue((Path(manifest.preview_root) / "public").is_dir())
        self.assertEqual(manifest.cleanup_empty_dirs, ["public/starter"])
        state = manifest.cleanup_dir_states["public/starter"]
        self.assertEqual(
            set(state),
            {"mode", "state_sha256", "is_empty", "device", "inode"},
        )
        self.assertTrue(state["is_empty"])

        diff = (run / "preview.diff").read_text(encoding="utf-8")
        changes = json.loads((run / "binary-changes.json").read_text(encoding="utf-8"))
        report = (run / "preview.md").read_text(encoding="utf-8")
        payload = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("Empty directory cleanup: public/starter", diff)
        self.assertEqual(changes["operations"][-1]["operation"], "cleanup-empty-dir")
        self.assertEqual(changes["operations"][-1]["path"], "public/starter")
        self.assertIn("Cleaned empty directories: `1`", report)
        self.assertEqual(payload["cleanup_empty_dirs"], ["public/starter"])
        self.assertEqual(payload["cleanup_dir_states"], manifest.cleanup_dir_states)

    def test_preview_removes_a_parent_made_empty_by_an_approved_delete(self) -> None:
        root, run, _audit = self.cleanup_fixture(child="sample-starter.txt")
        audit = scan_project(root, ["starter"])
        decisions = self.cleanup_decisions(
            root,
            audit,
            cleanup=["public/starter"],
            delete_paths=["public/starter/sample-starter.txt"],
        )

        manifest = create_preview(root, run, audit, decisions)

        self.assertTrue((root / "public/starter/sample-starter.txt").is_file())
        self.assertFalse((Path(manifest.preview_root) / "public/starter").exists())
        self.assertTrue((Path(manifest.preview_root) / "public").is_dir())
        self.assertFalse(manifest.cleanup_dir_states["public/starter"]["is_empty"])

    def test_preview_removes_a_parent_made_empty_by_an_approved_rename(self) -> None:
        root, run, _audit = self.cleanup_fixture(child="demo/starter.txt")
        audit = scan_project(root, ["starter", "demo"])
        decisions = self.cleanup_decisions(
            root,
            audit,
            cleanup=["public/starter"],
            rename_paths={"public/starter/demo": "public/product"},
        )

        manifest = create_preview(root, run, audit, decisions)

        self.assertTrue((root / "public/starter/demo/starter.txt").is_file())
        self.assertTrue((Path(manifest.preview_root) / "public/product/starter.txt").is_file())
        self.assertFalse((Path(manifest.preview_root) / "public/starter").exists())
        self.assertTrue((Path(manifest.preview_root) / "public").is_dir())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_cleanup_refuses_an_ancestor_symlink_swap_without_touching_source(self) -> None:
        root, run, audit = self.cleanup_fixture()
        source = root / "public/starter"
        preview_public = run / "preview/public"
        preview_cleanup = preview_public / "starter"
        original_scandir = preview_module.os.scandir
        swapped = []

        def replace_preview_ancestor(value):
            if (
                not swapped
                and (
                    isinstance(value, int)
                    or Path(value) == preview_cleanup
                )
                and preview_public.is_dir()
                and not preview_public.is_symlink()
            ):
                preview_public.rename(run / "preview/public-displaced")
                preview_public.symlink_to(root / "public", target_is_directory=True)
                swapped.append(True)
            return original_scandir(value)

        with patch(
            "destarter_lib.preview.os.scandir",
            side_effect=replace_preview_ancestor,
        ):
            with self.assertRaisesRegex(ValueError, "cleanup"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertTrue(source.is_dir())
        self.assertFalse(source.is_symlink())
        self.assertTrue((root / "public").is_dir())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_cleanup_isolates_a_terminal_swapped_after_final_check(self) -> None:
        root, run, _audit = self.cleanup_fixture()
        source_object = root / "source-object"
        source_object.mkdir()
        preserved = source_object / "source-preserved.txt"
        preserved.write_text("preserve this source object\n", encoding="utf-8")
        audit = scan_project(root, ["starter"])
        preview_cleanup = run / "preview/public/starter"
        original_rename = preview_module.os.rename
        original_atomic_move = preview_module._atomic_rename_no_replace
        swapped = []

        def swap_terminal_before_isolation(source, destination, *args, **kwargs):
            if (
                not swapped
                and source == "starter"
                and kwargs.get("src_dir_fd") is not None
            ):
                original_rename(
                    str(preview_cleanup), str(run / "preview/public/original"),
                )
                original_rename(str(source_object), str(preview_cleanup))
                swapped.append(True)
            return original_atomic_move(source, destination, *args, **kwargs)

        with patch(
            "destarter_lib.preview._atomic_rename_no_replace",
            side_effect=swap_terminal_before_isolation,
        ):
            with self.assertRaisesRegex(ValueError, "cleanup"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertFalse((run / "manifest.json").exists())
        preserved_copies = list(run.rglob("source-preserved.txt"))
        isolated_copies = [
            path for path in preserved_copies
            if path.parent.name == "starter"
            or any(
                part.startswith(".destarter-preview-cleanup-")
                for part in path.parts
            )
        ]
        self.assertEqual(len(isolated_copies), 1)
        self.assertEqual(
            isolated_copies[0].read_text(encoding="utf-8"),
            "preserve this source object\n",
        )

    def test_preview_cleanup_preserves_foreign_terminal_and_staging_after_failure(self) -> None:
        root, run, audit = self.cleanup_fixture()
        preview_cleanup = run / "preview/public/starter"
        foreign_identity = []

        def create_foreign_terminal(*_args, **_kwargs):
            preview_cleanup.mkdir()
            info = preview_cleanup.lstat()
            foreign_identity.append((info.st_dev, info.st_ino))
            raise ValueError("injected isolated cleanup validation failure")

        with patch(
            "destarter_lib.preview._verify_isolated_preview_cleanup_dir",
            side_effect=create_foreign_terminal,
        ):
            with self.assertRaisesRegex(ValueError, "isolated cleanup"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertFalse((run / "manifest.json").exists())
        self.assertTrue(foreign_identity)
        info = preview_cleanup.lstat()
        self.assertEqual((info.st_dev, info.st_ino), foreign_identity[0])
        staging_dirs = [
            path for path in run.iterdir()
            if path.name.startswith(".destarter-preview-cleanup-")
        ]
        self.assertEqual(len(staging_dirs), 1)
        self.assertTrue(any(
            path.name.startswith("cleanup-")
            for path in staging_dirs[0].iterdir()
        ))

    def test_preview_retry_refuses_a_recovery_required_cleanup_failure(self) -> None:
        root, run, audit = self.cleanup_fixture()
        preview_cleanup = run / "preview/public/starter"
        foreign_identity = []

        def create_foreign_terminal(*_args, **_kwargs):
            preview_cleanup.mkdir()
            info = preview_cleanup.lstat()
            foreign_identity.append((info.st_dev, info.st_ino))
            raise ValueError("injected isolated cleanup validation failure")

        decisions = self.cleanup_decisions(
            root, audit, cleanup=["public/starter"],
        )
        with patch(
            "destarter_lib.preview._verify_isolated_preview_cleanup_dir",
            side_effect=create_foreign_terminal,
        ):
            with self.assertRaisesRegex(ValueError, "isolated cleanup"):
                create_preview(root, run, audit, decisions)

        initial = preview_cleanup.lstat()
        self.assertEqual((initial.st_dev, initial.st_ino), foreign_identity[0])
        with self.assertRaisesRegex(ValueError, "recovery required"):
            create_preview(root, run, audit, decisions)
        retried = preview_cleanup.lstat()
        self.assertEqual((retried.st_dev, retried.st_ino), foreign_identity[0])
        self.assertFalse((run / "manifest.json").exists())

    def test_preview_cleanup_never_overwrites_a_raced_staging_destination(self) -> None:
        root, run, audit = self.cleanup_fixture()
        original_absent = preview_module._entry_absent
        foreign_identity = []

        def insert_foreign_after_staging_probe(parent_fd, name):
            result = original_absent(parent_fd, name)
            if result and name.startswith("cleanup-") and not foreign_identity:
                staging_dirs = [
                    path for path in run.iterdir()
                    if path.name.startswith(".destarter-preview-cleanup-")
                ]
                self.assertEqual(len(staging_dirs), 1)
                foreign = staging_dirs[0] / name
                foreign.mkdir()
                info = foreign.lstat()
                foreign_identity.append((foreign, info.st_dev, info.st_ino))
            return result

        with patch(
            "destarter_lib.preview._entry_absent",
            side_effect=insert_foreign_after_staging_probe,
        ):
            with self.assertRaisesRegex(ValueError, "cleanup"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(foreign_identity)
        foreign, device, inode = foreign_identity[0]
        info = foreign.lstat()
        self.assertEqual((info.st_dev, info.st_ino), (device, inode))
        self.assertTrue((root / "public/starter").is_dir())
        self.assertFalse((run / "manifest.json").exists())

    def test_preview_cleanup_refuses_when_atomic_no_clobber_is_unavailable(self) -> None:
        root, run, audit = self.cleanup_fixture()

        with patch(
            "destarter_lib.preview._atomic_rename_no_replace",
            side_effect=ValueError("atomic no-clobber rename unavailable"),
            create=True,
        ) as atomic_move:
            with self.assertRaisesRegex(ValueError, "atomic no-clobber"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(atomic_move.called)
        self.assertTrue((root / "public/starter").is_dir())
        self.assertFalse((run / "manifest.json").exists())

    def test_preview_cleanup_uses_the_original_pinned_preview_root(self) -> None:
        root, run, audit = self.cleanup_fixture()
        preview_root = run / "preview"
        preserved_root = run / "pinned-preview-recovery"
        substitute_guard = "unknown substitute tree must remain untouched\n"
        original_open_staging = preview_module._open_preview_cleanup_staging
        swapped = []

        def replace_preview_root_after_pin(*args, **kwargs):
            staging_fd = original_open_staging(*args, **kwargs)
            preview_root.rename(preserved_root)
            shutil.copytree(root, preview_root)
            (preview_root / "unknown-substitute.txt").write_text(
                substitute_guard, encoding="utf-8",
            )
            swapped.append(True)
            return staging_fd

        with patch(
            "destarter_lib.preview._open_preview_cleanup_staging",
            side_effect=replace_preview_root_after_pin,
        ):
            with self.assertRaisesRegex(ValueError, "preview root changed"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertFalse((run / "manifest.json").exists())
        self.assertTrue((preserved_root / "public/starter").is_dir())
        self.assertTrue((preview_root / "public/starter").is_dir())
        self.assertEqual(
            (preview_root / "unknown-substitute.txt").read_text(encoding="utf-8"),
            substitute_guard,
        )

    def test_preview_refuses_root_replacement_after_manifest_write(self) -> None:
        root, run, audit = self.cleanup_fixture()
        preview_root = run / "preview"
        preserved_root = run / "manifest-written-preview"
        original_safe_write = preview_module.safe_write_text
        swapped = []

        def replace_root_after_manifest_write(path, text, *args, **kwargs):
            result = original_safe_write(path, text, *args, **kwargs)
            if Path(path).name == "manifest.json" and not swapped:
                preview_root.rename(preserved_root)
                shutil.copytree(root, preview_root)
                swapped.append(True)
            return result

        with patch(
            "destarter_lib.preview.safe_write_text",
            side_effect=replace_root_after_manifest_write,
        ):
            with self.assertRaisesRegex(ValueError, "preview root changed"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertTrue((preserved_root / "public").is_dir())
        self.assertTrue((preview_root / "public/starter").is_dir())

    def test_apply_refuses_preview_root_identity_drift_before_backup(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=[]),
        )
        preview_root = Path(manifest.preview_root)
        replacement = run / "same-content-different-preview-root"
        shutil.copytree(preview_root, replacement)
        shutil.rmtree(preview_root)
        replacement.rename(preview_root)

        with self.assertRaisesRegex(ApplyError, "preview root identity"):
            apply_preview(root, run, manifest.approval_token)
        self.assertFalse((run / "backup").exists())

    def test_apply_preview_root_identity_is_strict_token_bound_and_optional(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=[]),
        )
        manifest_path = run / "manifest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(set(payload["preview_root_identity"]), {"device", "inode"})

        tampered = dict(payload)
        tampered["preview_root_identity"] = dict(payload["preview_root_identity"])
        tampered["preview_root_identity"]["inode"] += 1
        manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaisesRegex(ApplyError, "approval token is tampered"):
            apply_preview(root, run, manifest.approval_token)

        partial = dict(payload)
        partial["preview_root_identity"] = {
            "device": payload["preview_root_identity"]["device"],
        }
        manifest_path.write_text(json.dumps(partial), encoding="utf-8")
        with self.assertRaisesRegex(ApplyError, "invalid manifest preview_root_identity"):
            apply_preview(root, run, manifest.approval_token)

        legacy = dict(payload)
        legacy.pop("preview_root_identity")
        manifest_path.write_text(json.dumps(legacy), encoding="utf-8")
        with self.assertRaisesRegex(ApplyError, "approval token is tampered"):
            apply_preview(root, run, manifest.approval_token)

        core_names = (
            "run_id", "project_root", "preview_root", "source_hashes",
            "preview_hashes", "delete_tree_hashes", "rename_tree_hashes",
            "changed_paths", "deleted_paths", "renamed_paths",
            "cleanup_empty_dirs", "cleanup_dir_states",
        )
        additive_names = (
            "brand_mode", "brand_result_hash", "decision_hash",
            "source_tree_hash", "preview_tree_hash", "source_state_hash",
            "preview_state_hash", "artifact_hashes",
        )
        legacy_core = {name: legacy[name] for name in core_names}
        legacy_additive = {name: legacy[name] for name in additive_names}
        legacy["approval_token"] = preview_module._token(
            dict(legacy_core, **legacy_additive),
        )
        manifest_path.write_text(json.dumps(legacy), encoding="utf-8")
        result = apply_preview(root, run, legacy["approval_token"])
        self.assertTrue(Path(result.backup_root).is_dir())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_snapshot_refuses_a_symlink_inserted_after_cleanup_check(self) -> None:
        root, run, audit = self.cleanup_fixture()
        source_guard = root / "source-guard.txt"
        source_guard.write_text("source remains intact\n", encoding="utf-8")
        audit = scan_project(root, ["starter"])
        original_state_hash = preview_module._state_hash
        injected = []

        def insert_symlink_before_snapshot(path, excluded_names=()):
            if Path(path).name == "preview" and not injected:
                (run / "preview/late-link").symlink_to(
                    root / "source-guard.txt",
                )
                injected.append(True)
            return original_state_hash(path, excluded_names)

        with patch(
            "destarter_lib.preview._state_hash",
            side_effect=insert_symlink_before_snapshot,
        ):
            with self.assertRaisesRegex(ValueError, "symlink"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(injected)
        self.assertFalse((run / "manifest.json").exists())
        self.assertEqual(source_guard.read_text(encoding="utf-8"), "source remains intact\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_snapshot_refuses_file_replaced_by_symlink_before_fd_read(self) -> None:
        root, run, _audit = self.cleanup_fixture()
        victim = root / "snapshot-victim.txt"
        victim.write_text("ordinary preview file\n", encoding="utf-8")
        target = root.parent / "outside-snapshot-target.txt"
        target.write_text("outside target must not be accepted\n", encoding="utf-8")
        audit = scan_project(root, ["starter"])
        preview_victim = run / "preview/snapshot-victim.txt"
        original_state_hash = preview_module._state_hash
        original_open = preview_module.os.open
        active_state_roots = []
        swapped = []

        def track_state_hash(path, excluded_names=()):
            active_state_roots.append(Path(path))
            try:
                return original_state_hash(path, excluded_names)
            finally:
                active_state_roots.pop()

        def swap_before_fd_read(path, flags, *args, **kwargs):
            if (
                active_state_roots
                and active_state_roots[-1].name == "preview"
                and path == "snapshot-victim.txt"
                and not swapped
            ):
                preview_victim.unlink()
                preview_victim.symlink_to(target)
                swapped.append(True)
            return original_open(path, flags, *args, **kwargs)

        with patch(
            "destarter_lib.preview._state_hash",
            side_effect=track_state_hash,
        ), patch(
            "destarter_lib.preview.os.open",
            side_effect=swap_before_fd_read,
        ):
            with self.assertRaisesRegex(ValueError, "state.*file|symlink"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertFalse((run / "manifest.json").exists())
        self.assertEqual(target.read_text(encoding="utf-8"), "outside target must not be accepted\n")
        self.assertTrue(victim.is_file())
        self.assertFalse(victim.is_symlink())

    def test_preview_snapshot_refuses_in_place_file_rewrite_during_fd_read(self) -> None:
        root, run, _audit = self.cleanup_fixture()
        victim = root / "snapshot-victim.bin"
        victim.write_bytes(b"A" * (2 * 1024 * 1024))
        audit = scan_project(root, ["starter"])
        preview_victim = run / "preview/snapshot-victim.bin"
        original_state_hash = preview_module._state_hash
        original_open = preview_module.os.open
        original_read = preview_module.os.read
        active_state_roots = []
        victim_fds = set()
        rewritten = []

        def track_state_hash(path, excluded_names=()):
            active_state_roots.append(Path(path))
            try:
                return original_state_hash(path, excluded_names)
            finally:
                active_state_roots.pop()

        def record_victim_fd(path, flags, *args, **kwargs):
            descriptor = original_open(path, flags, *args, **kwargs)
            if (
                active_state_roots
                and active_state_roots[-1].name == "preview"
                and path == "snapshot-victim.bin"
            ):
                victim_fds.add(descriptor)
            return descriptor

        def rewrite_after_first_chunk(descriptor, count):
            chunk = original_read(descriptor, count)
            if descriptor in victim_fds and chunk and not rewritten:
                with preview_victim.open("r+b") as handle:
                    handle.seek(0)
                    handle.write(b"B" * len(chunk))
                    handle.flush()
                    os.fsync(handle.fileno())
                rewritten.append(True)
            return chunk

        with patch(
            "destarter_lib.preview._state_hash",
            side_effect=track_state_hash,
        ), patch(
            "destarter_lib.preview.os.open",
            side_effect=record_victim_fd,
        ), patch(
            "destarter_lib.preview.os.read",
            side_effect=rewrite_after_first_chunk,
        ):
            with self.assertRaisesRegex(ValueError, "state.*file"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(rewritten)
        self.assertFalse((run / "manifest.json").exists())
        self.assertEqual(preview_victim.stat().st_size, 2 * 1024 * 1024)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_preview_cleanup_refuses_an_ancestor_swap_after_final_check(self) -> None:
        root, run, audit = self.cleanup_fixture()
        source_guard = root / "public/source-guard.txt"
        source_guard.write_text("source remains intact\n", encoding="utf-8")
        audit = scan_project(root, ["starter"])
        preview_public = run / "preview/public"
        original_rename = preview_module.os.rename
        original_atomic_move = preview_module._atomic_rename_no_replace
        swapped = []

        def swap_ancestor_before_isolation(source, destination, *args, **kwargs):
            if (
                not swapped
                and source == "starter"
                and kwargs.get("src_dir_fd") is not None
            ):
                original_rename(
                    str(preview_public), str(run / "preview/public-displaced"),
                )
                preview_public.symlink_to(root / "public", target_is_directory=True)
                swapped.append(True)
            return original_atomic_move(source, destination, *args, **kwargs)

        with patch(
            "destarter_lib.preview._atomic_rename_no_replace",
            side_effect=swap_ancestor_before_isolation,
        ):
            with self.assertRaisesRegex(ValueError, "cleanup"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(swapped)
        self.assertFalse((run / "manifest.json").exists())
        self.assertTrue((root / "public/starter").is_dir())
        self.assertEqual(source_guard.read_text(encoding="utf-8"), "source remains intact\n")
        self.assertTrue(preview_public.is_symlink())

    def test_preview_rejects_source_drift_after_cleanup_before_manifest(self) -> None:
        root, run, _audit = self.cleanup_fixture()
        source_object = root / "source-object.txt"
        source_object.write_text("do not bind stale source state\n", encoding="utf-8")
        audit = scan_project(root, ["starter"])
        original_check = preview_module._ensure_no_symlinks
        checks = []
        mutated = []

        def move_source_after_cleanup(path):
            result = original_check(path)
            checks.append(path)
            if (
                not mutated
                and (run / "preview").is_dir()
                and not (run / "preview/public/starter").exists()
            ):
                source_object.rename(root / "source-object-moved.txt")
                mutated.append(True)
            return result

        with patch(
            "destarter_lib.preview._ensure_no_symlinks",
            side_effect=move_source_after_cleanup,
        ):
            with self.assertRaisesRegex(ValueError, "source changed during preview"):
                create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    ),
                )

        self.assertTrue(mutated)
        self.assertFalse((run / "manifest.json").exists())
        self.assertEqual(
            (root / "source-object-moved.txt").read_text(encoding="utf-8"),
            "do not bind stale source state\n",
        )

    def test_preview_refuses_cleanup_when_a_child_is_not_owned_or_safe(self) -> None:
        cases = ("leftover.txt", "node_modules", ".env", "symlink", "file")
        for case in cases:
            with self.subTest(case=case):
                root, run, audit = self.cleanup_fixture()
                cleanup = root / "public/starter"
                if case == "leftover.txt":
                    (cleanup / case).write_text("leftover\n", encoding="utf-8")
                elif case in {"node_modules", ".env"}:
                    child = cleanup / case
                    child.mkdir()
                    (child / "child.txt").write_text("excluded\n", encoding="utf-8")
                elif case == "symlink":
                    target = root / "outside"
                    target.mkdir()
                    cleanup.rmdir()
                    cleanup.symlink_to(target, target_is_directory=True)
                else:
                    cleanup.rmdir()
                    cleanup.write_text("not a directory\n", encoding="utf-8")

                if case in {"leftover.txt", "node_modules", ".env"}:
                    audit = scan_project(root, ["starter"])
                    decisions = self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    )
                else:
                    decisions = self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"], validate=False,
                    )
                with self.assertRaisesRegex(ValueError, "cleanup|symlink|directory|stale audit"):
                    create_preview(root, run, audit, decisions)
                self.assertTrue((root / "public").exists())
                if case == "symlink":
                    self.assertTrue(cleanup.is_symlink())
                elif case == "file":
                    self.assertTrue(cleanup.is_file())
                else:
                    self.assertTrue(cleanup.is_dir())

    def test_cleanup_decision_mode_and_state_are_token_bound(self) -> None:
        root, run, audit = self.cleanup_fixture()
        without_cleanup = create_preview(
            root, run, audit, self.cleanup_decisions(root, audit, cleanup=[])
        )
        without_cleanup_payload = json.loads((run / "manifest.json").read_text())
        with_cleanup = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        with_cleanup_payload = json.loads((run / "manifest.json").read_text())
        self.assertNotEqual(without_cleanup.approval_token, with_cleanup.approval_token)
        self.assertNotEqual(
            without_cleanup_payload["decision_hash"],
            with_cleanup_payload["decision_hash"],
        )

        directory = root / "public/starter"
        directory.chmod(0o711)
        mode_audit = scan_project(root, ["starter"])
        changed_mode = create_preview(
            root,
            run,
            mode_audit,
            self.cleanup_decisions(root, mode_audit, cleanup=["public/starter"]),
        )
        changed_mode_payload = json.loads((run / "manifest.json").read_text())
        self.assertNotEqual(with_cleanup.approval_token, changed_mode.approval_token)
        self.assertNotEqual(
            with_cleanup_payload["decision_hash"],
            changed_mode_payload["decision_hash"],
        )
        self.assertNotEqual(
            with_cleanup.cleanup_dir_states["public/starter"]["mode"],
            changed_mode.cleanup_dir_states["public/starter"]["mode"],
        )

        directory.chmod(0o755)
        (directory / "sample-starter.txt").write_text("first\n", encoding="utf-8")
        state_audit = scan_project(root, ["starter"])
        changed_state = create_preview(
            root,
            run,
            state_audit,
            self.cleanup_decisions(
                root,
                state_audit,
                cleanup=["public/starter"],
                delete_paths=["public/starter/sample-starter.txt"],
            ),
        )
        changed_state_payload = json.loads((run / "manifest.json").read_text())
        self.assertNotEqual(changed_mode.approval_token, changed_state.approval_token)
        self.assertNotEqual(
            changed_mode_payload["decision_hash"],
            changed_state_payload["decision_hash"],
        )
        self.assertNotEqual(
            changed_mode.cleanup_dir_states["public/starter"]["state_sha256"],
            changed_state.cleanup_dir_states["public/starter"]["state_sha256"],
        )

    def test_apply_refuses_cleanup_manifest_before_creating_a_backup(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )

        with self.assertRaisesRegex(ApplyError, "empty-directory cleanup.*not implemented"):
            apply_preview(root, run, manifest.approval_token)
        self.assertTrue((root / "public/starter").is_dir())
        self.assertFalse((run / "backup").exists())

    def test_apply_strictly_loads_cleanup_manifest_fields_before_backup(self) -> None:
        cases = (
            ("unknown top-level key", lambda value: value.update({"extra": 1}), False),
            ("missing cleanup paths", lambda value: value.pop("cleanup_empty_dirs"), False),
            ("missing cleanup states", lambda value: value.pop("cleanup_dir_states"), False),
            ("cleanup paths wrong type", lambda value: value.update({"cleanup_empty_dirs": {}}), False),
            ("cleanup states wrong type", lambda value: value.update({"cleanup_dir_states": []}), False),
            (
                "partial cleanup state",
                lambda value: value["cleanup_dir_states"]["public/starter"].pop("is_empty"),
                False,
            ),
            (
                "unknown cleanup state key",
                lambda value: value["cleanup_dir_states"]["public/starter"].update({"extra": 1}),
                False,
            ),
            (
                "normalized duplicate cleanup path",
                lambda value: value["cleanup_empty_dirs"].append("public/./starter"),
                True,
            ),
            (
                "cleanup state path mismatch",
                lambda value: value["cleanup_dir_states"].update({
                    "public/other": dict(value["cleanup_dir_states"]["public/starter"]),
                }),
                True,
            ),
        )
        for label, mutate, retoken in cases:
            with self.subTest(label=label):
                root, run, audit = self.cleanup_fixture()
                manifest = create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
                )
                payload = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
                mutate(payload)
                if retoken:
                    self._retoken_manifest(payload)
                (run / "manifest.json").write_text(
                    json.dumps(payload), encoding="utf-8",
                )
                self._assert_apply_refused_without_changes(
                    root,
                    run,
                    payload.get("approval_token", manifest.approval_token),
                    "invalid preview manifest|invalid manifest",
                )

    def test_apply_rejects_cleanup_token_tampering_before_backup(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        payload = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        payload["cleanup_dir_states"]["public/starter"]["mode"] ^= 0o001
        (run / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")

        self._assert_apply_refused_without_changes(
            root, run, manifest.approval_token, "approval token.*tampered",
        )

    def test_apply_rejects_cleanup_operation_shape_tampering_before_backup(self) -> None:
        cases = ("overlapping cleanup roots", "cleanup under source", "destination overlap")
        for label in cases:
            with self.subTest(label=label):
                child = "demo/starter.txt" if label == "destination overlap" else ""
                root, run, audit = self.cleanup_fixture(child=child)
                if label == "destination overlap":
                    audit = scan_project(root, ["starter", "demo"])
                    decisions = self.cleanup_decisions(
                        root,
                        audit,
                        cleanup=["public/starter"],
                        rename_paths={"public/starter/demo": "public/product"},
                    )
                else:
                    decisions = self.cleanup_decisions(
                        root, audit, cleanup=["public/starter"],
                    )
                create_preview(root, run, audit, decisions)
                payload = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
                state = dict(payload["cleanup_dir_states"]["public/starter"])
                if label == "overlapping cleanup roots":
                    payload["cleanup_empty_dirs"].append("public")
                    payload["cleanup_empty_dirs"].sort()
                    payload["cleanup_dir_states"]["public"] = state
                elif label == "cleanup under source":
                    payload["deleted_paths"] = ["public"]
                    payload["delete_tree_hashes"] = {
                        "public": preview_module._tree_hash(root, "public"),
                    }
                else:
                    payload["renamed_paths"]["public/starter/demo"] = (
                        "public/starter/output"
                    )
                    payload["rename_tree_hashes"]["public/starter/demo"][
                        "destination"
                    ] = "public/starter/output"
                self._retoken_manifest(payload)
                (run / "manifest.json").write_text(
                    json.dumps(payload), encoding="utf-8",
                )
                self._assert_apply_refused_without_changes(
                    root, run, payload["approval_token"], "invalid manifest.*overlap|invalid manifest cleanup",
                )

    def test_apply_revalidates_cleanup_source_state_before_backup(self) -> None:
        def change_mode(root, _run):
            (root / "public/starter").chmod(0o711)

        def add_ordinary(root, _run):
            (root / "public/starter/new.txt").write_text("foreign\n", encoding="utf-8")

        def add_ignored(root, _run):
            (root / "public/starter/.git").mkdir()

        def add_secret(root, _run):
            (root / "public/starter/.env").write_text("SECRET=x\n", encoding="utf-8")

        def replace_with_file(root, _run):
            shutil.rmtree(root / "public/starter")
            (root / "public/starter").write_text("foreign\n", encoding="utf-8")

        cases = (
            ("mode", change_mode),
            ("ordinary child", add_ordinary),
            ("ignored child", add_ignored),
            ("secret child", add_secret),
            ("changed to file", replace_with_file),
        )
        for label, mutate in cases:
            with self.subTest(label=label):
                root, run, audit = self.cleanup_fixture()
                manifest = create_preview(
                    root,
                    run,
                    audit,
                    self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
                )
                mutate(root, run)
                self._assert_apply_refused_without_changes(
                    root, run, manifest.approval_token, "cleanup|source changed",
                )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_apply_rejects_cleanup_source_symlink_replacement_before_backup(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        displaced = root.parent / "displaced-starter"
        (root / "public/starter").rename(displaced)
        (root / "public/starter").symlink_to(displaced, target_is_directory=True)

        with self.assertRaisesRegex(ApplyError, "symlink|cleanup|source changed"):
            apply_preview(root, run, manifest.approval_token)
        self.assertFalse((run / "backup").exists())
        self.assertFalse((run / "restore.json").exists())
        self.assertFalse((run / "reverse.diff").exists())
        self.assertTrue((root / "public/starter").is_symlink())
        self.assertTrue(displaced.is_dir())

    def test_apply_rejects_cleanup_inode_swap_during_preflight(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        original_iter = apply_module.iter_project_directories
        displaced = root.parent / "displaced-starter"
        swapped = []

        def replace_after_pin(value):
            if not swapped:
                directory = root / "public/starter"
                mode = stat.S_IMODE(directory.stat().st_mode)
                directory.rename(displaced)
                directory.mkdir(mode=mode)
                swapped.append(True)
            return original_iter(value)

        with patch(
            "destarter_lib.apply.iter_project_directories",
            side_effect=replace_after_pin,
        ):
            with self.assertRaisesRegex(ApplyError, "cleanup.*changed"):
                apply_preview(root, run, manifest.approval_token)

        self.assertTrue(swapped)
        self.assertTrue((root / "public/starter").is_dir())
        self.assertTrue(displaced.is_dir())
        self.assertFalse((run / "backup").exists())

    def test_apply_rejects_cleanup_ancestor_swap_during_preflight(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        original_iter = apply_module.iter_project_directories
        displaced = root.parent / "displaced-public"
        swapped = []

        def replace_ancestor_after_pin(value):
            if not swapped:
                public = root / "public"
                public_mode = stat.S_IMODE(public.stat().st_mode)
                cleanup_mode = stat.S_IMODE((public / "starter").stat().st_mode)
                public.rename(displaced)
                public.mkdir(mode=public_mode)
                (public / "starter").mkdir(mode=cleanup_mode)
                swapped.append(True)
            return original_iter(value)

        with patch(
            "destarter_lib.apply.iter_project_directories",
            side_effect=replace_ancestor_after_pin,
        ):
            with self.assertRaisesRegex(ApplyError, "cleanup.*changed"):
                apply_preview(root, run, manifest.approval_token)

        self.assertTrue(swapped)
        self.assertTrue((root / "public/starter").is_dir())
        self.assertTrue((displaced / "starter").is_dir())
        self.assertFalse((run / "backup").exists())

    def test_apply_rejects_same_state_new_cleanup_inode_after_preview(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        directory = root / "public/starter"
        original_mode = stat.S_IMODE(directory.stat().st_mode)
        displaced = root.parent / "displaced-starter"
        directory.rename(displaced)
        directory.mkdir(mode=original_mode)

        self._assert_apply_refused_without_changes(
            root, run, manifest.approval_token, "cleanup.*identity.*changed",
        )
        self.assertTrue(directory.is_dir())
        self.assertTrue(displaced.is_dir())

    def test_apply_revalidates_cleanup_preview_root_identity_before_backup(self) -> None:
        root, run, audit = self.cleanup_fixture()
        manifest = create_preview(
            root,
            run,
            audit,
            self.cleanup_decisions(root, audit, cleanup=["public/starter"]),
        )
        preview_root = Path(manifest.preview_root)
        replacement = run / "same-content-different-preview-root"
        shutil.copytree(preview_root, replacement)
        shutil.rmtree(preview_root)
        replacement.rename(preview_root)

        self._assert_apply_refused_without_changes(
            root, run, manifest.approval_token, "preview root identity",
        )

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
            self.assertNotEqual(first.approval_token, second.approval_token)
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

    def cleanup_fixture(self, child: str = ""):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        root = copy_fixture("nextjs-starter", base)
        directory = root / "public/starter"
        directory.mkdir(parents=True)
        if child:
            path = directory / child
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample\n", encoding="utf-8")
        return root, base / "run", scan_project(root, ["starter", "demo"])

    def cleanup_decisions(
        self,
        root: Path,
        audit,
        *,
        cleanup,
        delete_paths=None,
        rename_paths=None,
        validate: bool = True,
    ):
        payload = {
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "cleanup_empty_dirs": cleanup,
            "delete_paths": delete_paths or [],
            "rename_paths": rename_paths or {},
        }
        if not validate:
            return DecisionSet(
                "placeholder", {}, [], list(payload["delete_paths"]),
                dict(payload["rename_paths"]), [], list(cleanup),
            )
        path = root.parent / "cleanup-decisions.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return load_decisions(path, audit, root)

    def _retoken_manifest(self, payload) -> None:
        payload["approval_token"] = preview_module._token({
            key: value
            for key, value in payload.items()
            if key != "approval_token"
        })

    def _assert_apply_refused_without_changes(
        self,
        root: Path,
        run: Path,
        approval_token: str,
        message: str,
    ) -> None:
        before = preview_module._state_hash(root)
        with self.assertRaisesRegex(ApplyError, message):
            apply_preview(root, run, approval_token)
        self.assertEqual(preview_module._state_hash(root), before)
        self.assertFalse((run / "backup").exists())
        self.assertFalse((run / "restore.json").exists())
        self.assertFalse((run / "reverse.diff").exists())

    def _decisions(self, base: Path) -> Path:
        path = base / "decisions.json"
        path.write_text(json.dumps({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
        }), encoding="utf-8")
        return path

    def semantic_fixture(self, mode=None):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        root = copy_fixture("nextjs-starter", base)
        (root / "app/page.tsx").write_text(
            "export default function Page() {\n"
            "  return <main>Starter</main>;\n"
            "}\n",
            encoding="utf-8",
        )
        if mode is not None:
            os.chmod(root / "app/page.tsx", mode)
        return root, base / "run", scan_project(root, ["Northstar", "starter"])

    def semantic_decisions(
        self,
        root: Path,
        audit,
        replacement: str,
        *,
        start_line: int = 1,
        end_line: int = 3,
        reason: str = "Replace starter presentation",
    ):
        record = next(item for item in audit.files if item.relpath == "app/page.tsx")
        path = root.parent / "semantic-decisions.json"
        path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "text_edits": [{
                "path": "app/page.tsx",
                "expected_sha256": record.sha256,
                "start_line": start_line,
                "end_line": end_line,
                "replacement": replacement,
                "reason": reason,
            }],
        }), encoding="utf-8")
        return load_decisions(path, audit, root)

    def _semantic_preview(self, root: Path, run: Path, audit):
        return create_preview(
            root,
            run,
            audit,
            self.semantic_decisions(
                root,
                audit,
                "export default function Page() {\n"
                "  return <main>Neutral</main>;\n"
                "}\n",
            ),
        )

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

    def _nested_rename_preview(self, root: Path, run: Path):
        audit = scan_project(root, ["Northstar", "demo"])
        decisions_path = run.parent / "nested-rename-decisions.json"
        decisions_path.write_text(json.dumps({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "rename_paths": {"app/demo": "public/product/demo"},
        }), encoding="utf-8")
        return create_preview(
            root,
            run,
            audit,
            load_decisions(decisions_path, audit),
        )


if __name__ == "__main__":
    unittest.main()
