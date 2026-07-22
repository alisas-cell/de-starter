"""Create reviewable, project-external de-starter previews without touching source."""

import ctypes
import difflib
import errno
import json
import os
import re
import shutil
import stat
import sys
import uuid
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from .files import (
    IGNORED_DIRS,
    is_secret_name,
    iter_project_directories,
    read_text,
    safe_write_text,
    sha256_file,
)
from .models import AuditResult, DecisionSet, PreviewManifest
from .report import redact_evidence
from .decisions import PLACEHOLDER_PROFILE


_OWNER_FILE = ".destarter-preview-owner.json"
_CLEANUP_STAGING_OWNER = ".destarter-preview-cleanup-owner.json"
_PROTECTED_STEMS = {"license", "copying", "notice"}
_SECRET_VALUE_RE = re.compile(r"(?i)(secret|token|api[_-]?key|password|^sk_)")


def _is_ignored_name(name: str) -> bool:
    return name.casefold() in {item.casefold() for item in IGNORED_DIRS}


def _is_secret_name(name: str) -> bool:
    lowered = name.casefold()
    return is_secret_name(name) or lowered == ".env" or (
        lowered.startswith(".env.") and lowered not in {".env.example", ".env.sample", ".env.template"}
    )


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _ignore(_directory: str, names: List[str]) -> List[str]:
    return [name for name in names if _is_ignored_name(name) or _is_secret_name(name)]


