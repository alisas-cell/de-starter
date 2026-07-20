from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import load_decisions
from destarter_lib.preview import create_preview
from destarter_lib.scanner import scan_project


class PreviewApplyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
