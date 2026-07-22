from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from typing import Dict, Iterator, List, Optional, Tuple
import uuid

from .models import DirectoryRecord, FileRecord

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".next", ".nuxt", ".cache", ".pytest_cache",
    ".tox", ".venv", "venv", "build", "dist", "coverage", "node_modules",
    "vendor", "__pycache__",
}
SAFE_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
MAX_TEXT_BYTES = 2 * 1024 * 1024


def safe_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    """Atomically replace an artifact without following its final pathname."""
    if type(mode) is not int or mode < 0 or mode > 0o777:
        raise ValueError("invalid artifact mode")
    if os.name == "nt":
        raise OSError("safe artifact writing is unavailable on this platform")
    try:
        parent_fd = os.open(
            str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
    except OSError as error:
        raise OSError("unsafe artifact directory") from error
    temporary = ".destarter-write-{}".format(uuid.uuid4().hex)
    descriptor = None
    try:
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=parent_fd,
        )
        os.fchmod(descriptor, mode)
        view = memoryview(text.encode("utf-8"))
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    except OSError:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> Optional[str]:
    if is_secret_name(path.name) or path.stat().st_size > MAX_TEXT_BYTES:
        return None
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def is_secret_name(name: str) -> bool:
    return name == ".env" or (
        name.startswith(".env.") and name not in SAFE_ENV_EXAMPLES
    )


