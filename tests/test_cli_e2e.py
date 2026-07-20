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
            self.assertEqual(verified.returncode, 3, verified.stderr)
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
            self.assertIn("audit does not match current scan", stale.stderr)
            self.assertFalse((run / "preview").exists())
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            audit["findings"][0]["risk"] = "P9"
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            tampered = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("invalid audit risk", tampered.stderr.lower())
            self.assertNotIn("traceback", tampered.stderr.lower())

    def test_preview_requires_audit_to_match_fresh_scan_before_decisions(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "settings.py").write_text(
                'API_TOKEN = "live-secret-value"\nNorthstar PLAN_ID = "plan_123"\n', encoding="utf-8"
            )
            run = base / "run"
            source = self.write_json(base / "source.json", {"source_terms": ["Northstar"]})
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            secret = next(item for item in audit["findings"] if item["category"] == "possible-secret")
            secret["risk"] = "P3"
            p1 = next(item for item in audit["findings"] if item["risk"] == "P1" and item["relpath"] == "settings.py")
            p1["risk"] = "P3"
            fabricated = dict(secret, finding_id="F-fabricated", relpath="app/demo/page.tsx", line=0, column=0,
                              category="user-decides-sample-content", risk="P2", matched="<path>", evidence="inventory")
            audit["findings"].append(fabricated)
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            decisions = self.write_json(base / "decisions.json", {
                "brand_mode": "placeholder", "brand_profile": {},
                "actions": [{"finding_id": secret["finding_id"], "action": "replace", "replacement": "SAFE"}],
                "delete_paths": ["app/demo"],
            })
            result = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("audit does not match current scan", result.stderr)
            self.assertFalse((run / "preview").exists())
            applied = self.run_cli("apply", "--project", str(root), "--run-dir", str(run), "--approval-token", "attacker-token")
            self.assertNotEqual(applied.returncode, 0)
            self.assertEqual((root / "settings.py").read_text(encoding="utf-8"), 'API_TOKEN = "live-secret-value"\nNorthstar PLAN_ID = "plan_123"\n')

    def test_artifact_symlinks_never_write_their_targets(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run = base / "run"
            victim = root / "victim.txt"
            victim.write_text("untouched", encoding="utf-8")
            run.mkdir()
            os.symlink(victim, run / "discovery.json")
            self.assertEqual(self.run_cli("discover", "--project", str(root), "--run-dir", str(run)).returncode, 0)
            self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
            (run / "discovery.json").unlink()
            source = self.write_json(base / "source.json", {"source_terms": ["Northstar"]})
            os.symlink(victim, run / "audit.json")
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
            (run / "audit.json").unlink()
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            decisions = self.write_json(base / "decisions.json", {"brand_mode": "placeholder", "brand_profile": {}, "actions": []})
            os.symlink(victim, run / "preview.diff")
            self.assertEqual(self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions)).returncode, 0)
            self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
            (run / "preview.diff").unlink()
            self.assertEqual(self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions)).returncode, 0)
            token = json.loads((run / "manifest.json").read_text(encoding="utf-8"))["approval_token"]
            os.symlink(victim, run / "apply-result.json")
            self.assertEqual(self.run_cli("apply", "--project", str(root), "--run-dir", str(run), "--approval-token", token).returncode, 0)
            self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
            os.symlink(root, run / "verification")
            verified = self.run_cli("verify", "--project", str(root), "--run-dir", str(run), "--source-config", str(source))
            self.assertNotEqual(verified.returncode, 0)
            self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")

    def test_controlled_errors_and_strict_numeric_audit_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run = base / "run"
            source = self.write_json(base / "source.json", {"source_terms": ["Northstar"]})
            self.assertEqual(self.run_cli("audit", "--project", str(root), "--run-dir", str(run), "--source-config", str(source)).returncode, 0)
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            decisions = self.write_json(base / "decisions.json", {"brand_mode": "attacker-brand", "brand_profile": {}, "actions": []})
            decision_error = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(decision_error.returncode, 0)
            self.assertNotIn("attacker-brand", decision_error.stderr)
            self.assertNotIn("traceback", decision_error.stderr.lower())
            audit["files"][0]["size"] = True
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            result = self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("attacker-brand", result.stderr)
            self.assertNotIn("traceback", result.stderr.lower())
            audit["files"][0]["size"] = -1
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            self.assertNotEqual(self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions)).returncode, 0)
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            audit["files"][0]["size"] = 1
            audit["findings"][0]["line"] = True
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            self.assertNotEqual(self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions)).returncode, 0)
            audit["findings"][0]["line"] = 0
            audit["findings"][0]["column"] = -1
            (run / "audit.json").write_text(json.dumps(audit), encoding="utf-8")
            self.assertNotEqual(self.run_cli("preview", "--project", str(root), "--run-dir", str(run), "--decisions", str(decisions)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
