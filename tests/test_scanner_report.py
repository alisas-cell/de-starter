from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.report import write_audit_reports
from destarter_lib.scanner import scan_project


class ScannerReportTests(unittest.TestCase):
    def test_source_named_empty_directory_has_one_separate_directory_finding(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public" / "starter").mkdir(parents=True)

            audit = scan_project(root, ["starter"])

            self.assertEqual([record.relpath for record in audit.directories], ["public", "public/starter"])
            self.assertEqual(len(audit.findings), 0)
            self.assertEqual(len(audit.directory_findings), 1)
            finding = audit.directory_findings[0]
            directory = next(record for record in audit.directories if record.relpath == "public/starter")
            self.assertEqual(finding.relpath, "public/starter")
            self.assertEqual(finding.line, 0)
            self.assertEqual(finding.category, "directory-name")
            self.assertEqual(finding.sha256, directory.state_sha256)

    def test_non_empty_source_named_directory_is_found_separately_from_child_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "public" / "starter-assets" / "starter-child.txt"
            child.parent.mkdir(parents=True)
            child.write_text("neutral child", encoding="utf-8")

            audit = scan_project(root, ["starter"])

            self.assertIn("public", [record.relpath for record in audit.directories])
            self.assertEqual(
                [finding.relpath for finding in audit.directory_findings],
                ["public/starter-assets"],
            )
            self.assertEqual(
                [finding.relpath for finding in audit.findings],
                ["public/starter-assets/starter-child.txt"] * 2,
            )
            self.assertEqual(len(audit.findings), 2)
            self.assertEqual(len(audit.directory_findings), 1)

    def test_reports_directory_inventory_and_findings_separately(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public" / "starter").mkdir(parents=True)
            audit = scan_project(root, ["starter"])
            run_dir = root / "run"

            write_audit_reports(audit, run_dir)

            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            self.assertEqual(payload["findings"], [])
            self.assertEqual(len(payload["directories"]), 2)
            self.assertEqual(len(payload["directory_findings"]), 1)
            self.assertIn("## Directory residue", rendered)
            self.assertIn("public/starter", rendered)

    def test_context_changes_risk_for_same_term(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            audit = scan_project(root, ["Northstar", "starter_monthly"])
            risks = {(item.relpath, item.matched): item.risk.value for item in audit.findings}
            self.assertEqual(risks[("LICENSE", "Northstar")], "P0")
            self.assertEqual(risks[("messages/en.json", "starter_monthly")], "P1")
            self.assertEqual(risks[("app/demo/page.tsx", "Northstar")], "P2")
            self.assertEqual(risks[("messages/en.json", "Northstar")], "P3")

    def test_report_does_not_include_hardcoded_secret_value(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const NORTHSTAR_API_TOKEN = "live-secret-value"; // Northstar\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            secret_finding = next(
                item for item in audit.findings
                if item.category == "possible-secret"
            )
            self.assertEqual(secret_finding.risk.value, "P0")
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertNotIn("live-secret-value", rendered)
            self.assertNotIn("live-secret-value", json.dumps(payload))

    def test_typed_typescript_secret_is_p0_and_redacted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const NORTHSTAR_API_TOKEN: string = "typed-live-secret-value"; // Northstar\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            secret_finding = next(
                item for item in audit.findings
                if item.category == "possible-secret"
            )
            self.assertEqual(secret_finding.risk.value, "P0")
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertNotIn("typed-live-secret-value", rendered)
            self.assertNotIn("typed-live-secret-value", json.dumps(payload))

    def test_escaped_quote_secret_is_p0_and_redacted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const NORTHSTAR_PASSWORD = "' + ("\\" * 3)
                + '"escaped-live-secret-value"; // Northstar\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            secret_finding = next(
                item for item in audit.findings
                if item.category == "possible-secret"
            )
            self.assertEqual(secret_finding.risk.value, "P0")
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertNotIn("escaped-live-secret-value", rendered)
            self.assertNotIn("escaped-live-secret-value", json.dumps(payload))

    def test_unquoted_secret_is_p0_and_redacted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.sh").write_text(
                "export NORTHSTAR_API_TOKEN=unquoted-live-secret-value # Northstar\n",
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            secret_finding = next(
                item for item in audit.findings
                if item.category == "possible-secret"
            )
            self.assertEqual(secret_finding.risk.value, "P0")
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertNotIn("unquoted-live-secret-value", rendered)
            self.assertNotIn("unquoted-live-secret-value", json.dumps(payload))

    def test_repeated_secret_identifier_on_one_line_has_unique_ids(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const API_TOKEN = "first-live-secret"; '
                'const API_TOKEN = "second-live-secret";\n',
                encoding="utf-8",
            )
            audit = scan_project(root, [])
            secrets = [
                item for item in audit.findings
                if item.category == "possible-secret"
            ]
            self.assertEqual(len(secrets), 2)
            self.assertEqual(len({item.finding_id for item in secrets}), 2)
            self.assertEqual(len({item.column for item in secrets}), 2)

    def test_later_live_secret_is_not_hidden_by_example_assignment(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const SAMPLE_API_TOKEN = "example-token-value"; '
                'const LIVE_API_TOKEN = "later-live-secret-value";\n',
                encoding="utf-8",
            )
            audit = scan_project(root, [])
            secrets = [
                item for item in audit.findings
                if item.category == "possible-secret"
            ]
            self.assertEqual([item.matched for item in secrets], ["LIVE_API_TOKEN"])
            self.assertEqual(secrets[0].risk.value, "P0")

    def test_case_variant_terms_do_not_duplicate_ids_and_equal_terms_sort(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            audit = scan_project(root, ["zulu", "Alpha", "Northstar", "northstar"])
            self.assertEqual(audit.source_terms, ["Northstar", "Alpha", "zulu"])
            northstar_findings = [
                item for item in audit.findings
                if item.relpath == "messages/en.json" and item.matched == "Northstar"
            ]
            self.assertEqual(len(northstar_findings), 1)
            self.assertEqual(
                len({item.finding_id for item in audit.findings}), len(audit.findings)
            )

    def test_reports_all_path_occurrences_and_orders_json_by_risk(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            nested = root / "northstar" / "northstar-logo.txt"
            nested.parent.mkdir()
            nested.write_text("no source terms here\n", encoding="utf-8")
            audit = scan_project(root, ["Northstar", "starter_monthly"])
            path_findings = [
                item for item in audit.findings
                if item.relpath == "northstar/northstar-logo.txt"
            ]
            self.assertEqual([item.column for item in path_findings], [1, 11])
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [item["risk"] for item in payload["findings"]],
                sorted(item["risk"] for item in payload["findings"]),
            )

    def test_binary_demo_asset_is_inventoried_as_p2(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / "public" / "demo" / "sample.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, ["Northstar"])
            finding = next(item for item in audit.findings if item.relpath == "public/demo/sample.png")
            self.assertEqual(finding.risk.value, "P2")
            self.assertIn("binary-or-path inventory", finding.evidence)

    def test_hyphenated_demo_directory_is_inventoried_as_p2(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / ".asset-sources" / "starter-demo" / "still.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, ["Northstar"])
            finding = next(
                item for item in audit.findings
                if item.relpath == ".asset-sources/starter-demo/still.png"
            )
            self.assertEqual(finding.risk.value, "P2")
            self.assertIn("binary-or-path inventory", finding.evidence)

    def test_concatenated_sample_media_filename_is_inventoried_as_p2(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / "public" / "samplegallery.png"
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, [])
            finding = next(
                item for item in audit.findings
                if item.relpath == "public/samplegallery.png"
            )
            self.assertEqual(finding.risk.value, "P2")
            self.assertIn("binary-or-path inventory", finding.evidence)

    def test_sample_prefix_does_not_classify_source_file_as_p2(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            source = root / "src" / "sampler.ts"
            source.parent.mkdir(exist_ok=True)
            source.write_text("const marker = 'neutral';\n", encoding="utf-8")
            audit = scan_project(root, ["marker"])
            finding = next(
                item for item in audit.findings
                if item.relpath == "src/sampler.ts" and item.matched == "marker"
            )
            self.assertEqual(finding.risk.value, "P3")

    def test_brand_in_binary_filename_is_reported(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / "public" / "northstar-logo.png"
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, ["Northstar"])
            finding = next(
                item for item in audit.findings
                if item.relpath == "public/northstar-logo.png"
            )
            self.assertEqual(finding.risk.value, "P3")
            self.assertEqual(finding.category, "file-or-directory-name")


if __name__ == "__main__":
    unittest.main()
