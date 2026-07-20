from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
import sys
import unittest

from tests.support import REPO_ROOT, copy_fixture


CLI = REPO_ROOT / "skills" / "de-starter" / "scripts" / "destarter.py"


class CliEndToEndTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args], text=True,
            capture_output=True, check=False,
        )

    def write_json(self, path: Path, payload: object) -> Path:
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_full_lifecycle_is_safe_and_writes_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run = base / "run"
            discovered = self.run_cli("discover", "--project", str(root), "--run-dir", str(run))
            self.assertEqual(discovered.returncode, 0, discovered.stderr)
            self.assertTrue((run / "discovery.json").is_file())
            source = self.write_json(base / "source.json", {"source_terms": ["Northstar", "demo"]})
            audited = self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source))
            self.assertEqual(audited.returncode, 0, audited.stderr)
            self.assertTrue((run / "audit.json").is_file())
            self.assertTrue((run / "audit.md").is_file())
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            finding = next(item for item in audit["findings"] if item["relpath"] == "messages/en.json" and item["risk"] == "P3")
            decisions = self.write_json(base / "decisions.json", {
                "brand_mode": "placeholder", "brand_profile": {}, "actions": [{
                    "finding_id": finding["finding_id"], "action": "replace", "replacement": "Your Product",
                }],
            })
            preview = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertEqual(preview.returncode, 0, preview.stderr)
            token = preview.stdout.strip().splitlines()[-1]
            before = (root / "messages/en.json").read_text(encoding="utf-8")
            rejected = self.run_cli("apply", "--project", str(root), "--run-dir", str(run), "--approval-token", "wrong")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("approval", rejected.stderr.lower())
            self.assertEqual((root / "messages/en.json").read_text(encoding="utf-8"), before)
            applied = self.run_cli("apply", "--project", str(root), "--run-dir", str(run), "--approval-token", token)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue((run / "apply-result.json").is_file())
            verified = self.run_cli("verify", "--project", str(root), "--run-dir", str(run), "--source-config", str(source))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertTrue((run / "verification" / "audit.json").is_file())
            self.assertIn("remaining", verified.stdout.lower())

    def test_rejects_internal_ancestor_and_symlink_run_dirs_without_writes(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            for run in (root / ".destarter", base, base / "linked"):
                if run.name == "linked":
                    os.symlink(base / "outside", run)
                with self.subTest(run=run):
                    result = self.run_cli("discover", "--project", str(root), "--run-dir", str(run))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("run directory", result.stderr.lower())
                    self.assertFalse((root / ".destarter").exists())

    def test_rejects_invalid_or_secret_bearing_inputs_without_traceback(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run = base / "run"
            bad_source = (base / "source.json")
            bad_source.write_text('{"source_terms":["Northstar"],"source_terms":["leak-secret"]}', encoding="utf-8")
            result = self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(bad_source))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("traceback", result.stderr.lower())
            self.assertNotIn("leak-secret", result.stderr)
            self.assertFalse(run.exists())
            (root / "secret.py").write_text('TOKEN = "live-cli-secret"\n', encoding="utf-8")
            source = self.write_json(base / "good.json", {"source_terms": ["Northstar"]})
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            (run / "audit.json").write_text('{"project":{},"source_terms":[],"findings":[],"files":[]}', encoding="utf-8")
            preview = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(source))
            self.assertNotEqual(preview.returncode, 0)
            self.assertNotIn("traceback", preview.stderr.lower())
            self.assertNotIn("live-cli-secret", preview.stderr)

    def test_preview_rejects_stale_and_tampered_audit_without_mutating_project(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run = base / "run"
            source = self.write_json(base / "source.json", {"source_terms": ["Northstar"]})
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            original = (root / "messages/en.json").read_text(encoding="utf-8")
            (root / "messages/en.json").write_text(original + "\n// changed", encoding="utf-8")
            decisions = self.write_json(base / "decisions.json", {"brand_mode": "placeholder", "brand_profile": {}, "actions": []})
            stale = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("stale audit", stale.stderr.lower())
            self.assertFalse((run / "preview").exists())
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            audit["findings"][0]["risk"] = "P9"
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            tampered = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("invalid audit risk", tampered.stderr.lower())
            self.assertNotIn("traceback", tampered.stderr.lower())


if __name__ == "__main__":
    unittest.main()