def _token(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _safe_relpath(value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("preview operation must stay inside project")
    path = Path(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("preview operation must stay inside project")
    for part in path.parts:
        lowered = part.casefold()
        stem = lowered.split(".", 1)[0]
        if _is_ignored_name(part) or _is_secret_name(part) or stem in _PROTECTED_STEMS:
            raise ValueError("preview operation contains protected ignored metadata")
    return path


def _ensure_no_symlinks(root: Path) -> None:
    """Reject links rather than risk following an external or absolute target."""
    for directory, dirs, files in os.walk(str(root), followlinks=False):
        current = Path(directory)
        dirs[:] = [name for name in dirs if not _is_ignored_name(name) and not _is_secret_name(name)]
        files = [name for name in files if not _is_secret_name(name)]
        for name in dirs + files:
            candidate = current / name
            if candidate.is_symlink():
                raise ValueError("project contains symlink; preview refuses symlink sources")


def _safe_file_records(root: Path, excluded_names: Iterable[str] = ()) -> List[Dict[str, object]]:
    """Inventory the same safe, non-secret tree that may enter a preview."""
    records = []
    excluded = set(excluded_names)
    for directory, dirs, files in os.walk(str(root), followlinks=False):
        current = Path(directory)
        dirs[:] = [name for name in dirs if not _is_ignored_name(name) and not _is_secret_name(name)]
        for name in sorted(files):
            if name in excluded or _is_ignored_name(name) or _is_secret_name(name):
                continue
            path = current / name
            if path.is_symlink() or not path.is_file():
                continue
            relpath = path.relative_to(root).as_posix()
            records.append({
                "relpath": relpath, "size": path.stat().st_size,
                "sha256": sha256_file(path), "is_text": read_text(path) is not None,
            })
    return sorted(records, key=lambda item: str(item["relpath"]))


def _snapshot_hash(records: List[Dict[str, object]]) -> str:
    return _token({"files": records})


def _assert_source_unchanged(
    root: Path,
    source_records: List[Dict[str, object]],
    source_tree_hash: str,
    source_state_hash: str,
) -> None:
    current_records = _safe_file_records(root)
    if (
        current_records != source_records
        or _snapshot_hash(current_records) != source_tree_hash
        or _state_hash(root) != source_state_hash
    ):
        raise ValueError("source changed during preview")


def _state_hash(root: Path, excluded_names: Iterable[str] = ()) -> str:
    """Bind every safe file, directory (including empty ones), and permission mode."""
    excluded = set(excluded_names)
    try:
        root_info = root.lstat()
    except OSError as error:
        raise ValueError("preview state root is unavailable") from error
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise ValueError("preview state contains unsafe root object")
    entries = []
    for directory, dirs, files in os.walk(str(root), followlinks=False):
        current = Path(directory)
        try:
            current_info = current.lstat()
        except OSError as error:
            raise ValueError("preview state directory is unavailable") from error
        if stat.S_ISLNK(current_info.st_mode) or not stat.S_ISDIR(current_info.st_mode):
            raise ValueError("preview state contains unsafe directory object")
        dirs[:] = [name for name in dirs if not _is_ignored_name(name) and not _is_secret_name(name)]
        rel_dir = current.relative_to(root).as_posix()
        entries.append({"kind": "dir", "path": rel_dir, "mode": stat.S_IMODE(current_info.st_mode)})
        for name in sorted(dirs):
            path = current / name
            try:
                info = path.lstat()
            except OSError as error:
                raise ValueError("preview state directory entry is unavailable") from error
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("preview state contains symlink or unsupported directory entry")
        for name in sorted(files):
            if name in excluded or _is_ignored_name(name) or _is_secret_name(name):
                continue
            path = current / name
            try:
                info = path.lstat()
            except OSError as error:
                raise ValueError("preview state file entry is unavailable") from error
            if stat.S_ISLNK(info.st_mode):
                raise ValueError("preview state contains symlink file entry")
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("preview state contains unsupported file entry")
            entries.append({"kind": "file", "path": path.relative_to(root).as_posix(),
                            "mode": stat.S_IMODE(info.st_mode), "sha256": sha256_file(path)})
    return _token({"state": sorted(entries, key=lambda item: (str(item["path"]), str(item["kind"])))})


def _tree_files(root: Path, relpath: str) -> List[Tuple[str, Path]]:
    target = root / _safe_relpath(relpath)
    if target.is_file():
        return [(relpath, target)]
    if not target.is_dir():
        raise ValueError("preview operation path does not exist: {}".format(relpath))
    records = []
    for record in _safe_file_records(target):
        child = target / str(record["relpath"])
        records.append(((Path(relpath) / str(record["relpath"])).as_posix(), child))
    if not records:
        # Empty directories are still bound to a deterministic tree hash.
        return []
    return records


def _tree_hash(root: Path, relpath: str) -> str:
    entries = ["{}:{}".format(path, sha256_file(item)) for path, item in _tree_files(root, relpath)]
    return sha256("\n".join(entries).encode("utf-8")).hexdigest()


def _contains_secret_or_ignored(root: Path, relpath: str) -> bool:
    target = root / _safe_relpath(relpath)
    if target.is_file():
        return _is_secret_name(target.name) or _is_ignored_name(target.name)
    if not target.is_dir():
        return False
    for directory, dirs, files in os.walk(str(target), followlinks=False):
        if any(_is_ignored_name(name) or _is_secret_name(name) for name in dirs):
            return True
        if any(_is_ignored_name(name) or _is_secret_name(name) for name in files):
            return True
    return False


def _cleanup_directory_states(
    root: Path, audit: AuditResult, cleanup_paths: Iterable[str],
) -> Dict[str, Dict[str, object]]:
    """Bind only audited, current, safe cleanup directories to the preview."""
    cleanup = sorted(cleanup_paths)
    if len(cleanup) != len(set(cleanup)):
        raise ValueError("cleanup empty directories contain duplicates")
    audited = {item.relpath: item for item in audit.directories}
    if len(audited) != len(audit.directories):
        raise ValueError("audit contains duplicate directory records")
    current = {item.relpath: item for item in iter_project_directories(root)}
    states: Dict[str, Dict[str, object]] = {}
    for relpath in cleanup:
        safe = _safe_relpath(relpath).as_posix()
        if safe != relpath:
            raise ValueError("cleanup directory path is not canonical: {}".format(relpath))
        path = root / safe
        try:
            info = path.lstat()
        except OSError as error:
            raise ValueError("cleanup directory is missing: {}".format(relpath)) from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("cleanup directory is not a real directory: {}".format(relpath))
        if _contains_secret_or_ignored(root, relpath):
            raise ValueError(
                "cleanup directory contains excluded secret file or ignored metadata: {}".format(relpath)
            )
        expected = audited.get(relpath)
        actual = current.get(relpath)
        if expected is None or actual is None or actual != expected:
            raise ValueError("cleanup directory changed after audit: {}".format(relpath))
        states[relpath] = {
            "mode": expected.mode,
            "state_sha256": expected.state_sha256,
            "is_empty": expected.is_empty,
        }
    return states


def _directory_identity_at(
    parent_fd: int, name: str, relpath: str,
) -> Tuple[int, int]:
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        raise ValueError(
            "cleanup preview directory is missing: {}".format(relpath)
        ) from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(
            "cleanup preview path is not a real directory: {}".format(relpath)
        )
    return info.st_dev, info.st_ino


def _open_pinned_preview_directory(
    parent_fd: int, name: str, relpath: str,
) -> Tuple[int, Tuple[int, int]]:
    before = _directory_identity_at(parent_fd, name, relpath)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as error:
        raise ValueError(
            "cannot pin cleanup preview directory: {}".format(relpath)
        ) from error
    try:
        opened = os.fstat(descriptor)
        identity = opened.st_dev, opened.st_ino
        if before != identity or _directory_identity_at(parent_fd, name, relpath) != identity:
            raise ValueError(
                "cleanup preview directory changed while being pinned: {}".format(relpath)
            )
        return descriptor, identity
    except Exception:
        os.close(descriptor)
        raise


def _open_pinned_preview_cleanup_dir(
    preview_root: Path, relpath: str,
) -> Tuple[int, int, int, Tuple[str, ...], Tuple[Tuple[int, int], ...]]:
    """Open the cleanup root and all components without following links."""
    parts = _safe_relpath(relpath).parts
    try:
        root_fd = os.open(
            str(preview_root),
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except OSError as error:
        raise ValueError("cannot pin preview root for cleanup") from error
    parent_fd = root_fd
    terminal_fd = -1
    identities: List[Tuple[int, int]] = []
    try:
        for index, part in enumerate(parts):
            current = "/".join(parts[:index + 1])
            child_fd, identity = _open_pinned_preview_directory(
                parent_fd, part, current,
            )
            identities.append(identity)
            if index == len(parts) - 1:
                terminal_fd = child_fd
                break
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = child_fd
        return root_fd, parent_fd, terminal_fd, parts, tuple(identities)
    except Exception:
        if terminal_fd >= 0:
            os.close(terminal_fd)
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)
        raise


def _assert_pinned_preview_cleanup_chain(
    root_fd: int,
    parts: Tuple[str, ...],
    identities: Tuple[Tuple[int, int], ...],
) -> None:
    """Ensure no pinned preview component was renamed or link-swapped."""
    current_fd = os.dup(root_fd)
    try:
        for index, part in enumerate(parts):
            relpath = "/".join(parts[:index + 1])
            actual = _directory_identity_at(current_fd, part, relpath)
            if actual != identities[index]:
                raise ValueError(
                    "cleanup preview directory changed after inspection: {}".format(relpath)
                )
            if index == len(parts) - 1:
                break
            next_fd, opened = _open_pinned_preview_directory(
                current_fd, part, relpath,
            )
            if opened != identities[index]:
                os.close(next_fd)
                raise ValueError(
                    "cleanup preview directory changed after inspection: {}".format(relpath)
                )
            os.close(current_fd)
            current_fd = next_fd
    finally:
        os.close(current_fd)


def _entry_absent(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        return False
    except FileNotFoundError:
        return True


def _write_cleanup_staging_owner(
    staging_fd: int, project_root: Path,
) -> None:
    payload = json.dumps(
        {"project_root": str(project_root)}, sort_keys=True,
    ).encode("utf-8") + b"\n"
    try:
        descriptor = os.open(
            _CLEANUP_STAGING_OWNER,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=staging_fd,
        )
    except OSError as error:
        raise ValueError("cannot mark cleanup staging as owned") from error
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
    except OSError as error:
        raise ValueError("cannot write cleanup staging owner") from error
    finally:
        os.close(descriptor)


def _open_preview_cleanup_staging(run: Path, project_root: Path) -> int:
    """Create one unique, owner-marked staging directory per preview attempt."""
    try:
        run_fd = os.open(
            str(run), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
    except OSError as error:
        raise ValueError("cannot pin run directory for cleanup staging") from error
    try:
        for _attempt in range(8):
            name = ".destarter-preview-cleanup-{}".format(uuid.uuid4().hex)
            try:
                os.mkdir(name, 0o700, dir_fd=run_fd)
            except FileExistsError:
                continue
            try:
                staging_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=run_fd,
                )
            except OSError as error:
                raise ValueError("cannot pin cleanup staging directory") from error
            try:
                identity = _directory_identity_at(
                    run_fd, name, "cleanup staging",
                )
                opened = os.fstat(staging_fd)
                if identity != (opened.st_dev, opened.st_ino):
                    raise ValueError("cleanup staging directory changed while being pinned")
                _write_cleanup_staging_owner(staging_fd, project_root)
                return staging_fd
            except Exception:
                os.close(staging_fd)
                raise
        raise ValueError("cannot allocate unique cleanup staging directory")
    finally:
        os.close(run_fd)


def _cleanup_staging_name(relpath: str) -> str:
    return "cleanup-{}".format(sha256(relpath.encode("utf-8")).hexdigest())


def _atomic_rename_no_replace(
    source: str,
    destination: str,
    *,
    src_dir_fd: int,
    dst_dir_fd: int,
) -> None:
    """Move one descriptor-relative name without ever replacing its destination."""
    if (
        not isinstance(source, str)
        or not isinstance(destination, str)
        or not source
        or not destination
        or "/" in source
        or "/" in destination
        or "\x00" in source
        or "\x00" in destination
        or any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (src_dir_fd, dst_dir_fd)
        )
    ):
        raise ValueError("invalid atomic no-clobber rename component")
    try:
        source_bytes = os.fsencode(source)
        destination_bytes = os.fsencode(destination)
    except (TypeError, UnicodeError) as error:
        raise ValueError("invalid atomic no-clobber rename component") from error
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        primitive = getattr(libc, "renameatx_np", None)
        flags = 0x4  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        primitive = getattr(libc, "renameat2", None)
        flags = 0x1  # RENAME_NOREPLACE
    else:
        primitive = None
        flags = 0
    if primitive is None:
        raise ValueError("atomic no-clobber rename unavailable")
    primitive.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    primitive.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = primitive(
        src_dir_fd,
        source_bytes,
        dst_dir_fd,
        destination_bytes,
        flags,
    )
    if result == 0:
        return
    error_code = ctypes.get_errno()
    if error_code == errno.EEXIST:
        raise ValueError("cleanup staging destination already exists")
    unsupported = {
        errno.EINVAL,
        errno.ENOSYS,
        getattr(errno, "ENOTSUP", errno.EOPNOTSUPP),
        errno.EOPNOTSUPP,
    }
    if error_code in unsupported:
        raise ValueError("atomic no-clobber rename unavailable")
    detail = os.strerror(error_code) if error_code else "unknown failure"
    raise ValueError("atomic no-clobber rename failed: {}".format(detail))


def _isolate_preview_cleanup_dir(
    root_fd: int,
    parent_fd: int,
    parts: Tuple[str, ...],
    identities: Tuple[Tuple[int, int], ...],
    staging_fd: int,
    relpath: str,
) -> str:
    """Atomically move the terminal entry out of the preview before rechecking it."""
    _assert_pinned_preview_cleanup_chain(root_fd, parts, identities)
    if _directory_identity_at(parent_fd, parts[-1], relpath) != identities[-1]:
        raise ValueError("cleanup preview directory changed before isolation: {}".format(relpath))
    if os.fstat(parent_fd).st_dev != os.fstat(staging_fd).st_dev:
        raise ValueError("cleanup staging must be on the preview filesystem")
    staging_name = _cleanup_staging_name(relpath)
    if not _entry_absent(staging_fd, staging_name):
        raise ValueError("cleanup staging entry already exists")
    _atomic_rename_no_replace(
        parts[-1], staging_name,
        src_dir_fd=parent_fd,
        dst_dir_fd=staging_fd,
    )
    return staging_name


def _verify_isolated_preview_cleanup_dir(
    staging_fd: int,
    staging_name: str,
    expected_identity: Tuple[int, int],
    state: Mapping[str, object],
    relpath: str,
) -> None:
    actual = _directory_identity_at(staging_fd, staging_name, relpath)
    if actual != expected_identity:
        raise ValueError("isolated cleanup directory changed: {}".format(relpath))
    descriptor, opened_identity = _open_pinned_preview_directory(
        staging_fd, staging_name, relpath,
    )
    try:
        if opened_identity != expected_identity:
            raise ValueError("isolated cleanup directory changed: {}".format(relpath))
        info = os.fstat(descriptor)
        if stat.S_IMODE(info.st_mode) != state["mode"]:
            raise ValueError("isolated cleanup directory mode changed: {}".format(relpath))
        with os.scandir(descriptor) as entries:
            if next(entries, None) is not None:
                raise ValueError("isolated cleanup directory is not empty: {}".format(relpath))
        if _directory_identity_at(staging_fd, staging_name, relpath) != expected_identity:
            raise ValueError("isolated cleanup directory changed during inspection: {}".format(relpath))
    finally:
        os.close(descriptor)


def _remove_preview_cleanup_dir(
    preview_root: Path,
    staging_fd: int,
    relpath: str,
    state: Mapping[str, object],
) -> Dict[str, object]:
    """Isolate and prove one approved empty directory without deleting it."""
    root_fd, parent_fd, terminal_fd, parts, identities = _open_pinned_preview_cleanup_dir(
        preview_root, relpath,
    )
    try:
        info = os.fstat(terminal_fd)
        if stat.S_IMODE(info.st_mode) != state["mode"]:
            raise ValueError("cleanup preview directory mode changed: {}".format(relpath))
        with os.scandir(terminal_fd) as entries:
            if next(entries, None) is not None:
                raise ValueError("cleanup preview directory is not empty: {}".format(relpath))
        if (info.st_dev, info.st_ino) != identities[-1]:
            raise ValueError("cleanup preview directory changed during inspection: {}".format(relpath))
        staging_name = _isolate_preview_cleanup_dir(
            root_fd, parent_fd, parts, identities, staging_fd, relpath,
        )
        _verify_isolated_preview_cleanup_dir(
            staging_fd, staging_name, identities[-1], state, relpath,
        )
        if not _entry_absent(parent_fd, parts[-1]):
            raise ValueError(
                "cleanup preview terminal reappeared after isolation: {}".format(relpath)
            )
        _assert_pinned_preview_cleanup_chain(root_fd, parts[:-1], identities[:-1])
    except Exception:
        raise
    finally:
        os.close(terminal_fd)
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)
    return {
        "operation": "cleanup-empty-dir",
        "path": relpath,
        "mode": state["mode"],
        "source_state_sha256": state["state_sha256"],
        "source_is_empty": state["is_empty"],
    }


def _remove_owned_preview(preview_root: Path, project_root: Path) -> None:
    if not preview_root.exists():
        return
    if preview_root.is_symlink() or not preview_root.is_dir():
        raise ValueError("existing preview root is not a safe directory")
    owner = preview_root / _OWNER_FILE
    try:
        payload = json.loads(owner.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("refusing to remove unowned preview root") from error
    if payload != {"project_root": str(project_root)}:
        raise ValueError("refusing to remove preview owned by another project")
    shutil.rmtree(preview_root)


def _preview_relpath(relpath: str, renames: Mapping[str, str]) -> str:
    for source, destination in sorted(renames.items(), key=lambda item: len(item[0]), reverse=True):
        if relpath == source:
            return destination
        prefix = source.rstrip("/") + "/"
        if relpath.startswith(prefix):
            return destination.rstrip("/") + "/" + relpath[len(prefix):]
    return relpath


def _operation_records(root: Path, paths: Iterable[str], operation: str, renames: Mapping[str, str]) -> List[Dict[str, object]]:
    records = []
    for relpath in sorted(paths):
        for child_relpath, path in _tree_files(root, relpath):
            record = {
                "operation": operation,
                "path": child_relpath,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "is_text": read_text(path) is not None,
            }
            if operation == "rename":
                record["destination"] = _preview_relpath(child_relpath, renames)
            records.append(record)
    return records


def _redact_report_text(text: str, decisions: DecisionSet) -> str:
    """Keep normal review diffs useful while never echoing secret-like input values."""
    text = redact_evidence(text)
    values = [action.replacement for action in decisions.actions if action.replacement]
    values.extend(decisions.brand_profile.values())
    for value in sorted(set(values), key=len, reverse=True):
        if _SECRET_VALUE_RE.search(value):
            text = text.replace(value, "<redacted>")
    return text


def create_preview(
    project_root: Path,
    run_dir: Path,
    audit: AuditResult,
    decisions: DecisionSet,
) -> PreviewManifest:
    """Materialize decisions in a guarded external copy and emit review artifacts."""
    root = project_root.resolve()
    run = run_dir.resolve()
    if not root.is_dir():
        raise ValueError("project root must be an existing directory")
    if _contains(root, run) or _contains(run, root):
        raise ValueError("run directory must be outside project and disjoint from it")
    if run.exists() and run.is_symlink():
        raise ValueError("run directory must not be a symlink")
    _ensure_no_symlinks(root)
    deleted = sorted(set(decisions.delete_paths))
    renames = dict(sorted(decisions.rename_paths.items()))
    cleanup = sorted(decisions.cleanup_empty_dirs)
    operation_roots = deleted + list(renames) + list(renames.values()) + cleanup
    for relpath in operation_roots:
        _safe_relpath(relpath)
    cleanup_dir_states = _cleanup_directory_states(root, audit, cleanup)
    for relpath in deleted + list(renames):
        if _contains_secret_or_ignored(root, relpath):
            raise ValueError("path contains excluded secret file or ignored metadata: {}".format(relpath))
    source_records = _safe_file_records(root)
    audited_records = [
        {"relpath": item.relpath, "size": item.size, "sha256": item.sha256, "is_text": item.is_text}
        for item in sorted(audit.files, key=lambda item: item.relpath)
    ]
    if source_records != audited_records:
        raise ValueError("stale audit: safe source inventory changed")
    source_tree_hash = _snapshot_hash(source_records)
    source_state_hash = _state_hash(root)
    for action in decisions.actions:
        if action.action == "replace":
            finding = next((item for item in audit.findings if item.finding_id == action.finding_id), None)
            if finding and any(
                finding.relpath == path or finding.relpath.startswith(path.rstrip("/") + "/")
                for path in deleted
            ):
                raise ValueError("text replacement falls under deleted path")

    preview_root = run / "preview"
    _remove_owned_preview(preview_root, root)
    run.mkdir(parents=True, exist_ok=True)
    if run.is_symlink() or not run.is_dir():
        raise ValueError("run directory must be a real directory")
    shutil.copytree(root, preview_root, ignore=_ignore)
    safe_write_text(preview_root / _OWNER_FILE, json.dumps({"project_root": str(root)}, sort_keys=True) + "\n")

    findings = {item.finding_id: item for item in audit.findings}
    changed = set()
    action_preimage_hashes: Dict[str, str] = {}
    actions_by_path: Dict[str, List[Tuple[object, object]]] = {}
    semantic_paths = {edit.path for edit in decisions.text_edits}
    for action in decisions.actions:
        if action.action != "replace":
            continue
        finding = findings.get(action.finding_id)
        if finding is None:
            raise ValueError("decision references unknown finding: {}".format(action.finding_id))
        if finding.line <= 0:
            raise ValueError("path finding cannot be text-replaced")
        source_path = root / _safe_relpath(finding.relpath)
        if source_path.is_symlink() or sha256_file(source_path) != finding.sha256:
            raise ValueError("finding no longer matches source: {}".format(finding.finding_id))
        if finding.relpath in semantic_paths and any(
            character in (action.replacement or "")
            for character in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"
        ):
            raise ValueError(
                "line-count-changing finding replacement conflicts with "
                "semantic edit: {}".format(finding.relpath)
            )
        actions_by_path.setdefault(finding.relpath, []).append((finding, action))

    for relpath, pairs in actions_by_path.items():
        path = preview_root / _safe_relpath(relpath)
        text = read_text(path)
        if text is None:
            raise ValueError("finding is not safely editable text: {}".format(relpath))
        lines = text.splitlines(keepends=True)
        for finding, action in sorted(pairs, key=lambda pair: (pair[0].line, pair[0].column), reverse=True):
            index, start = finding.line - 1, finding.column - 1
            end = start + len(finding.matched)
            if index < 0 or index >= len(lines) or lines[index][start:end] != finding.matched:
                raise ValueError("finding no longer matches preview source: {}".format(finding.finding_id))
            lines[index] = lines[index][:start] + (action.replacement or "") + lines[index][end:]
        rendered_text = "".join(lines)
        action_preimage_hashes[relpath] = sha256(
            rendered_text.encode("utf-8")
        ).hexdigest()
        safe_write_text(path, rendered_text, stat.S_IMODE(path.stat().st_mode))
        changed.add(relpath)

    semantic_metadata = []
    edits_by_path = {}
    for edit in decisions.text_edits:
        edits_by_path.setdefault(edit.path, []).append(edit)
    for relpath, edits in sorted(edits_by_path.items()):
        path = preview_root / _safe_relpath(relpath)
        text = read_text(path)
        if text is None:
            raise ValueError("semantic edit is not safely editable text: {}".format(relpath))
        before_hash = sha256(text.encode("utf-8")).hexdigest()
        expected_preimage = action_preimage_hashes.get(
            relpath, edits[0].expected_sha256
        )
        if before_hash != expected_preimage:
            raise ValueError("semantic edit preview preimage changed: {}".format(relpath))
        lines = text.splitlines(keepends=True)
        for edit in sorted(
            edits,
            key=lambda item: (item.start_line, item.end_line),
            reverse=True,
        ):
            lines[edit.start_line - 1:edit.end_line] = edit.replacement.splitlines(keepends=True)
        safe_write_text(path, "".join(lines), stat.S_IMODE(path.stat().st_mode))
        after_hash = sha256_file(path)
        changed.add(relpath)
        semantic_metadata.extend({
            "path": edit.path,
            "start_line": edit.start_line,
            "end_line": edit.end_line,
            "reason": edit.reason,
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "p1_migration_protected": edit.p1_migration_protected,
        } for edit in edits)

    delete_tree_hashes = {relpath: _tree_hash(root, relpath) for relpath in deleted}
    rename_tree_hashes = {
        source: {"destination": destination, "source_hash": _tree_hash(root, source)}
        for source, destination in renames.items()
    }
    for source, destination in renames.items():
        source_path = preview_root / _safe_relpath(source)
        destination_path = preview_root / _safe_relpath(destination)
        if not source_path.exists() or destination_path.exists():
            raise ValueError("invalid rename: {} -> {}".format(source, destination))
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))
        rename_tree_hashes[source]["preview_hash"] = _tree_hash(preview_root, destination)
    for relpath in deleted:
        path = preview_root / _safe_relpath(relpath)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            raise ValueError("invalid delete path: {}".format(relpath))

    cleanup_staging_fd = _open_preview_cleanup_staging(run, root) if cleanup else -1
    try:
        cleanup_operations = [
            _remove_preview_cleanup_dir(
                preview_root, cleanup_staging_fd, relpath,
                cleanup_dir_states[relpath],
            )
            for relpath in cleanup
        ]
    finally:
        if cleanup_staging_fd >= 0:
            os.close(cleanup_staging_fd)
    _ensure_no_symlinks(preview_root)
    _assert_source_unchanged(
        root, source_records, source_tree_hash, source_state_hash,
    )

    source_hashes = {}
    for relpath in sorted(changed):
        source_hashes[relpath] = sha256_file(root / _safe_relpath(relpath))
    for relpath in deleted + list(renames):
        source_hashes.update({path: sha256_file(item) for path, item in _tree_files(root, relpath)})
    preview_hashes = {}
    for relpath in sorted(changed):
        rendered = _preview_relpath(relpath, renames)
        if not any(rendered == deleted_path or rendered.startswith(deleted_path + "/") for deleted_path in deleted):
            preview_hashes[rendered] = sha256_file(preview_root / _safe_relpath(rendered))
    for source in renames:
        for original, _path in _tree_files(root, source):
            rendered = _preview_relpath(original, renames)
            preview_hashes[rendered] = sha256_file(preview_root / _safe_relpath(rendered))

    diff_lines = []
    for relpath in sorted(changed):
        rendered = _preview_relpath(relpath, renames)
        before = (root / _safe_relpath(relpath)).read_text(encoding="utf-8").splitlines(True)
        after = (preview_root / _safe_relpath(rendered)).read_text(encoding="utf-8").splitlines(True)
        diff_lines.extend(difflib.unified_diff(before, after, "a/" + relpath, "b/" + rendered))
    for relpath in deleted:
        diff_lines.append("Binary/path deletion: {} (tree sha256 {})\n".format(relpath, delete_tree_hashes[relpath]))
    for source, destination in renames.items():
        detail = rename_tree_hashes[source]
        diff_lines.append("Binary/path rename: {} -> {} ({} -> {})\n".format(
            source, destination, detail["source_hash"], detail["preview_hash"]
        ))
    for operation in cleanup_operations:
        diff_lines.append(
            "Empty directory cleanup: {} (mode {:04o}, source state sha256 {})\n".format(
                operation["path"], operation["mode"], operation["source_state_sha256"],
            )
        )
    safe_write_text(run / "preview.diff", _redact_report_text("".join(diff_lines), decisions))

    binary_operations = _operation_records(root, deleted, "delete", renames)
    binary_operations.extend(_operation_records(root, renames, "rename", renames))
    for relpath in sorted(changed):
        binary_operations.append({"operation": "replace", "path": relpath, "destination": _preview_relpath(relpath, renames), "is_text": True})
    binary_operations.extend(cleanup_operations)
    safe_write_text(run / "binary-changes.json", json.dumps({"operations": binary_operations}, indent=2, sort_keys=True) + "\n")

    placeholders = []
    if decisions.brand_mode == "placeholder":
        values = {}
        for field, value in sorted(decisions.brand_profile.items()):
            values.setdefault(value, []).append(field)
        for value, identifiers in sorted(values.items()):
            locations = []
            occurrences = 0
            for record in _safe_file_records(preview_root):
                text = read_text(preview_root / str(record["relpath"]))
                count = text.count(value) if text is not None else 0
                if count:
                    occurrences += count
                    locations.append({"path": record["relpath"], "occurrences": count})
            neutral = value if any(
                value == known for known in PLACEHOLDER_PROFILE.values()
            ) else "<custom placeholder>"
            placeholders.append({
                "value": neutral,
                "identifiers": sorted(identifiers),
                "status": "present" if occurrences else "absent",
                "occurrences": occurrences,
                "locations": locations,
            })
    safe_write_text(run / "placeholders.json", json.dumps(placeholders, indent=2, sort_keys=True) + "\n")
    safe_write_text(
        run / "semantic-edits.json",
        json.dumps({"edits": semantic_metadata}, indent=2, sort_keys=True) + "\n",
    )

    preview_tree_hash = _snapshot_hash(_safe_file_records(preview_root, {_OWNER_FILE}))
    preview_state_hash = _state_hash(preview_root, {_OWNER_FILE})
    decision_hash = _token({
        "brand_mode": decisions.brand_mode,
        "brand_profile": decisions.brand_profile,
        "actions": sorted([
            {"finding_id": action.finding_id, "action": action.action, "replacement": action.replacement,
             "migration_plan": action.migration_plan, "rollback_plan": action.rollback_plan}
            for action in decisions.actions
        ], key=lambda item: item["finding_id"]),
        "text_edits": sorted([
            {
                "path": edit.path,
                "expected_sha256": edit.expected_sha256,
                "start_line": edit.start_line,
                "end_line": edit.end_line,
                "replacement": edit.replacement,
                "reason": edit.reason,
                "migration_plan": edit.migration_plan,
                "rollback_plan": edit.rollback_plan,
                "p1_migration_protected": edit.p1_migration_protected,
            }
            for edit in decisions.text_edits
        ], key=lambda item: (item["path"], item["start_line"], item["end_line"])),
        "delete_paths": deleted, "rename_paths": renames,
        "cleanup_empty_dirs": cleanup,
        "cleanup_dir_states": cleanup_dir_states,
    })
    artifact_hashes = {
        name: sha256_file(run / name)
        for name in (
            "preview.diff", "binary-changes.json", "placeholders.json",
            "semantic-edits.json",
        )
    }
    _assert_source_unchanged(
        root, source_records, source_tree_hash, source_state_hash,
    )
    core = {
        "run_id": sha256(str(run).encode("utf-8")).hexdigest()[:16],
        "project_root": str(root), "preview_root": str(preview_root.resolve()),
        "source_hashes": dict(sorted(source_hashes.items())),
        "preview_hashes": dict(sorted(preview_hashes.items())),
        "delete_tree_hashes": delete_tree_hashes, "rename_tree_hashes": rename_tree_hashes,
        "changed_paths": sorted(preview_hashes), "deleted_paths": deleted, "renamed_paths": renames,
        "cleanup_empty_dirs": cleanup, "cleanup_dir_states": cleanup_dir_states,
    }
    profile_hash = _token({"brand_profile": decisions.brand_profile})
    brand_result_hash = _token({
        "brand_mode": decisions.brand_mode,
        "profile_hash": profile_hash,
        "preview_hashes": core["preview_hashes"],
        "delete_tree_hashes": core["delete_tree_hashes"],
        "rename_tree_hashes": core["rename_tree_hashes"],
        "cleanup_empty_dirs": core["cleanup_empty_dirs"],
        "cleanup_dir_states": core["cleanup_dir_states"],
    })
    token_payload = dict(core)
    token_payload.update({
        "brand_mode": decisions.brand_mode, "brand_result_hash": brand_result_hash,
        "decision_hash": decision_hash, "source_tree_hash": source_tree_hash,
        "preview_tree_hash": preview_tree_hash, "source_state_hash": source_state_hash,
        "preview_state_hash": preview_state_hash, "artifact_hashes": artifact_hashes,
    })
    manifest = PreviewManifest(**core, approval_token=_token(token_payload))
    manifest_payload = asdict(manifest)
    manifest_payload.update({
        "brand_mode": decisions.brand_mode, "brand_result_hash": brand_result_hash,
        "decision_hash": decision_hash, "source_tree_hash": source_tree_hash,
        "preview_tree_hash": preview_tree_hash, "source_state_hash": source_state_hash,
        "preview_state_hash": preview_state_hash, "artifact_hashes": artifact_hashes,
    })
    safe_write_text(run / "manifest.json", json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n")

    safe_write_text(run / "preview.md", "\n".join([
        "# De-starter Preview", "", "- Brand mode: `{}`".format(decisions.brand_mode),
        "- Changed files: `{}`".format(len(preview_hashes)), "- Deleted paths: `{}`".format(len(deleted)),
        "- Renamed paths: `{}`".format(len(renames)),
        "- Cleaned empty directories: `{}`".format(len(cleanup)),
        "- Approval token: `{}`".format(manifest.approval_token), "",
        "- P1 migration-protected semantic edits: `{}`".format(sum(
            edit.p1_migration_protected for edit in decisions.text_edits
        )), "",
        "Review `audit.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, and `semantic-edits.json` before approval.", "",
    ]))
    return manifest
