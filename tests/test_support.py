import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support import copy_fixture


class CopyFixtureTests(unittest.TestCase):
    def test_copy_fixture_preserves_target_path_and_nested_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory)

            target = copy_fixture("nextjs-starter", destination)

            self.assertEqual(target, destination / "nextjs-starter")
            demo_page = target / "app" / "demo" / "page.tsx"
            self.assertTrue(demo_page.is_file())
            self.assertEqual(
                demo_page.read_text(),
                "export default function DemoPage() {\n"
                "  return <main>Northstar Starter demonstration</main>;\n"
                "}\n",
            )


if __name__ == "__main__":
    unittest.main()
