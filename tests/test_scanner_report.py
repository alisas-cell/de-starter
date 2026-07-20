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
