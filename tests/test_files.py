from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from tests.support import SKILL_SCRIPTS

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.files import (
    iter_project_directories,
    iter_project_files,
    read_text,
    sha256_file,
)


class FileDiscoveryTests(unittest.TestCase):
    def test_directory_inventory_is_sorted_and_records_safe_source_directories(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = root / "empty-source"
            nested = root / "starter-assets" / "nested"
            empty.mkdir()
            empty.chmod(0o750)
            nested.mkdir(parents=True)
            (nested / "asset.txt").write_text("asset", encoding="utf-8")
            (root / "node_modules" / "dependency").mkdir(parents=True)
            (root / ".env.production" / "secret").mkdir(parents=True)
            (root / "linked-source").symlink_to(empty, target_is_directory=True)

            records = list(iter_project_directories(root))
            by_path = {record.relpath: record for record in records}

            self.assertEqual(
                [record.relpath for record in records],
                ["empty-source", "starter-assets", "starter-assets/nested"],
            )
            self.assertEqual(by_path["empty-source"].mode, 0o750)
            self.assertTrue(by_path["empty-source"].is_empty)
            self.assertFalse(by_path["starter-assets"].is_empty)
            self.assertFalse(by_path["starter-assets/nested"].is_empty)
            self.assertEqual(len(by_path["starter-assets"].state_sha256), 64)
            self.assertEqual(records, list(iter_project_directories(root)))

    def test_directory_inventory_treats_excluded_children_as_non_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "public"
            parent.mkdir()
            (parent / "node_modules").mkdir()
            (parent / ".env.staging").mkdir()

            records = {record.relpath: record for record in iter_project_directories(root)}

            self.assertEqual(set(records), {"public"})
            self.assertFalse(records["public"].is_empty)

    def test_directory_state_hash_changes_for_direct_and_descendant_changes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "starter"
            parent.mkdir()

            initial = next(iter_project_directories(root))
            (parent / "direct.txt").write_text("direct", encoding="utf-8")
            after_direct = next(iter_project_directories(root))
            (parent / "nested").mkdir()
            (parent / "nested" / "child.txt").write_text("child", encoding="utf-8")
            after_descendant = next(iter_project_directories(root))

            self.assertNotEqual(initial.state_sha256, after_direct.state_sha256)
            self.assertNotEqual(after_direct.state_sha256, after_descendant.state_sha256)

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
