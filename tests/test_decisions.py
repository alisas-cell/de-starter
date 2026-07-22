from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import DecisionError, load_decisions
from destarter_lib.models import RiskLevel
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
