from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from typing import Dict, Iterator, Optional, Tuple
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


def _entry_type(mode: int) -> str:
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def _sha256_open_file(parent_fd: int, name: str) -> str:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=parent_fd)
    try:
        digest = sha256()
        for chunk in iter(lambda: os.read(descriptor, 65536), b""):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _directory_state_from_fd(descriptor: int) -> Tuple[int, str, bool]:
    directory_stat = os.fstat(descriptor)
    entries = []
    with os.scandir(descriptor) as scan:
        names = sorted(entry.name for entry in scan)
    for name in names:
        entry_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        mode = stat.S_IMODE(entry_stat.st_mode)
        entry: Dict[str, object] = {
            "name": name,
            "type": _entry_type(entry_stat.st_mode),
            "mode": mode,
        }
        if stat.S_ISDIR(entry_stat.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            try:
                _, entry["state_sha256"], _ = _directory_state_from_fd(child_fd)
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(entry_stat.st_mode):
            entry["sha256"] = _sha256_open_file(descriptor, name)
        elif stat.S_ISLNK(entry_stat.st_mode):
            entry["target_sha256"] = sha256(
                os.readlink(name, dir_fd=descriptor).encode("utf-8")
            ).hexdigest()
        entries.append(entry)
    payload = {
        "mode": stat.S_IMODE(directory_stat.st_mode),
        "entries": entries,
    }
    return stat.S_IMODE(directory_stat.st_mode), _state_digest(payload), not entries


def _directory_state(path: Path) -> Tuple[int, str, bool]:
    descriptor = os.open(
        str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )
    try:
        return _directory_state_from_fd(descriptor)
    finally:
        os.close(descriptor)


def iter_project_directories(root: Path) -> Iterator[DirectoryRecord]:
    """Inventory real project directories without following directory symlinks."""
    records = []
    root = Path(root)
    for current, directory_names, _ in os.walk(root, topdown=True, followlinks=False):
        directory = Path(current)
        safe_names = []
        for name in directory_names:
            if name in IGNORED_DIRS or is_secret_name(name):
                continue
            try:
                entry_stat = (directory / name).lstat()
            except OSError:
                continue
            if stat.S_ISDIR(entry_stat.st_mode) and not stat.S_ISLNK(entry_stat.st_mode):
                safe_names.append(name)
        directory_names[:] = sorted(safe_names)

        if directory == root:
            continue
        try:
            mode, state_sha256, is_empty = _directory_state(directory)
        except OSError:
            continue
        records.append(
            DirectoryRecord(
                relpath=directory.relative_to(root).as_posix(),
                mode=mode,
                state_sha256=state_sha256,
                is_empty=is_empty,
            )
        )
    yield from sorted(records, key=lambda item: item.relpath)


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
