from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import DecisionError, load_decisions
from destarter_lib.models import Finding, RiskLevel
from destarter_lib.scanner import scan_project


class DecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = copy_fixture("nextjs-starter", Path(self.temp.name))
        self.audit = scan_project(self.root, ["Northstar", "starter_monthly"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, payload: dict) -> Path:
        path = Path(self.temp.name) / "decisions.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_raw(self, payload: bytes) -> Path:
        path = Path(self.temp.name) / "decisions.json"
        path.write_bytes(payload)
        return path

    def base_payload(self) -> dict:
        return {"brand_mode": "placeholder", "brand_profile": {}, "actions": []}

    def write_payload(self, directory: str, payload: dict) -> Path:
        path = Path(directory) / "decisions.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def text_edit_payload(self, audit=None, path="app/demo/page.tsx", **changes) -> dict:
        audit = audit or self.audit
        record = next((item for item in audit.files if item.relpath == path), None)
        edit = {
            "path": path,
            "expected_sha256": record.sha256 if record else "0" * 64,
            "start_line": 1,
            "end_line": 1,
            "replacement": "// neutral\n",
            "reason": "Replace approved sample presentation",
        }
        edit.update(changes)
        payload = self.base_payload()
        payload["text_edits"] = [edit]
        return payload

    def cleanup_payload(self, *paths: str, **changes) -> dict:
        payload = self.base_payload()
        payload["cleanup_empty_dirs"] = list(paths)
        payload.update(changes)
        return payload

    def audit_cleanup_directory(self, relpath: str, *, non_empty: bool = False):
        directory = self.root / relpath
        directory.mkdir(parents=True)
        if non_empty:
            (directory / "child.txt").write_text("child\n", encoding="utf-8")
        return scan_project(self.root, ["starter"])

    def test_cleanup_empty_dirs_is_compatible_and_requires_exact_directory_authority(self) -> None:
        self.assertEqual(load_decisions(self.write(self.base_payload()), self.audit).cleanup_empty_dirs, [])

        audit = self.audit_cleanup_directory("public/starter")
        decisions = load_decisions(
            self.write(self.cleanup_payload("public/starter")), audit, self.root,
        )
        self.assertEqual(decisions.cleanup_empty_dirs, ["public/starter"])

        audit = self.audit_cleanup_directory("public/nonempty-starter", non_empty=True)
        decisions = load_decisions(
            self.write(self.cleanup_payload("public/nonempty-starter")), audit, self.root,
        )
        self.assertEqual(decisions.cleanup_empty_dirs, ["public/nonempty-starter"])

    def test_cleanup_empty_dirs_rejects_nonexact_or_protected_paths(self) -> None:
        audit = self.audit_cleanup_directory("public/starter")
        ordinary = self.root / "public/ordinary"
        ordinary.mkdir()
        audit = scan_project(self.root, ["starter"])
        for path in (
            "public/starter", "public//starter", ".", "/outside", "../outside",
            "public/ordinary", "node_modules/starter", ".env/starter", "LICENSE/starter",
            "missing/starter",
        ):
            with self.subTest(path=path):
                paths = ["public/starter", path]
                with self.assertRaises(DecisionError):
                    load_decisions(self.write(self.cleanup_payload(*paths)), audit, self.root)

    def test_cleanup_empty_dirs_rejects_changed_symlink_and_file(self) -> None:
        audit = self.audit_cleanup_directory("public/starter")
        starter = self.root / "public/starter"
        starter.rmdir()
        target = self.root / "outside"
        target.mkdir()
        starter.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(DecisionError, "symlink"):
            load_decisions(self.write(self.cleanup_payload("public/starter")), audit, self.root)

        starter.unlink()
        starter.write_text("not a directory\n", encoding="utf-8")
        with self.assertRaisesRegex(DecisionError, "directory"):
            load_decisions(self.write(self.cleanup_payload("public/starter")), audit, self.root)

    def test_cleanup_empty_dirs_requires_matching_directory_finding_and_rejects_protected_descendants(self) -> None:
        audit = self.audit_cleanup_directory("public/starter", non_empty=True)
        directory_finding = next(
            item for item in audit.directory_findings if item.relpath == "public/starter"
        )
        for changed_audit in (
            replace(audit, directory_findings=[]),
            replace(
                audit,
                directory_findings=[replace(directory_finding, sha256="0" * 64)],
            ),
        ):
            with self.subTest(changed_audit=changed_audit.directory_findings):
                with self.assertRaisesRegex(DecisionError, "directory finding"):
                    load_decisions(
                        self.write(self.cleanup_payload("public/starter")),
                        changed_audit,
                        self.root,
                    )

        for risk in (RiskLevel.P0, RiskLevel.P1):
            protected = Finding(
                finding_id="protected-{}".format(risk.value),
                relpath="public/starter/child.txt",
                line=1,
                column=1,
                matched="child",
                category="content",
                risk=risk,
                evidence="protected descendant",
                sha256="0" * 64,
            )
            with self.subTest(risk=risk):
                with self.assertRaisesRegex(DecisionError, "protected finding"):
                    load_decisions(
                        self.write(self.cleanup_payload("public/starter")),
                        replace(audit, findings=audit.findings + [protected]),
                        self.root,
                    )

    def test_cleanup_empty_dirs_permits_owned_children_but_rejects_operation_overlap(self) -> None:
        (self.root / "public/starter/demo").mkdir(parents=True)
        (self.root / "public/starter/demo/starter.txt").write_text("demo\n", encoding="utf-8")
        (self.root / "public/starter/samples").mkdir()
        (self.root / "public/starter/samples/sample-starter.txt").write_text(
            "sample\n", encoding="utf-8"
        )
        audit = scan_project(self.root, ["starter"])
        decisions = load_decisions(self.write(self.cleanup_payload(
            "public/starter",
            delete_paths=["public/starter/samples/sample-starter.txt"],
            rename_paths={"public/starter/demo": "public/product"},
        )), audit, self.root)
        self.assertEqual(decisions.cleanup_empty_dirs, ["public/starter"])

        for cleanup, deletes, renames in (
            ("public/starter/samples/sample-starter.txt", ["public/starter/samples/sample-starter.txt"], {}),
            ("public/starter/demo", [], {"public/starter/demo": "public/product"}),
            ("public/starter", [], {"app/demo": "public/starter"}),
        ):
            with self.subTest(cleanup=cleanup, deletes=deletes, renames=renames):
                with self.assertRaisesRegex(DecisionError, "cleanup_empty_dirs"):
                    load_decisions(
                        self.write(self.cleanup_payload(
                            cleanup, delete_paths=deletes, rename_paths=renames,
                        )),
                        audit,
                        self.root,
                    )

    def test_cleanup_empty_dirs_cannot_be_a_delete_or_rename_source(self) -> None:
        (self.root / "public/starter/samples").mkdir(parents=True)
        (self.root / "public/starter/samples/sample.txt").write_text(
            "delete\n", encoding="utf-8"
        )
        (self.root / "public/starter/samples/child-starter").mkdir()
        (self.root / "public/starter/samples/child-starter/sample.txt").write_text(
            "delete nested\n", encoding="utf-8"
        )
        (self.root / "public/starter/demo").mkdir()
        (self.root / "public/starter/demo/sample.txt").write_text(
            "rename\n", encoding="utf-8"
        )
        (self.root / "public/starter/demo/child-starter").mkdir()
        (self.root / "public/starter/demo/child-starter/sample.txt").write_text(
            "rename nested\n", encoding="utf-8"
        )
        audit = scan_project(self.root, ["starter"])

        delete_source = "public/starter/samples"
        rename_source = "public/starter/demo"
        load_decisions(
            self.write(self.cleanup_payload(delete_paths=[delete_source])), audit, self.root
        )
        load_decisions(
            self.write(self.cleanup_payload(rename_paths={rename_source: "public/product"})),
            audit,
            self.root,
        )

        for payload in (
            self.cleanup_payload(delete_source, delete_paths=[delete_source]),
            self.cleanup_payload(
                "public/starter/samples/child-starter", delete_paths=[delete_source]
            ),
            self.cleanup_payload(rename_source, rename_paths={rename_source: "public/product"}),
            self.cleanup_payload(
                "public/starter/demo/child-starter",
                rename_paths={rename_source: "public/product"},
            ),
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(DecisionError, "cleanup_empty_dirs"):
                    load_decisions(self.write(payload), audit, self.root)

    def test_cleanup_empty_dirs_rejects_ambiguous_cleanup_roots_and_destination_ancestors(self) -> None:
        (self.root / "public/starter/child-starter").mkdir(parents=True)
        audit = scan_project(self.root, ["starter"])
        with self.assertRaisesRegex(DecisionError, "cleanup_empty_dirs"):
            load_decisions(self.write(self.cleanup_payload(
                "public/starter", "public/starter/child-starter",
            )), audit, self.root)
        with self.assertRaisesRegex(DecisionError, "cleanup_empty_dirs"):
            load_decisions(self.write(self.cleanup_payload(
                "public/starter", rename_paths={"app/demo": "public/starter/new"},
            )), audit, self.root)

    def test_text_edit_requires_matching_audited_hash_and_current_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            audit = scan_project(root, ["Northstar", "starter"])
            page = next(item for item in audit.files if item.relpath == "app/demo/page.tsx")
            payload = self.base_payload()
            payload["text_edits"] = [{
                "path": page.relpath,
                "expected_sha256": page.sha256,
                "start_line": 1,
                "end_line": 1,
                "replacement": "// approved neutral heading\n",
                "reason": "Replace approved sample presentation",
            }]
            decisions = load_decisions(self.write_payload(tmp, payload), audit, root)
            self.assertEqual(decisions.text_edits[0].path, "app/demo/page.tsx")
            payload["text_edits"][0]["expected_sha256"] = "0" * 64
            with self.assertRaisesRegex(DecisionError, "text edit hash"):
                load_decisions(self.write_payload(tmp, payload), audit, root)

    def test_text_edit_rejects_p0_line_even_with_migration_and_rollback(self) -> None:
        page_finding = next(
            item for item in self.audit.findings
            if item.relpath == "app/demo/page.tsx" and item.line == 2
        )
        audit = replace(
            self.audit,
            findings=[replace(page_finding, line=1, risk=RiskLevel.P0)],
        )
        payload = self.text_edit_payload(
            audit,
            migration_plan="Migrate the public identifier before release",
            rollback_plan="Restore the audited bytes from backup",
        )
        with self.assertRaisesRegex(DecisionError, "protected P0 line"):
            load_decisions(self.write(payload), audit, self.root)

    def test_text_edit_requires_both_plans_to_overlap_p1_line(self) -> None:
        page_finding = next(
            item for item in self.audit.findings
            if item.relpath == "app/demo/page.tsx" and item.line == 2
        )
        audit = replace(
            self.audit,
            findings=[replace(page_finding, line=1, risk=RiskLevel.P1)],
        )
        for plans in (
            {},
            {"migration_plan": "Migrate the public identifier before release"},
            {"rollback_plan": "Restore the audited bytes from backup"},
            {
                "migration_plan": " ",
                "rollback_plan": "Restore the audited bytes from backup",
            },
        ):
            with self.subTest(plans=plans):
                with self.assertRaisesRegex(
                    DecisionError,
                    "P1 text edit requires migration and rollback plans",
                ):
                    load_decisions(
                        self.write(self.text_edit_payload(audit, **plans)),
                        audit,
                        self.root,
                    )

    def test_text_edit_allows_p1_line_with_both_plans(self) -> None:
        page_finding = next(
            item for item in self.audit.findings
            if item.relpath == "app/demo/page.tsx" and item.line == 2
        )
        audit = replace(
            self.audit,
            findings=[replace(page_finding, line=1, risk=RiskLevel.P1)],
        )
        payload = self.text_edit_payload(
            audit,
            migration_plan="Migrate the public identifier before release",
            rollback_plan="Restore the audited bytes from backup",
        )
        decisions = load_decisions(self.write(payload), audit, self.root)
        self.assertEqual(
            decisions.text_edits[0].migration_plan,
            "Migrate the public identifier before release",
        )
        self.assertEqual(
            decisions.text_edits[0].rollback_plan,
            "Restore the audited bytes from backup",
        )

    def test_text_edit_rejects_finding_action_overlap(self) -> None:
        finding = next(
            item for item in self.audit.findings
            if item.relpath == "messages/en.json" and item.line == 2
        )
        payload = self.text_edit_payload(
            path="messages/en.json", start_line=2, end_line=2,
        )
        payload["actions"] = [{"finding_id": finding.finding_id, "action": "keep"}]
        with self.assertRaisesRegex(DecisionError, "overlaps finding action"):
            load_decisions(self.write(payload), self.audit, self.root)

    def test_p1_text_edit_with_plans_still_rejects_finding_action_overlap(self) -> None:
        page_finding = next(
            item for item in self.audit.findings
            if item.relpath == "app/demo/page.tsx" and item.line == 2
        )
        p1_finding = replace(page_finding, line=1, risk=RiskLevel.P1)
        audit = replace(self.audit, findings=[p1_finding])
        payload = self.text_edit_payload(
            audit,
            migration_plan="Migrate the public identifier before release",
            rollback_plan="Restore the audited bytes from backup",
        )
        payload["actions"] = [{
            "finding_id": p1_finding.finding_id,
            "action": "keep",
        }]
        with self.assertRaisesRegex(DecisionError, "overlaps finding action"):
            load_decisions(self.write(payload), audit, self.root)

    def test_text_edit_rejects_overlapping_ranges(self) -> None:
        payload = self.text_edit_payload()
        payload["text_edits"].append({
            **payload["text_edits"][0], "start_line": 1, "end_line": 2,
        })
        with self.assertRaisesRegex(DecisionError, "text edits overlap"):
            load_decisions(self.write(payload), self.audit, self.root)

    def test_text_edit_rejects_nonportable_paths(self) -> None:
        for path in ("../outside.ts", "/outside.ts", "C:\\outside.ts", "app\\demo\\page.tsx"):
            with self.subTest(path=path):
                payload = self.text_edit_payload(path=path)
                with self.assertRaisesRegex(DecisionError, "text edit path"):
                    load_decisions(self.write(payload), self.audit, self.root)

    def test_text_edit_rejects_secret_legal_and_binary_paths(self) -> None:
        for path in (".env", "LICENSE"):
            with self.subTest(path=path):
                payload = self.text_edit_payload()
                payload["text_edits"][0]["path"] = path
                with self.assertRaisesRegex(DecisionError, "protected"):
                    load_decisions(self.write(payload), self.audit, self.root)
        binary_path = self.root / "asset.bin"
        binary_path.write_bytes(b"\x00binary")
        audit = scan_project(self.root, ["Northstar", "starter"])
        payload = self.base_payload()
        payload["text_edits"] = [{
            "path": "asset.bin", "expected_sha256": next(
                item.sha256 for item in audit.files if item.relpath == "asset.bin"
            ), "start_line": 1, "end_line": 1, "replacement": "neutral",
            "reason": "Replace sample binary",
        }]
        with self.assertRaisesRegex(DecisionError, "audited text file"):
            load_decisions(self.write(payload), audit, self.root)

    def test_text_edit_rejects_missing_audit_file_and_unknown_keys(self) -> None:
        payload = self.text_edit_payload()
        payload["text_edits"][0]["path"] = "missing.ts"
        with self.assertRaisesRegex(DecisionError, "audited text file"):
            load_decisions(self.write(payload), self.audit, self.root)
        payload = self.text_edit_payload(extra=True)
        with self.assertRaisesRegex(DecisionError, "unknown text edit keys"):
            load_decisions(self.write(payload), self.audit, self.root)

    def test_text_edit_requires_reason_and_string_replacement(self) -> None:
        with self.assertRaisesRegex(DecisionError, "reason"):
            load_decisions(
                self.write(self.text_edit_payload(reason=" ")),
                self.audit,
                self.root,
            )
        with self.assertRaisesRegex(DecisionError, "replacement"):
            load_decisions(
                self.write(self.text_edit_payload(replacement=["neutral"])),
                self.audit,
                self.root,
            )

    def test_text_edit_rejects_invalid_ranges(self) -> None:
        for changes in (
            {"start_line": 0}, {"start_line": True}, {"end_line": 0},
            {"start_line": 2, "end_line": 1}, {"end_line": 4},
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(DecisionError, "text edit"):
                    load_decisions(
                        self.write(self.text_edit_payload(**changes)),
                        self.audit,
                        self.root,
                    )

    def test_text_edit_rejects_stale_current_hash(self) -> None:
        payload = self.text_edit_payload()
        (self.root / "app/demo/page.tsx").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(DecisionError, "current file"):
            load_decisions(self.write(payload), self.audit, self.root)

    def test_text_edit_requires_project_root(self) -> None:
        with self.assertRaisesRegex(DecisionError, "require project_root"):
            load_decisions(self.write(self.text_edit_payload()), self.audit)

    def test_text_edit_rejects_symlinked_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            target = root / "outside.ts"
            target.write_text("export default 'outside';\n", encoding="utf-8")
            page = root / "app/demo/page.tsx"
            page.unlink()
            page.symlink_to(target)
            audit = scan_project(root, ["Northstar", "starter"])
            payload = self.text_edit_payload(audit)
            with self.assertRaisesRegex(DecisionError, "symlink"):
                load_decisions(self.write_payload(tmp, payload), audit, root)

    def test_real_brand_requires_all_fields(self) -> None:
        path = self.write({"brand_mode": "real", "brand_profile": {"product_name": "Nova"}, "actions": []})
        with self.assertRaisesRegex(DecisionError, "missing brand fields"):
            load_decisions(path, self.audit)

    def test_p0_action_is_rejected(self) -> None:
        finding = next(item for item in self.audit.findings if item.risk.value == "P0")
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{"finding_id": finding.finding_id, "action": "replace", "replacement": "Nova"}],
        })
        with self.assertRaisesRegex(DecisionError, "P0"):
            load_decisions(path, self.audit)

    def test_p1_requires_migration_and_rollback(self) -> None:
        finding = next(item for item in self.audit.findings if item.risk.value == "P1")
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{"finding_id": finding.finding_id, "action": "replace", "replacement": "nova_monthly"}],
        })
        with self.assertRaisesRegex(DecisionError, "migration"):
            load_decisions(path, self.audit)

    def test_placeholder_mode_supplies_neutral_profile(self) -> None:
        path = self.write({"brand_mode": "placeholder", "brand_profile": {}, "actions": []})
        decisions = load_decisions(path, self.audit)
        self.assertEqual(decisions.brand_profile["product_name"], "Your Product")
        self.assertEqual(decisions.brand_profile["domain"], "example.com")

    def test_delete_path_cannot_contain_p0_or_p1_findings(self) -> None:
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "delete_paths": ["LICENSE"],
        })
        with self.assertRaisesRegex(DecisionError, "protected finding"):
            load_decisions(path, self.audit)

    def test_rename_paths_must_stay_inside_project(self) -> None:
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "rename_paths": {"app/demo": "../escaped"},
        })
        with self.assertRaisesRegex(DecisionError, "rename_paths"):
            load_decisions(path, self.audit)

    def test_path_findings_cannot_use_text_replace(self) -> None:
        path_finding = next(item for item in self.audit.findings if item.line == 0)
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{
                "finding_id": path_finding.finding_id,
                "action": "replace",
                "replacement": "renamed",
            }],
        })
        with self.assertRaisesRegex(DecisionError, "rename_paths"):
            load_decisions(path, self.audit)

    def test_real_brand_rejects_blank_values(self) -> None:
        profile = {
            "product_name": "Nova", "short_name": "Nova", "url": "https://nova.example",
            "domain": "nova.example", "support_email": " ",
            "repository_url": "https://github.com/acme/nova", "owner": "Acme",
        }
        with self.assertRaisesRegex(DecisionError, "missing brand fields"):
            load_decisions(self.write({"brand_mode": "real", "brand_profile": profile, "actions": []}), self.audit)

    def test_placeholder_profile_cannot_override_required_value_with_blank(self) -> None:
        with self.assertRaisesRegex(DecisionError, "brand_profile"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {"domain": " "}, "actions": [],
            }), self.audit)

    def test_duplicate_and_conflicting_actions_are_rejected(self) -> None:
        finding = next(item for item in self.audit.findings if item.risk.value == "P3")
        with self.assertRaisesRegex(DecisionError, "duplicate action"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {},
                "actions": [
                    {"finding_id": finding.finding_id, "action": "keep"},
                    {"finding_id": finding.finding_id, "action": "replace", "replacement": "Nova"},
                ],
            }), self.audit)

    def test_rejects_unknown_top_level_keys_and_invalid_action_shape(self) -> None:
        with self.assertRaisesRegex(DecisionError, "unknown decision keys"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [], "surprise": True,
            }), self.audit)
        with self.assertRaisesRegex(DecisionError, "actions must"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": {},
            }), self.audit)

    def test_rename_paths_cannot_target_another_rename_source(self) -> None:
        with self.assertRaisesRegex(DecisionError, "rename_paths"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                "rename_paths": {"app/demo": "app/showcase", "app/showcase": "app/archive"},
            }), self.audit)

    def test_rejects_non_portable_or_empty_project_paths(self) -> None:
        unsafe_paths = ["/escaped", "\\\\server\\share", "C:escaped", "C:\\escaped", "app\\demo", ".", ""]
        for unsafe_path in unsafe_paths:
            with self.subTest(unsafe_path=unsafe_path):
                with self.assertRaisesRegex(DecisionError, "delete_paths"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                        "delete_paths": [unsafe_path],
                    }), self.audit)

    def test_rejects_legal_and_ignored_roots_without_audit_findings(self) -> None:
        empty_audit = scan_project(self.root, [])
        for path in ["LICENSE.md", "docs/NOTICE", ".git/config", "node_modules/pkg", "build/output"]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(DecisionError, "protected"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                        "delete_paths": [path],
                    }), empty_audit)

    def test_filesystem_operations_require_an_audited_scope(self) -> None:
        with self.assertRaisesRegex(DecisionError, "audited P2"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                "delete_paths": ["untracked"],
            }), self.audit)
        with self.assertRaisesRegex(DecisionError, "audited"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                "rename_paths": {"untracked": "renamed"},
            }), self.audit)
        decisions = load_decisions(self.write({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
            "rename_paths": {"app/demo": "app/showcase"},
        }), self.audit)
        self.assertEqual(decisions.rename_paths, {"app/demo": "app/showcase"})

    def test_rejects_normalized_path_collisions_and_duplicate_json_keys(self) -> None:
        with self.assertRaisesRegex(DecisionError, "duplicates"):
            load_decisions(self.write({
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                "rename_paths": {"app/demo": "app/showcase", "app//demo": "app/archive"},
            }), self.audit)
        with self.assertRaisesRegex(DecisionError, "duplicate JSON key"):
            load_decisions(self.write_raw(
                b'{"brand_mode":"placeholder","brand_mode":"real","brand_profile":{},"actions":[]}'
            ), self.audit)
        with self.assertRaisesRegex(DecisionError, "duplicate JSON key"):
            load_decisions(self.write_raw(
                b'{"brand_mode":"placeholder","brand_profile":{},"actions":[],"rename_paths":{"app/demo":"app/showcase","app/demo":"app/archive"}}'
            ), self.audit)

    def test_invalid_json_encoding_and_container_types_raise_decision_error(self) -> None:
        with self.assertRaisesRegex(DecisionError, "invalid decisions JSON"):
            load_decisions(self.write_raw(b'\xff'), self.audit)
        for value in ([], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(DecisionError, "brand_mode"):
                    load_decisions(self.write({
                        "brand_mode": value, "brand_profile": {}, "actions": [],
                    }), self.audit)
        finding = next(item for item in self.audit.findings if item.risk.value == "P3")
        for value in ([], {}):
            with self.subTest(action=value):
                with self.assertRaisesRegex(DecisionError, "action must"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {},
                        "actions": [{"finding_id": finding.finding_id, "action": value}],
                    }), self.audit)

    def test_filesystem_scope_cannot_expand_beyond_its_exact_audited_root(self) -> None:
        for operation in ("delete", "rename"):
            with self.subTest(operation=operation):
                payload = {"brand_mode": "placeholder", "brand_profile": {}, "actions": []}
                if operation == "delete":
                    payload["delete_paths"] = ["app"]
                else:
                    payload["rename_paths"] = {"app": "showcase"}
                with self.assertRaisesRegex(DecisionError, "audited"):
                    load_decisions(self.write(payload), self.audit)
        decisions = load_decisions(self.write({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
            "delete_paths": ["app/demo"],
        }), self.audit)
        self.assertEqual(decisions.delete_paths, ["app/demo"])

    def test_rename_allows_audited_nested_p2_directory_root(self) -> None:
        (self.root / "public/demo/gallery").mkdir(parents=True)
        (self.root / "public/demo/video").mkdir(parents=True)
        (self.root / "public/demo/gallery/cover.png").write_bytes(b"cover")
        (self.root / "public/demo/video/clip.mp4").write_bytes(b"clip")
        audit = scan_project(self.root, ["Northstar", "starter_monthly"])

        decisions = load_decisions(self.write({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
            "rename_paths": {"public/demo": "public/product"},
        }), audit)

        self.assertEqual(decisions.rename_paths, {"public/demo": "public/product"})

    def test_rename_allows_audited_nested_path_finding_root(self) -> None:
        (self.root / "assets/Northstar/gallery").mkdir(parents=True)
        (self.root / "assets/Northstar/video").mkdir(parents=True)
        (self.root / "assets/Northstar/gallery/cover.bin").write_bytes(b"cover")
        (self.root / "assets/Northstar/video/clip.bin").write_bytes(b"clip")
        audit = scan_project(self.root, ["Northstar", "starter_monthly"])

        decisions = load_decisions(self.write({
            "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
            "rename_paths": {"assets/Northstar": "assets/product"},
        }), audit)

        self.assertEqual(
            decisions.rename_paths,
            {"assets/Northstar": "assets/product"},
        )

    def test_rename_destinations_cannot_target_protected_roots(self) -> None:
        for destination in [".git/destarter", "docs/NOTICE", "node_modules/output", "build/output", ".cache/output"]:
            with self.subTest(destination=destination):
                with self.assertRaisesRegex(DecisionError, "protected"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                        "rename_paths": {"app/demo": destination},
                    }), self.audit)

    def test_rejects_windows_normalized_trailing_dot_or_whitespace_paths(self) -> None:
        for unsafe_path in [".git.", ".git ", "node_modules.", "app/demo. "]:
            with self.subTest(destination=unsafe_path):
                with self.assertRaisesRegex(DecisionError, "stay inside the project"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                        "rename_paths": {"app/demo": unsafe_path},
                    }), self.audit)
        for unsafe_path in ["app/demo.", "app/demo "]:
            with self.subTest(delete=unsafe_path):
                with self.assertRaisesRegex(DecisionError, "stay inside the project"):
                    load_decisions(self.write({
                        "brand_mode": "placeholder", "brand_profile": {}, "actions": [],
                        "delete_paths": [unsafe_path],
                    }), self.audit)


if __name__ == "__main__":
    unittest.main()
