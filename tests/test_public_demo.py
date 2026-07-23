from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = REPO_ROOT / "examples" / "public-demo" / "demo.py"


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


if __name__ == "__main__":
    unittest.main()
