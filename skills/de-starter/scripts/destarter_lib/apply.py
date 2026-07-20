"""Safely materialize a reviewed de-starter preview as one recoverable transaction."""

import difflib
import json
import os
import shutil
import stat
import tempfile
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from .files import sha256_file
from .models import ApplyResult, PreviewManifest
from .preview import (
    _OWNER_FILE, _contains, _contains_secret_or_ignored, _ensure_no_symlinks, _safe_file_records,
    _safe_relpath, _snapshot_hash, _state_hash, _token, _tree_hash,
)
from .report import redact_evidence


_BACKUP_OWNER = ".destarter-backup-owner.json"
_ARTIFACTS = ("preview.diff", "binary-changes.json", "placeholders.json")
_MANIFEST_KEYS = {
    "run_id", "project_root", "preview_root", "source_hashes", "preview_hashes",
    "delete_tree_hashes", "rename_tree_hashes", "changed_paths", "deleted_paths",
    "renamed_paths", "approval_token", "brand_mode", "brand_result_hash",
    "decision_hash", "source_tree_hash", "preview_tree_hash", "source_state_hash",
    "preview_state_hash", "artifact_hashes",
}


class ApplyError(RuntimeError):
    """The approved preview cannot be safely applied."""


def _fail(message: str) -> None:
    raise ApplyError(message)


def _load_json(path: Path) -> Mapping[str, object]:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _fail("invalid preview manifest: {}".format(error))
    if not isinstance(value, dict):
        _fail("invalid preview manifest")
    if set(value) != _MANIFEST_KEYS:
        _fail("invalid preview manifest keys")
    return value


