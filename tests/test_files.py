from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from tests.support import SKILL_SCRIPTS

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.files import iter_project_files, read_text, sha256_file


class FileDiscoveryTests(unittest.TestCase):
    def test_excludes_secrets_dependencies_and_build_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SECRET=real", encoding="utf-8")
            (root / ".env.staging").write_text("SECRET=also-real", encoding="utf-8")
            (root / ".env.example").write_text("NAME=Starter", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("Starter", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "dep.js").write_text("Starter", encoding="utf-8")
            paths = [record.relpath for record in iter_project_files(root)]
            self.assertEqual(paths, [".env.example", "src/app.ts"])

    def test_binary_file_is_not_decoded(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.bin"
            path.write_bytes(b"\x00\x01Northstar")
            self.assertIsNone(read_text(path))
            self.assertEqual(len(sha256_file(path)), 64)


if __name__ == "__main__":
    unittest.main()
