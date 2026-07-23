from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = REPO_ROOT / "examples" / "public-demo" / "demo.py"
CLI = REPO_ROOT / "skills" / "de-starter" / "scripts" / "destarter.py"
SOURCE_EXAMPLE = REPO_ROOT / "examples" / "public-demo" / "source-config.example.json"
DECISIONS_EXAMPLE = REPO_ROOT / "examples" / "public-demo" / "decisions.example.json"


def load_demo():
    spec = spec_from_file_location("de_starter_public_demo", DEMO_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load public demo helper")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicDemoWorkspaceTests(unittest.TestCase):
    def test_prepare_creates_owned_disjoint_demo_and_expected_empty_directories(self):
        self.assertTrue(DEMO_PATH.is_file(), "public demo helper is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"

            result = demo.prepare_workspace(workspace)

            self.assertEqual(Path(result["project"]), (workspace / "project").resolve())
            self.assertEqual(Path(result["run_dir"]), (workspace / "run").resolve())
            self.assertNotEqual(Path(result["project"]), Path(result["run_dir"]))
            self.assertTrue((workspace / "project" / "public" / "starter").is_dir())
            self.assertTrue((workspace / "project" / "public" / "uploads").is_dir())
            self.assertTrue((workspace / ".de-starter-public-demo.json").is_file())
            self.assertTrue((workspace / "baseline-inventory.json").is_file())
            sentinel = json.loads(
                (workspace / ".de-starter-public-demo.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                sentinel,
                {"kind": "de-starter-public-demo", "version": 1},
            )

    def test_prepare_refuses_nonempty_unowned_destination(self):
        self.assertTrue(DEMO_PATH.is_file(), "public demo helper is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            workspace.mkdir()
            foreign = workspace / "foreign.txt"
            foreign.write_text("keep\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "empty|owned"):
                demo.prepare_workspace(workspace)

            self.assertEqual(foreign.read_text(encoding="utf-8"), "keep\n")

    def test_reset_requires_exact_sentinel_and_keeps_unowned_directory(self):
        self.assertTrue(DEMO_PATH.is_file(), "public demo helper is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            workspace.mkdir()
            foreign = workspace / "foreign.txt"
            foreign.write_text("keep\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sentinel"):
                demo.reset_workspace(workspace)

            self.assertTrue(workspace.is_dir())
            self.assertEqual(foreign.read_text(encoding="utf-8"), "keep\n")

    def test_reset_removes_only_a_prepared_workspace(self):
        self.assertTrue(DEMO_PATH.is_file(), "public demo helper is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            sibling = parent / "keep"
            sibling.mkdir()
            workspace = parent / "lab"
            demo.prepare_workspace(workspace)

            demo.reset_workspace(workspace)

            self.assertFalse(workspace.exists())
            self.assertTrue(sibling.is_dir())

    def test_inventory_is_stable_and_contains_only_project_relative_paths(self):
        self.assertTrue(DEMO_PATH.is_file(), "public demo helper is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            demo.prepare_workspace(workspace)

            first = demo.inventory_project(workspace)
            second = demo.inventory_project(workspace)

            self.assertEqual(first, second)
            self.assertIn("LICENSE", first["files"])
            self.assertIn("public/starter", first["directories"])
            self.assertIn("public/uploads", first["directories"])
            self.assertTrue(all(not Path(path).is_absolute() for path in first["files"]))
            self.assertTrue(all(not Path(path).is_absolute() for path in first["directories"]))


class PublicDemoLifecycleTests(unittest.TestCase):
    def run_cli(self, *args, expected=None):
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def prepare_audit(self, workspace):
        self.assertTrue(SOURCE_EXAMPLE.is_file(), "source-config example is missing")
        demo = load_demo()
        demo.prepare_workspace(workspace)
        project = workspace.resolve() / "project"
        run = workspace.resolve() / "run"
        self.run_cli(
            "discover", "--project", str(project), "--run-dir", str(run), expected=0,
        )
        shutil.copy2(SOURCE_EXAMPLE, run / "source-config.json")
        self.run_cli(
            "audit", "--project", str(project), "--run-dir", str(run),
            "--source-config", str(run / "source-config.json"), expected=0,
        )
        return demo, project, run

    def test_example_decisions_match_the_fixed_seed_audit(self):
        self.assertTrue(DECISIONS_EXAMPLE.is_file(), "decisions example is missing")
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            _, _, run = self.prepare_audit(workspace)
            audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
            decisions = json.loads(DECISIONS_EXAMPLE.read_text(encoding="utf-8"))
            finding_ids = {item["finding_id"] for item in audit["findings"]}

            self.assertTrue(
                {item["finding_id"] for item in decisions["actions"]} <= finding_ids
            )
            self.assertEqual(decisions["delete_paths"], ["app/demo"])
            self.assertEqual(
                decisions["rename_paths"],
                {"public/starter-logo.svg": "public/product-logo.svg"},
            )
            self.assertEqual(decisions["cleanup_empty_dirs"], ["public/starter"])
            self.assertEqual(decisions["text_edits"], [])
            self.assertFalse(
                any(
                    next(
                        item for item in audit["findings"]
                        if item["finding_id"] == action["finding_id"]
                    )["risk"] in {"P0", "P1"}
                    for action in decisions["actions"]
                )
            )

    def test_documented_success_lifecycle_changes_only_approved_scope(self):
        self.assertTrue(DECISIONS_EXAMPLE.is_file(), "decisions example is missing")
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            _, project, run = self.prepare_audit(workspace)
            before = demo.inventory_project(workspace)
            license_before = (project / "LICENSE").read_bytes()
            shutil.copy2(DECISIONS_EXAMPLE, run / "decisions.json")
            preview = self.run_cli(
                "preview", "--project", str(project), "--run-dir", str(run),
                "--decisions", str(run / "decisions.json"), expected=0,
            )
            token = preview.stdout.strip().splitlines()[-1]

            self.run_cli(
                "apply", "--project", str(project), "--run-dir", str(run),
                "--approval-token", token, expected=0,
            )
            verification = self.run_cli(
                "verify", "--project", str(project), "--run-dir", str(run),
                "--source-config", str(run / "source-config.json"), expected=3,
            )
            result = demo.check_applied(workspace)

            self.assertEqual(result["status"], "approved-scope-verified")
            self.assertNotEqual(demo.inventory_project(workspace), before)
            self.assertEqual((project / "LICENSE").read_bytes(), license_before)
            self.assertEqual(
                json.loads((project / "messages/en.json").read_text(encoding="utf-8"))["plan"],
                "starter_monthly",
            )
            self.assertFalse((project / "app/demo").exists())
            self.assertFalse((project / "public/starter").exists())
            self.assertTrue((project / "public/uploads").is_dir())
            self.assertTrue((project / "public/product-logo.svg").is_file())
            self.assertIn("remaining", verification.stdout.lower())
            for artifact in ("backup", "restore.json", "reverse.diff", "apply-result.json"):
                self.assertTrue((run / artifact).exists(), artifact)


if __name__ == "__main__":
    unittest.main()
