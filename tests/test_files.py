from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import unittest
from unittest import mock

from tests.support import SKILL_SCRIPTS

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.files import (
    iter_project_directories,
    iter_project_files,
    read_text,
    sha256_file,
)
from destarter_lib import files as files_module


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

    def test_directory_state_hash_changes_when_an_existing_descendant_changes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "starter"
            child = parent / "nested" / "child.txt"
            child.parent.mkdir(parents=True)
            child.write_text("before", encoding="utf-8")

            initial = next(iter_project_directories(root))
            child.write_text("after", encoding="utf-8")
            after_descendant = next(iter_project_directories(root))

            self.assertNotEqual(initial.state_sha256, after_descendant.state_sha256)

    def test_excluded_child_content_is_opaque_but_keeps_parent_non_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "public"
            hidden = parent / "node_modules"
            hidden.mkdir(parents=True)
            secret = hidden / "private.txt"
            secret.write_text("before", encoding="utf-8")

            initial = next(iter_project_directories(root))
            secret.write_text("after", encoding="utf-8")
            hidden.chmod(0)
            try:
                after = next(iter_project_directories(root))
            finally:
                hidden.chmod(0o755)

            self.assertEqual(initial.state_sha256, after.state_sha256)
            self.assertFalse(after.is_empty)
            self.assertEqual(after.relpath, "public")

    def test_directory_inventory_fails_closed_when_child_appears_after_snapshot(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "public"
            parent.mkdir()
            original = getattr(files_module, "_snapshot_directory", None)
            mutated = False
            parent_identity = (parent.stat().st_dev, parent.stat().st_ino)

            def mutate_after_snapshot(descriptor: int):
                nonlocal mutated
                snapshot = original(descriptor)
                current = os.fstat(descriptor)
                if not mutated and (current.st_dev, current.st_ino) == parent_identity:
                    mutated = True
                    (parent / "raced-child").mkdir()
                return snapshot

            with mock.patch.object(
                files_module,
                "_snapshot_directory",
                side_effect=mutate_after_snapshot,
                create=True,
            ):
                with self.assertRaises(RuntimeError):
                    list(iter_project_directories(root))

    def test_directory_inventory_fails_closed_when_child_becomes_a_symlink(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "public"
            child = parent / "safe"
            outside = root / "outside"
            child.mkdir(parents=True)
            outside.mkdir()
            original = getattr(files_module, "_snapshot_directory", None)
            mutated = False
            parent_identity = (parent.stat().st_dev, parent.stat().st_ino)

            def replace_after_snapshot(descriptor: int):
                nonlocal mutated
                snapshot = original(descriptor)
                current = os.fstat(descriptor)
                if not mutated and (current.st_dev, current.st_ino) == parent_identity:
                    mutated = True
                    child.rmdir()
                    child.symlink_to(outside, target_is_directory=True)
                return snapshot

            with mock.patch.object(
                files_module,
                "_snapshot_directory",
                side_effect=replace_after_snapshot,
                create=True,
            ):
                with self.assertRaises(RuntimeError):
                    list(iter_project_directories(root))

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