def _state_digest(payload: Dict[str, object]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class DirectoryInventoryError(RuntimeError):
    """Raised when a directory cannot be inventoried from stable descriptors."""


@dataclass(frozen=True)
class _EntrySnapshot:
    name: str
    identity: Tuple[int, int, int, int, int, int, int]


@dataclass(frozen=True)
class _DirectorySnapshot:
    identity: Tuple[int, int, int, int, int, int, int]
    entries: Tuple[_EntrySnapshot, ...]


@dataclass(frozen=True)
class _CollectedDirectory:
    mode: int
    state_sha256: str
    is_empty: bool
    records: Tuple[DirectoryRecord, ...]


def _identity(entry_stat: os.stat_result) -> Tuple[int, int, int, int, int, int, int]:
    return (
        entry_stat.st_dev,
        entry_stat.st_ino,
        stat.S_IFMT(entry_stat.st_mode),
        stat.S_IMODE(entry_stat.st_mode),
        entry_stat.st_size,
        entry_stat.st_mtime_ns,
        entry_stat.st_ctime_ns,
    )


def _snapshot_directory(descriptor: int) -> _DirectorySnapshot:
    """Capture entry identities from one pinned directory descriptor."""
    try:
        entries = tuple(
            _EntrySnapshot(
                name,
                _identity(os.stat(name, dir_fd=descriptor, follow_symlinks=False)),
            )
            for name in sorted(os.listdir(descriptor))
        )
        return _DirectorySnapshot(_identity(os.fstat(descriptor)), entries)
    except OSError as error:
        raise DirectoryInventoryError("directory changed during inventory") from error


def _assert_identity(
    entry_stat: os.stat_result,
    expected: Tuple[int, int, int, int, int, int, int],
) -> None:
    if _identity(entry_stat) != expected:
        raise DirectoryInventoryError("directory changed during inventory")


def _entry_type(mode: int) -> str:
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def _sha256_open_file(parent_fd: int, entry: _EntrySnapshot) -> str:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        descriptor = os.open(entry.name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise DirectoryInventoryError("directory changed during inventory") from error
    try:
        opened = os.fstat(descriptor)
        _assert_identity(opened, entry.identity)
        if not stat.S_ISREG(opened.st_mode):
            raise DirectoryInventoryError("directory changed during inventory")
        digest = sha256()
        for chunk in iter(lambda: os.read(descriptor, 65536), b""):
            digest.update(chunk)
        _assert_identity(os.fstat(descriptor), entry.identity)
        return digest.hexdigest()
    except OSError as error:
        raise DirectoryInventoryError("directory changed during inventory") from error
    finally:
        os.close(descriptor)


def _open_child_directory(parent_fd: int, entry: _EntrySnapshot) -> int:
    try:
        descriptor = os.open(
            entry.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as error:
        raise DirectoryInventoryError("directory changed during inventory") from error
    try:
        opened = os.fstat(descriptor)
        _assert_identity(opened, entry.identity)
        if not stat.S_ISDIR(opened.st_mode):
            raise DirectoryInventoryError("directory changed during inventory")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _symlink_digest(parent_fd: int, entry: _EntrySnapshot) -> str:
    try:
        before = os.stat(entry.name, dir_fd=parent_fd, follow_symlinks=False)
        _assert_identity(before, entry.identity)
        target = os.readlink(entry.name, dir_fd=parent_fd)
        _assert_identity(
            os.stat(entry.name, dir_fd=parent_fd, follow_symlinks=False),
            entry.identity,
        )
    except OSError as error:
        raise DirectoryInventoryError("directory changed during inventory") from error
    return sha256(target.encode("utf-8")).hexdigest()


def _collect_directory(descriptor: int, relpath: str) -> _CollectedDirectory:
    before = _snapshot_directory(descriptor)
    entries: List[Dict[str, object]] = []
    records: List[DirectoryRecord] = []
    has_excluded_child = False

    for snapshot in before.entries:
        if snapshot.name in IGNORED_DIRS or is_secret_name(snapshot.name):
            has_excluded_child = True
            continue
        try:
            entry_stat = os.stat(
                snapshot.name, dir_fd=descriptor, follow_symlinks=False
            )
        except OSError as error:
            raise DirectoryInventoryError("directory changed during inventory") from error
        _assert_identity(entry_stat, snapshot.identity)
        mode = stat.S_IMODE(entry_stat.st_mode)
        entry: Dict[str, object] = {
            "name": snapshot.name,
            "type": _entry_type(entry_stat.st_mode),
            "mode": mode,
        }
        if stat.S_ISDIR(entry_stat.st_mode):
            child_fd = _open_child_directory(descriptor, snapshot)
            try:
                child_relpath = "/".join(filter(None, (relpath, snapshot.name)))
                child = _collect_directory(child_fd, child_relpath)
            finally:
                os.close(child_fd)
            entry["state_sha256"] = child.state_sha256
            records.extend(child.records)
        elif stat.S_ISREG(entry_stat.st_mode):
            entry["sha256"] = _sha256_open_file(descriptor, snapshot)
        elif stat.S_ISLNK(entry_stat.st_mode):
            entry["target_sha256"] = _symlink_digest(descriptor, snapshot)
        entries.append(entry)

    if _snapshot_directory(descriptor) != before:
        raise DirectoryInventoryError("directory changed during inventory")
    mode = before.identity[3]
    state_sha256 = _state_digest({
        "mode": mode,
        "entries": entries,
        "has_excluded_child": has_excluded_child,
    })
    is_empty = not before.entries
    if relpath:
        records.append(DirectoryRecord(relpath, mode, state_sha256, is_empty))
    return _CollectedDirectory(mode, state_sha256, is_empty, tuple(records))


def iter_project_directories(root: Path) -> Iterator[DirectoryRecord]:
    """Inventory real project directories without following directory symlinks."""
    try:
        descriptor = os.open(
            str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
    except OSError as error:
        raise DirectoryInventoryError("unsafe project directory") from error
    try:
        first = _collect_directory(descriptor, "")
        second = _collect_directory(descriptor, "")
    finally:
        os.close(descriptor)
    if first != second:
        raise DirectoryInventoryError("directory changed during inventory")
    yield from sorted(second.records, key=lambda item: item.relpath)


def iter_project_files(root: Path) -> Iterator[FileRecord]:
    records = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if is_secret_name(path.name):
            continue
        records.append(
            FileRecord(
                relpath=rel.as_posix(),
                size=path.stat().st_size,
                sha256=sha256_file(path),
                is_text=read_text(path) is not None,
            )
        )
    yield from sorted(records, key=lambda item: item.relpath)
