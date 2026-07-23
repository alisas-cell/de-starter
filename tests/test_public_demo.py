from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import shutil
import subprocess
import struct
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
                {
                    "kind": "de-starter-public-demo",
                    "version": 1,
                    "workspace": str(workspace.resolve()),
                },
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

    def test_reset_refuses_a_sentinel_copied_to_another_workspace(self):
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            parent = Path(tmp)
            original = parent / "original"
            copied = parent / "copied"
            demo.prepare_workspace(original)
            shutil.copytree(original, copied)

            with self.assertRaisesRegex(ValueError, "identity|workspace"):
                demo.reset_workspace(copied)

            self.assertTrue(original.is_dir())
            self.assertTrue(copied.is_dir())

    def test_reset_refuses_an_unknown_top_level_entry(self):
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            demo.prepare_workspace(workspace)
            foreign = workspace / "foreign.txt"
            foreign.write_text("keep\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unexpected"):
                demo.reset_workspace(workspace)

            self.assertTrue(workspace.is_dir())
            self.assertEqual(foreign.read_text(encoding="utf-8"), "keep\n")

    def test_prepare_refuses_a_workspace_inside_the_repository(self):
        demo = load_demo()
        with self.assertRaisesRegex(ValueError, "inside the repository"):
            demo._safe_workspace_path(REPO_ROOT / "would-be-public-demo")

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


class PublicDemoCliMixin:
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


class PublicDemoLifecycleTests(PublicDemoCliMixin, unittest.TestCase):
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


class PublicDemoRefusalTests(PublicDemoCliMixin, unittest.TestCase):
    def prepare_preview(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        workspace = Path(temporary.name) / "lab"
        _, project, run = self.prepare_audit(workspace)
        shutil.copy2(DECISIONS_EXAMPLE, run / "decisions.json")
        preview = self.run_cli(
            "preview", "--project", str(project), "--run-dir", str(run),
            "--decisions", str(run / "decisions.json"), expected=0,
        )
        token = preview.stdout.strip().splitlines()[-1]
        return load_demo(), workspace, project, run, token

    def test_wrong_token_rejects_before_any_project_write(self):
        demo, workspace, project, run, _ = self.prepare_preview()
        before = demo.inventory_project(workspace)

        result = self.run_cli(
            "apply", "--project", str(project), "--run-dir", str(run),
            "--approval-token", "intentionally-wrong-demo-token",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approval", result.stderr.lower())
        self.assertEqual(demo.inventory_project(workspace), before)
        self.assertFalse((run / "apply-result.json").exists())
        self.assertFalse((run / "backup").exists())

    def test_stale_preview_rejects_before_partial_approved_edits(self):
        demo, workspace, project, run, token = self.prepare_preview()
        tampered = demo.tamper_previewed_project(workspace)
        after_tamper = demo.inventory_project(workspace)
        tampered_bytes = tampered.read_bytes()

        result = self.run_cli(
            "apply", "--project", str(project), "--run-dir", str(run),
            "--approval-token", token,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approval failed", result.stderr.lower())
        self.assertEqual(tampered.read_bytes(), tampered_bytes)
        self.assertEqual(demo.inventory_project(workspace), after_tamper)
        self.assertTrue((project / "app/demo").is_dir())
        self.assertTrue((project / "public/starter").is_dir())
        self.assertTrue((project / "public/starter-logo.svg").is_file())
        self.assertFalse((project / "public/product-logo.svg").exists())
        self.assertFalse((run / "apply-result.json").exists())
        self.assertFalse((run / "backup").exists())

    def test_tamper_refuses_an_unowned_directory(self):
        demo = load_demo()
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "foreign"
            target = workspace / "project" / "messages" / "en.json"
            target.parent.mkdir(parents=True)
            target.write_text('{"brand":"keep"}\n', encoding="utf-8")
            before = target.read_bytes()

            with self.assertRaisesRegex(ValueError, "sentinel"):
                demo.tamper_previewed_project(workspace)

            self.assertEqual(target.read_bytes(), before)


class PublicDemoDocumentationTests(unittest.TestCase):
    def test_public_demo_walkthrough_preserves_the_safety_contract(self):
        readme = REPO_ROOT / "examples" / "public-demo" / "README.md"
        self.assertTrue(readme.is_file(), "public demo walkthrough is missing")
        text = readme.read_text(encoding="utf-8")
        for phrase in (
            "Risk is reduced, not zero",
            "Git or a verified backup",
            "review the private `preview.diff`",
            "paste the exact token yourself",
            "exit code 3 is expected",
            "no one-command restore",
        ):
            self.assertIn(phrase, text)
        self.assertNotRegex(text, r"--approval-token\s+[0-9a-f]{64}")
        self.assertNotIn("$(python", text)
        self.assertNotIn("$(tail", text)
        self.assertLess(
            text.index("review the private `preview.diff`"),
            text.index("paste the exact token yourself"),
        )

    def test_root_readme_links_the_demo_and_states_nonzero_risk(self):
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("examples/public-demo/README.md", text)
        self.assertIn("Risk is reduced, not zero", text)
        self.assertIn("Git or a verified backup", text)
        self.assertIn("purchased Starter", text)

    def test_public_demo_json_examples_are_strict_and_token_free(self):
        source = json.loads(SOURCE_EXAMPLE.read_text(encoding="utf-8"))
        decisions = json.loads(DECISIONS_EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(set(source), {"source_terms"})
        self.assertEqual(
            set(decisions),
            {
                "brand_mode", "brand_profile", "actions", "delete_paths",
                "rename_paths", "text_edits", "cleanup_empty_dirs",
            },
        )
        combined = SOURCE_EXAMPLE.read_text() + DECISIONS_EXAMPLE.read_text()
        self.assertIsNone(re.search(r"\b[0-9a-f]{64}\b", combined))


class PublicDemoMediaTests(unittest.TestCase):
    def test_chinese_media_documents_include_the_honest_safety_segment(self):
        documents = (
            REPO_ROOT / "docs" / "self-media-package.zh-CN.md",
            REPO_ROOT / "docs" / "video-shot-list.zh-CN.md",
            REPO_ROOT / "docs" / "video-production-log.zh-CN.md",
        )
        for document in documents:
            text = document.read_text(encoding="utf-8")
            for phrase in (
                "公开合成演示",
                "错误令牌",
                "过期预览",
                "低风险不等于零风险",
                "没有一键恢复命令",
            ):
                self.assertIn(phrase, text, "%s: %s" % (document.name, phrase))

    def test_public_demo_evidence_source_is_redacted(self):
        source = (
            REPO_ROOT / "docs" / "assets" / "video" / "sources"
            / "08-public-demo-safety.html"
        )
        self.assertTrue(source.is_file(), "public demo evidence HTML is missing")
        text = source.read_text(encoding="utf-8")
        self.assertIn("REDACTED", text)
        self.assertIn("错误令牌", text)
        self.assertIn("过期预览", text)
        self.assertIsNone(re.search(r"\b[0-9a-f]{64}\b", text))
        self.assertIsNone(re.search(r"/(Users|home)/", text))
        self.assertNotIn("approval-token", text)

    def test_public_demo_evidence_png_is_1600_by_900(self):
        image = (
            REPO_ROOT / "docs" / "assets" / "video" / "08-public-demo-safety.png"
        )
        self.assertTrue(image.is_file(), "public demo evidence PNG is missing")
        data = image.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", data[16:24]), (1600, 900))


if __name__ == "__main__":
    unittest.main()
