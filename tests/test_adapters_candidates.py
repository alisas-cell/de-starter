from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.adapters import detect_project
from destarter_lib.candidates import discover_candidates


class AdapterCandidateTests(unittest.TestCase):
    def test_detects_node_commands_and_package_manager(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'", encoding="utf-8")
            facts = detect_project(root)
            self.assertEqual(facts.kind, "node-next")
            self.assertEqual(facts.package_manager, "pnpm")
            self.assertEqual(
                facts.validation_commands,
                ["pnpm lint", "pnpm test", "pnpm build"],
            )

    def test_discovers_source_identity_without_dependency_names(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            candidates = discover_candidates(root)
            values = {candidate.value for candidate in candidates}
            self.assertIn("Northstar Labs", values)
            self.assertIn("northstar-starter", values)
            self.assertIn(
                "https://github.com/northstar-labs/northstar-starter",
                values,
            )
            self.assertNotIn("next", values)

    def test_discovers_python_project_identity(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("python-starter", Path(tmp))
            values = {candidate.value for candidate in discover_candidates(root)}
            self.assertIn("harbor-starter", values)
            self.assertIn("Harbor Works", values)
            self.assertIn("team@harbor.example", values)

    def test_discovers_display_identity_from_static_html(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("static-starter", Path(tmp))
            values = {candidate.value for candidate in discover_candidates(root)}
            self.assertIn("Canvas Boilerplate", values)
            self.assertIn("Canvas Foundry", values)


if __name__ == "__main__":
    unittest.main()