def _require_string(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        _fail("invalid manifest {}".format(name))
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        _fail("invalid manifest {}".format(label))
    return value


def _rel(value: object, label: str) -> str:
    try:
        return _safe_relpath(value).as_posix()
    except (TypeError, ValueError) as error:
        _fail("invalid manifest {}: {}".format(label, error))
    raise AssertionError("unreachable")


def _hashes(value: object, label: str) -> Dict[str, str]:
    if not isinstance(value, dict):
        _fail("invalid manifest {}".format(label))
    result = {}
    for path, digest in value.items():
        relpath = _rel(path, label)
        result[relpath] = _digest(digest, "{} hash".format(label))
    if len(result) != len(value):
        _fail("invalid manifest {} duplicate path".format(label))
    return dict(sorted(result.items()))


def _paths(value: object, label: str) -> List[str]:
    if not isinstance(value, list):
        _fail("invalid manifest {}".format(label))
    result = [_rel(item, label) for item in value]
    if len(set(result)) != len(result):
        _fail("invalid manifest {} duplicate path".format(label))
    return sorted(result)


def _renames(value: object) -> Dict[str, str]:
    if not isinstance(value, dict):
        _fail("invalid manifest renamed_paths")
    result = {_rel(source, "renamed_paths"): _rel(destination, "renamed_paths") for source, destination in value.items()}
    if len(result) != len(value) or len(set(result.values())) != len(result):
        _fail("invalid manifest renamed_paths")
    return dict(sorted(result.items()))


def _rename_hashes(value: object, renames: Mapping[str, str]) -> Dict[str, Dict[str, str]]:
    if not isinstance(value, dict) or set(value) != set(renames):
        _fail("invalid manifest rename_tree_hashes")
    result = {}
    for source, details in value.items():
        if not isinstance(details, dict) or set(details) != {"destination", "source_hash", "preview_hash"}:
            _fail("invalid manifest rename_tree_hashes")
        if _rel(details["destination"], "rename_tree_hashes") != renames[source]:
            _fail("invalid manifest rename_tree_hashes")
        for name in ("source_hash", "preview_hash"):
            _digest(details[name], "rename_tree_hashes")
        result[source] = dict(details)
    return result


def _load_manifest(run: Path) -> Tuple[PreviewManifest, Mapping[str, object]]:
    payload = _load_json(run / "manifest.json")
    run_id = _require_string(payload, "run_id")
    project_root = _require_string(payload, "project_root")
    preview_root = _require_string(payload, "preview_root")
    token = _require_string(payload, "approval_token")
    source_hashes = _hashes(payload.get("source_hashes"), "source_hashes")
    preview_hashes = _hashes(payload.get("preview_hashes"), "preview_hashes")
    delete_hashes = _hashes(payload.get("delete_tree_hashes"), "delete_tree_hashes")
    changed = _paths(payload.get("changed_paths"), "changed_paths")
    deleted = _paths(payload.get("deleted_paths"), "deleted_paths")
    renames = _renames(payload.get("renamed_paths"))
    rename_hashes = _rename_hashes(payload.get("rename_tree_hashes"), renames)
    if payload.get("brand_mode") not in {"real", "placeholder"}:
        _fail("invalid manifest brand_mode")
    for name in ("brand_result_hash", "decision_hash", "source_tree_hash", "preview_tree_hash", "source_state_hash", "preview_state_hash"):
        _digest(payload.get(name), name)
    artifacts = _hashes(payload.get("artifact_hashes"), "artifact_hashes")
    if set(artifacts) != set(_ARTIFACTS):
        _fail("invalid manifest artifact_hashes")
    if set(changed) != set(preview_hashes) or set(deleted) != set(delete_hashes):
        _fail("invalid manifest operation hashes")
    core = {
        "run_id": run_id, "project_root": project_root, "preview_root": preview_root,
        "source_hashes": source_hashes, "preview_hashes": preview_hashes,
        "delete_tree_hashes": delete_hashes, "rename_tree_hashes": rename_hashes,
        "changed_paths": changed, "deleted_paths": deleted, "renamed_paths": renames,
    }
    additive = {name: payload[name] for name in (
        "brand_mode", "brand_result_hash", "decision_hash", "source_tree_hash", "preview_tree_hash", "source_state_hash", "preview_state_hash", "artifact_hashes"
    )}
    expected = _token(dict(core, **additive))
    if token != expected:
        _fail("manifest approval token is tampered or stale")
    return PreviewManifest(**core, approval_token=token), payload


def _under(root: str, path: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _inside_renamed_preview(manifest: PreviewManifest, path: str) -> bool:
    return any(_under(destination, path) for destination in manifest.renamed_paths.values())


def _validate_operation_shapes(manifest: PreviewManifest) -> None:
    sources = list(manifest.renamed_paths) + list(manifest.deleted_paths)
    destinations = list(manifest.renamed_paths.values())
    if any(_under(first, second) or _under(second, first) for index, first in enumerate(sources) for second in sources[index + 1:]):
        _fail("invalid manifest overlapping source operations")
    if any(_under(first, second) or _under(second, first) for index, first in enumerate(destinations) for second in destinations[index + 1:]):
        _fail("invalid manifest overlapping rename destinations")
    if any(_under(source, destination) or _under(destination, source) for source in sources for destination in destinations):
        _fail("invalid manifest rename overlap")
    for relpath in manifest.changed_paths:
        if any(_under(deleted, relpath) for deleted in manifest.deleted_paths):
            _fail("invalid manifest changed path under delete")


def _verify_approval(root: Path, run: Path, manifest: PreviewManifest, raw: Mapping[str, object], token: str) -> Path:
    if token != manifest.approval_token:
        _fail("approval token does not match current preview")
    if str(root) != manifest.project_root:
        _fail("project root does not match preview")
    preview = Path(manifest.preview_root)
    if preview != (run / "preview").resolve() or not preview.is_dir() or preview.is_symlink():
        _fail("preview root does not match run directory")
    try:
        owner = json.loads((preview / _OWNER_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _fail("preview ownership marker is invalid: {}".format(error))
    if owner != {"project_root": str(root)}:
        _fail("preview is not owned by this project")
    try:
        _ensure_no_symlinks(root)
        _ensure_no_symlinks(preview)
    except ValueError as error:
        _fail(str(error))
    _validate_operation_shapes(manifest)
    for relpath in list(manifest.deleted_paths) + list(manifest.renamed_paths):
        if _contains_secret_or_ignored(root, relpath):
            _fail("operation root contains excluded secret file or ignored metadata: {}".format(relpath))
    for relpath, expected in manifest.delete_tree_hashes.items():
        try:
            actual = _tree_hash(root, relpath)
        except ValueError:
            _fail("delete tree changed after preview: {}".format(relpath))
        if actual != expected:
            _fail("delete tree changed after preview: {}".format(relpath))
    for source, details in manifest.rename_tree_hashes.items():
        try:
            source_hash = _tree_hash(root, source)
            preview_hash = _tree_hash(preview, details["destination"])
        except ValueError:
            _fail("rename tree changed after preview: {}".format(source))
        if source_hash != details["source_hash"]:
            _fail("rename source changed after preview: {}".format(source))
        if preview_hash != details["preview_hash"]:
            _fail("rename preview changed after approval token creation: {}".format(source))
    for relpath, expected in manifest.source_hashes.items():
        source = root / _safe_relpath(relpath)
        if not source.is_file() or sha256_file(source) != expected:
            _fail("source changed after preview: {}".format(relpath))
    for relpath, expected in manifest.preview_hashes.items():
        candidate = preview / _safe_relpath(relpath)
        if not candidate.is_file() or sha256_file(candidate) != expected:
            _fail("preview changed after approval token creation: {}".format(relpath))
    if _snapshot_hash(_safe_file_records(root)) != raw["source_tree_hash"]:
        _fail("source changed after preview")
    if _snapshot_hash(_safe_file_records(preview, {_OWNER_FILE})) != raw["preview_tree_hash"]:
        _fail("preview changed after approval token creation")
    if _state_hash(root) != raw["source_state_hash"]:
        _fail("source changed after preview")
    if _state_hash(preview, {_OWNER_FILE}) != raw["preview_state_hash"]:
        _fail("preview changed after approval token creation")
    for name, expected in raw["artifact_hashes"].items():
        path = run / _safe_relpath(name)
        if not path.is_file() or sha256_file(path) != expected:
            _fail("preview artifact changed after approval token creation: {}".format(name))
    return preview


def _copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, copy_function=shutil.copy2)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _path_hash(path: Path) -> str:
    """Hash every file and empty directory in a backup, including mode bits."""
    entries = []
    if path.is_file():
        return sha256(("F::{}:{}".format(path.stat().st_mode & 0o777, sha256_file(path))).encode("utf-8")).hexdigest()
    for directory, dirs, files in os.walk(str(path), followlinks=False):
        current = Path(directory)
        entries.append("D:{}:{}".format(current.relative_to(path).as_posix(), current.stat().st_mode & 0o777))
        for name in sorted(dirs + files):
            child = current / name
            if child.is_symlink():
                _fail("backup source contains symlink")
            if child.is_file():
                entries.append("F:{}:{}:{}".format(child.relative_to(path).as_posix(), child.stat().st_mode & 0o777, sha256_file(child)))
    return sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


def _backup(root: Path, run: Path, manifest: PreviewManifest) -> Tuple[Path, List[Dict[str, str]]]:
    backup = run / "backup"
    if backup.exists():
        _fail("preview was already applied or backup directory is unowned")
    backup.mkdir(mode=0o700)
    try:
        (backup / _BACKUP_OWNER).write_text(json.dumps({"project_root": str(root), "run_id": manifest.run_id}, sort_keys=True) + "\n", encoding="utf-8")
        roots = sorted(set(manifest.deleted_paths) | set(manifest.renamed_paths) | {
            path for path in manifest.source_hashes
            if not any(_under(source, path) for source in manifest.renamed_paths)
            and not any(_under(deleted, path) for deleted in manifest.deleted_paths)
        })
        records = []
        for relpath in roots:
            source = root / _safe_relpath(relpath)
            if not source.exists() or source.is_symlink():
                _fail("preflight original path missing: {}".format(relpath))
            target = backup / "original" / _safe_relpath(relpath)
            _copy_path(source, target)
            original_hash, backup_hash = _path_hash(source), _path_hash(target)
            if original_hash != backup_hash:
                _fail("backup verification failed: {}".format(relpath))
            records.append({"path": relpath, "backup": str(target), "sha256": backup_hash})
        return backup, records
    except Exception:
        shutil.rmtree(backup, ignore_errors=True)
        raise


def _write_file_atomic(source: Path, destination: Path) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=".destarter-", dir=str(destination.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            with source.open("rb") as input_handle:
                shutil.copyfileobj(input_handle, handle)
        shutil.copystat(source, temporary)
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_text_atomic(destination: Path, text: str) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=".destarter-", dir=str(destination.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()


def _materialize_tree(preview: Path, destination: Path) -> None:
    temporary = Path(tempfile.mkdtemp(prefix=".destarter-", dir=str(destination.parent)))
    shutil.rmtree(temporary)
    try:
        _copy_path(preview, temporary)
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _rollback(root: Path, backup: Path, records: Iterable[Mapping[str, str]], manifest: PreviewManifest) -> None:
    for path in list(manifest.renamed_paths.values()) + [item["path"] for item in records]:
        candidate = root / _safe_relpath(path)
        if candidate.exists() or candidate.is_symlink():
            _remove(candidate)
    for item in records:
        original = root / _safe_relpath(item["path"])
        stored = Path(item["backup"])
        if _path_hash(stored) != item["sha256"]:
            raise ApplyError("rollback backup verification failed")
        _copy_path(stored, original)
        if _path_hash(original) != item["sha256"]:
            raise ApplyError("rollback verification failed")


def _reverse_diff(root: Path, preview: Path, manifest: PreviewManifest) -> str:
    lines = []
    for original, expected in sorted(manifest.source_hashes.items()):
        if any(_under(deleted, original) for deleted in manifest.deleted_paths):
            continue
        rendered = original
        for source, destination in manifest.renamed_paths.items():
            if _under(source, original):
                rendered = destination + original[len(source):]
                break
        before, after = root / _safe_relpath(original), preview / _safe_relpath(rendered)
        if before.is_file() and after.is_file():
            try:
                lines.extend(difflib.unified_diff(after.read_text(encoding="utf-8").splitlines(True), before.read_text(encoding="utf-8").splitlines(True), "a/" + rendered, "b/" + original))
            except UnicodeDecodeError:
                pass
    for relpath in manifest.deleted_paths:
        lines.append("Restore deleted path from verified backup: {}\n".format(relpath))
    for source, destination in manifest.renamed_paths.items():
        lines.append("Reverse rename: {} -> {}\n".format(destination, source))
    return redact_evidence("".join(lines))


def _fd_support() -> None:
    required = ("open", "rename", "replace", "unlink", "rmdir", "mkdir")
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or any(name not in os.supports_dir_fd for name in (os.rename, os.unlink, os.rmdir, os.mkdir)):
        _fail("safe descriptor-relative filesystem primitives are unavailable")


def _open_root(root: Path) -> int:
    _fd_support()
    return os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _open_parent(root_fd: int, relpath: str) -> Tuple[int, str]:
    parts = _safe_relpath(relpath).parts
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, parts[-1]
    except Exception:
        os.close(fd)
        raise


def _identity(fd: int, name: str) -> Tuple[int, int]:
    item = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if stat.S_ISLNK(item.st_mode):
        _fail("symlink appeared at mutation boundary")
    return item.st_dev, item.st_ino


def _fd_copy_file(source: Path, parent_fd: int, name: str, mode: int, replace: bool = False) -> Tuple[int, int]:
    temporary = ".destarter-{}".format(uuid.uuid4().hex)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(temporary, flags, mode, dir_fd=parent_fd)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as input_handle:
            shutil.copyfileobj(input_handle, output)
        if replace:
            os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        else:
            os.rename(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        return _identity(parent_fd, name)
    except Exception:
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except OSError:
            pass
        raise


def _fd_remove_tree(parent_fd: int, name: str) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            for entry in os.listdir(child):
                _fd_remove_tree(child, entry)
        finally:
            os.close(child)
        os.rmdir(name, dir_fd=parent_fd)
    else:
        os.unlink(name, dir_fd=parent_fd)


def _fd_copy_tree(source: Path, parent_fd: int, name: str) -> Tuple[int, int]:
    info = source.lstat()
    if source.is_symlink():
        _fail("preview symlink appeared at mutation boundary")
    if source.is_file():
        return _fd_copy_file(source, parent_fd, name, stat.S_IMODE(info.st_mode))
    os.mkdir(name, stat.S_IMODE(info.st_mode), dir_fd=parent_fd)
    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        for item in sorted(source.iterdir(), key=lambda path: path.name):
            _fd_copy_tree(item, child, item.name)
    except Exception:
        _fd_remove_tree(parent_fd, name)
        raise
    finally:
        os.close(child)
    return _identity(parent_fd, name)


def _fd_quarantine(root_fd: int, relpath: str) -> Tuple[int, str, str, Tuple[int, int]]:
    parent_fd, name = _open_parent(root_fd, relpath)
    identity = _identity(parent_fd, name)
    quarantine = ".destarter-quarantine-{}".format(uuid.uuid4().hex)
    os.rename(name, quarantine, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    return parent_fd, name, quarantine, identity


def _fd_restore_quarantine(record: Tuple[int, str, str, Tuple[int, int]]) -> None:
    parent_fd, name, quarantine, _identity_before = record
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        raise ApplyError("rollback cannot restore over raced original path")
    except FileNotFoundError:
        os.rename(quarantine, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)


def _fd_apply(root: Path, preview: Path, manifest: PreviewManifest) -> List[Tuple[int, str, Tuple[int, int]]]:
    """Mutate only through pinned no-follow directory descriptors."""
    root_fd = _open_root(root)
    quarantines = []
    created = []
    try:
        for relpath in list(manifest.deleted_paths) + list(manifest.renamed_paths):
            quarantines.append(_fd_quarantine(root_fd, relpath))
        for source, destination in manifest.renamed_paths.items():
            parent_fd, name = _open_parent(root_fd, destination)
            try:
                try:
                    os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                    _fail("rename destination appeared after preflight: {}".format(destination))
                except FileNotFoundError:
                    pass
                created.append((parent_fd, name, _fd_copy_tree(preview / _safe_relpath(destination), parent_fd, name)))
            except Exception:
                os.close(parent_fd)
                raise
        for relpath in manifest.changed_paths:
            if _inside_renamed_preview(manifest, relpath):
                continue
            parent_fd, name = _open_parent(root_fd, relpath)
            try:
                old = _identity(parent_fd, name)
                created.append((parent_fd, name, _fd_copy_file(preview / _safe_relpath(relpath), parent_fd, name,
                                                               stat.S_IMODE(os.stat(name, dir_fd=parent_fd, follow_symlinks=False).st_mode), replace=True)))
            except Exception:
                os.close(parent_fd)
                raise
        for record in quarantines:
            _fd_remove_tree(record[0], record[2])
        return created
    except Exception:
        for parent_fd, name, identity in reversed(created):
            try:
                if _identity(parent_fd, name) == identity:
                    _fd_remove_tree(parent_fd, name)
            except Exception:
                pass
            os.close(parent_fd)
        for record in reversed(quarantines):
            try:
                _fd_restore_quarantine(record)
            except Exception:
                pass
            os.close(record[0])
        raise
    finally:
        os.close(root_fd)


def apply_preview(project_root: Path, run_dir: Path, approval_token: str) -> ApplyResult:
    """Apply precisely the token-bound preview, restoring all originals on failure."""
    root, run = project_root.resolve(), run_dir.resolve()
    if not root.is_dir() or run.is_symlink() or _contains(root, run) or _contains(run, root):
        _fail("project and run directories must be disjoint real directories")
    manifest, raw = _load_manifest(run)
    preview = _verify_approval(root, run, manifest, raw, approval_token)
    # Preflight all destinations before creating the backup or changing source.
    for source, destination in manifest.renamed_paths.items():
        source_path, destination_path = root / _safe_relpath(source), root / _safe_relpath(destination)
        preview_path = preview / _safe_relpath(destination)
        if not source_path.exists() or source_path.is_symlink() or destination_path.exists() or destination_path.is_symlink() or not preview_path.exists() or not destination_path.parent.is_dir():
            _fail("rename preflight failed: {} -> {}".format(source, destination))
    for relpath in manifest.changed_paths:
        # Changed paths that are part of a renamed tree are materialized with that tree.
        if _inside_renamed_preview(manifest, relpath):
            continue
        source, final = root / _safe_relpath(relpath), preview / _safe_relpath(relpath)
        if not source.is_file() or source.is_symlink() or not final.is_file() or source.read_bytes().find(b"\x00") >= 0 or final.read_bytes().find(b"\x00") >= 0:
            _fail("text replacement preflight failed: {}".format(relpath))
    backup, records = _backup(root, run, manifest)
    try:
        # A backup is not authority to apply: source may have changed while copying it.
        _verify_approval(root, run, manifest, raw, approval_token)
    except Exception:
        shutil.rmtree(backup, ignore_errors=True)
        raise
    try:
        for relpath in list(manifest.deleted_paths) + list(manifest.renamed_paths):
            if _contains_secret_or_ignored(root, relpath):
                _fail("operation root contains excluded secret file or ignored metadata: {}".format(relpath))
        reverse = _reverse_diff(root, preview, manifest)
        _fd_apply(root, preview, manifest)
        for relpath, expected in manifest.preview_hashes.items():
            target = root / _safe_relpath(relpath)
            if not target.is_file() or sha256_file(target) != expected:
                _fail("post-apply verification failed: {}".format(relpath))
        if any((root / _safe_relpath(path)).exists() for path in manifest.deleted_paths):
            _fail("post-apply deletion verification failed")
        if any((root / _safe_relpath(path)).exists() for path in manifest.renamed_paths):
            _fail("post-apply rename verification failed")
        if _snapshot_hash(_safe_file_records(root)) != raw["preview_tree_hash"]:
            _fail("post-apply preview verification failed")
        restore_path = run / "restore.json"
        _write_text_atomic(restore_path, json.dumps({
            "backup_root": str(backup), "operations": records,
            "deleted_paths": manifest.deleted_paths, "renamed_paths": manifest.renamed_paths,
        }, indent=2, sort_keys=True) + "\n")
        _write_text_atomic(run / "reverse.diff", reverse)
    except Exception as error:
        try:
            _rollback(root, backup, records, manifest)
        except Exception as rollback_error:
            raise ApplyError("apply failed and rollback failed: {}".format(rollback_error)) from error
        for artifact in (run / "restore.json", run / "reverse.diff"):
            if artifact.exists():
                artifact.unlink()
        raise ApplyError("apply failed; changes rolled back: {}".format(error)) from error
    return ApplyResult(manifest.run_id, manifest.changed_paths, manifest.deleted_paths,
                       manifest.renamed_paths, str(backup), str(run / "restore.json"))
