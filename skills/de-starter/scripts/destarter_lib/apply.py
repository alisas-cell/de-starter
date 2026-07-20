"""Apply an approved preview through one fail-closed, descriptor-owned transaction."""

import difflib
import json
import os
import stat
import uuid
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .files import sha256_file
from .models import ApplyResult, PreviewManifest
from .preview import (
    _OWNER_FILE,
    _contains,
    _contains_secret_or_ignored,
    _ensure_no_symlinks,
    _is_ignored_name,
    _is_secret_name,
    _safe_file_records,
    _safe_relpath,
    _snapshot_hash,
    _state_hash,
    _token,
    _tree_hash,
)
from .report import redact_evidence


_BACKUP_OWNER = ".destarter-backup-owner.json"
_ARTIFACTS = ("preview.diff", "binary-changes.json", "placeholders.json")
_RESULT_ARTIFACTS = ("restore.json", "reverse.diff")
_MANIFEST_KEYS = {
    "run_id", "project_root", "preview_root", "source_hashes", "preview_hashes",
    "delete_tree_hashes", "rename_tree_hashes", "changed_paths", "deleted_paths",
    "renamed_paths", "approval_token", "brand_mode", "brand_result_hash",
    "decision_hash", "source_tree_hash", "preview_tree_hash", "source_state_hash",
    "preview_state_hash", "artifact_hashes",
}
Identity = Tuple[int, int]


class ApplyError(RuntimeError):
    """The approved preview cannot be safely applied."""


@dataclass(frozen=True)
class ObjectState:
    identity: Identity
    digest: str
    kind: str
    forbidden: bool


@dataclass
class Original:
    relpath: str
    parent_fd: int
    name: str
    expected: ObjectState
    backup_name: str
    moved: Optional[ObjectState] = None


@dataclass
class Output:
    relpath: str
    parent_fd: int
    name: str
    preview_parent_fd: int
    preview_name: str
    expected: ObjectState
    initially_absent: bool
    created: Optional[ObjectState] = None


@dataclass
class Artifact:
    name: str
    expected: ObjectState


@dataclass
class Transaction:
    root: Path
    run: Path
    preview: Path
    manifest: PreviewManifest
    raw: Mapping[str, object]
    root_fd: int
    run_fd: int
    preview_fd: int
    backup_fd: int
    original_fd: int
    backup_identity: Identity
    original_identity: Identity
    owner_state: ObjectState
    originals: List[Original]
    outputs: List[Output]
    ambient: Dict[str, Identity]
    fds: List[int] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    backup_exists: bool = True

    def close(self) -> None:
        for descriptor in reversed(self.fds):
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.fds[:] = []


def _fail(message: str) -> None:
    raise ApplyError(message)


def _load_json(path: Path) -> Mapping[str, object]:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key: {}".format(key))
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeError, ValueError) as error:
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
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
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
    result = {
        _rel(source, "renamed_paths"): _rel(destination, "renamed_paths")
        for source, destination in value.items()
    }
    if len(result) != len(value) or len(set(result.values())) != len(result):
        _fail("invalid manifest renamed_paths")
    return dict(sorted(result.items()))


def _rename_hashes(
    value: object, renames: Mapping[str, str]
) -> Dict[str, Dict[str, str]]:
    if not isinstance(value, dict) or set(value) != set(renames):
        _fail("invalid manifest rename_tree_hashes")
    result = {}
    for source, details in value.items():
        if (
            not isinstance(details, dict)
            or set(details) != {"destination", "source_hash", "preview_hash"}
        ):
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
    delete_hashes = _hashes(
        payload.get("delete_tree_hashes"), "delete_tree_hashes"
    )
    changed = _paths(payload.get("changed_paths"), "changed_paths")
    deleted = _paths(payload.get("deleted_paths"), "deleted_paths")
    renames = _renames(payload.get("renamed_paths"))
    rename_hashes = _rename_hashes(
        payload.get("rename_tree_hashes"), renames
    )
    if payload.get("brand_mode") not in {"real", "placeholder"}:
        _fail("invalid manifest brand_mode")
    for name in (
        "brand_result_hash", "decision_hash", "source_tree_hash",
        "preview_tree_hash", "source_state_hash", "preview_state_hash",
    ):
        _digest(payload.get(name), name)
    artifacts = _hashes(payload.get("artifact_hashes"), "artifact_hashes")
    if set(artifacts) != set(_ARTIFACTS):
        _fail("invalid manifest artifact_hashes")
    if set(changed) != set(preview_hashes) or set(deleted) != set(delete_hashes):
        _fail("invalid manifest operation hashes")
    core = {
        "run_id": run_id,
        "project_root": project_root,
        "preview_root": preview_root,
        "source_hashes": source_hashes,
        "preview_hashes": preview_hashes,
        "delete_tree_hashes": delete_hashes,
        "rename_tree_hashes": rename_hashes,
        "changed_paths": changed,
        "deleted_paths": deleted,
        "renamed_paths": renames,
    }
    additive = {
        name: payload[name]
        for name in (
            "brand_mode", "brand_result_hash", "decision_hash",
            "source_tree_hash", "preview_tree_hash", "source_state_hash",
            "preview_state_hash", "artifact_hashes",
        )
    }
    if token != _token(dict(core, **additive)):
        _fail("manifest approval token is tampered or stale")
    return PreviewManifest(**core, approval_token=token), payload


def _under(root: str, path: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _inside_renamed_preview(manifest: PreviewManifest, path: str) -> bool:
    return any(
        _under(destination, path)
        for destination in manifest.renamed_paths.values()
    )


def _validate_operation_shapes(manifest: PreviewManifest) -> None:
    sources = list(manifest.renamed_paths) + list(manifest.deleted_paths)
    destinations = list(manifest.renamed_paths.values())
    if any(
        _under(first, second) or _under(second, first)
        for index, first in enumerate(sources)
        for second in sources[index + 1:]
    ):
        _fail("invalid manifest overlapping source operations")
    if any(
        _under(first, second) or _under(second, first)
        for index, first in enumerate(destinations)
        for second in destinations[index + 1:]
    ):
        _fail("invalid manifest overlapping rename destinations")
    if any(
        _under(source, destination) or _under(destination, source)
        for source in sources
        for destination in destinations
    ):
        _fail("invalid manifest rename overlap")
    for relpath in manifest.changed_paths:
        if any(_under(deleted, relpath) for deleted in manifest.deleted_paths):
            _fail("invalid manifest changed path under delete")


def _verify_approval(
    root: Path,
    run: Path,
    manifest: PreviewManifest,
    raw: Mapping[str, object],
    token: str,
) -> Path:
    """Do the token/source verification before any backup object is created."""
    if token != manifest.approval_token:
        _fail("approval token does not match current preview")
    if str(root) != manifest.project_root:
        _fail("project root does not match preview")
    preview = Path(manifest.preview_root)
    if (
        preview != (run / "preview").resolve()
        or not preview.is_dir()
        or preview.is_symlink()
    ):
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
            _fail(
                "operation root contains excluded secret file or ignored "
                "metadata: {}".format(relpath)
            )
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
            _fail(
                "rename preview changed after approval token creation: "
                "{}".format(source)
            )
    for relpath, expected in manifest.source_hashes.items():
        source = root / _safe_relpath(relpath)
        if not source.is_file() or sha256_file(source) != expected:
            _fail("source changed after preview: {}".format(relpath))
    for relpath, expected in manifest.preview_hashes.items():
        candidate = preview / _safe_relpath(relpath)
        if not candidate.is_file() or sha256_file(candidate) != expected:
            _fail(
                "preview changed after approval token creation: "
                "{}".format(relpath)
            )
    if _snapshot_hash(_safe_file_records(root)) != raw["source_tree_hash"]:
        _fail("source changed after preview")
    if (
        _snapshot_hash(_safe_file_records(preview, {_OWNER_FILE}))
        != raw["preview_tree_hash"]
    ):
        _fail("preview changed after approval token creation")
    if _state_hash(root) != raw["source_state_hash"]:
        _fail("source changed after preview")
    if _state_hash(preview, {_OWNER_FILE}) != raw["preview_state_hash"]:
        _fail("preview changed after approval token creation")
    for name, expected in raw["artifact_hashes"].items():
        path = run / _safe_relpath(name)
        if not path.is_file() or sha256_file(path) != expected:
            _fail(
                "preview artifact changed after approval token creation: "
                "{}".format(name)
            )
    return preview


def _reverse_diff(
    root: Path, preview: Path, manifest: PreviewManifest
) -> str:
    lines = []
    for original in sorted(manifest.source_hashes):
        if any(
            _under(deleted, original) for deleted in manifest.deleted_paths
        ):
            continue
        rendered = original
        for source, destination in manifest.renamed_paths.items():
            if _under(source, original):
                rendered = destination + original[len(source):]
                break
        before = root / _safe_relpath(original)
        after = preview / _safe_relpath(rendered)
        if before.is_file() and after.is_file():
            try:
                lines.extend(
                    difflib.unified_diff(
                        after.read_text(encoding="utf-8").splitlines(True),
                        before.read_text(encoding="utf-8").splitlines(True),
                        "a/" + rendered,
                        "b/" + original,
                    )
                )
            except UnicodeDecodeError:
                pass
    for relpath in manifest.deleted_paths:
        lines.append(
            "Restore deleted path from verified backup: {}\n".format(relpath)
        )
    for source, destination in manifest.renamed_paths.items():
        lines.append(
            "Reverse rename: {} -> {}\n".format(destination, source)
        )
    return redact_evidence("".join(lines))


def _fd_support() -> None:
    required_dir_fd = {
        os.open, os.stat, os.rename, os.unlink, os.rmdir, os.mkdir, os.link,
    }
    required_follow = {os.stat, os.link}
    if (
        os.name != "posix"
        or not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or not required_dir_fd.issubset(os.supports_dir_fd)
        or not required_follow.issubset(os.supports_follow_symlinks)
    ):
        _fail("safe descriptor-relative filesystem primitives are unavailable")


def _open_directory(path: Path) -> int:
    return os.open(
        str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )


def _open_parent(root_fd: int, relpath: str) -> Tuple[int, str]:
    parts = _safe_relpath(relpath).parts
    descriptor = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_fd
        return descriptor, parts[-1]
    except Exception:
        os.close(descriptor)
        raise


def _identity_from_stat(info: os.stat_result) -> Identity:
    return info.st_dev, info.st_ino


def _identity_at(parent_fd: int, name: str) -> Identity:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(info.st_mode):
        _fail("symlink appeared at transaction boundary")
    return _identity_from_stat(info)


def _identity_path(path: Path) -> Identity:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        _fail("ambient ancestor is no longer a real directory: {}".format(path))
    return _identity_from_stat(info)


def _hash_open_file(descriptor: int) -> str:
    digest = sha256()
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def _scan_open_object(
    descriptor: int,
    relpath: str,
    entries: List[Mapping[str, object]],
    *,
    safe_only: bool,
    excluded_names: Set[str],
) -> bool:
    info = os.fstat(descriptor)
    mode = stat.S_IMODE(info.st_mode)
    name = Path(relpath).name if relpath else ""
    forbidden = bool(
        name and (_is_secret_name(name) or _is_ignored_name(name))
    )
    if stat.S_ISREG(info.st_mode):
        entries.append({
            "kind": "file",
            "path": relpath,
            "mode": mode,
            "sha256": _hash_open_file(descriptor),
        })
        return forbidden
    if not stat.S_ISDIR(info.st_mode):
        _fail("transaction object has unsupported filesystem type")
    entries.append({"kind": "dir", "path": relpath, "mode": mode})
    for child_name in sorted(os.listdir(descriptor)):
        child_forbidden = (
            _is_secret_name(child_name) or _is_ignored_name(child_name)
        )
        if safe_only and (
            child_name in excluded_names or child_forbidden
        ):
            continue
        child = os.open(
            child_name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=descriptor,
        )
        try:
            child_path = (
                child_name if relpath in {"", "."}
                else relpath.rstrip("/") + "/" + child_name
            )
            forbidden = (
                _scan_open_object(
                    child,
                    child_path,
                    entries,
                    safe_only=safe_only,
                    excluded_names=excluded_names,
                )
                or forbidden
                or child_forbidden
            )
        finally:
            os.close(child)
    return forbidden


def _state_from_open(
    descriptor: int,
    *,
    safe_only: bool = False,
    excluded_names: Iterable[str] = (),
) -> ObjectState:
    info = os.fstat(descriptor)
    entries: List[Mapping[str, object]] = []
    forbidden = _scan_open_object(
        descriptor,
        ".",
        entries,
        safe_only=safe_only,
        excluded_names=set(excluded_names),
    )
    ordered = sorted(
        entries,
        key=lambda item: (str(item["path"]), str(item["kind"])),
    )
    kind = "dir" if stat.S_ISDIR(info.st_mode) else "file"
    return ObjectState(
        _identity_from_stat(info),
        _token({"state": ordered}),
        kind,
        forbidden,
    )


def _state_at(parent_fd: int, name: str) -> ObjectState:
    descriptor = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd
    )
    try:
        state = _state_from_open(descriptor)
        if state.identity != _identity_at(parent_fd, name):
            _fail("transaction object changed while being inspected")
        return state
    finally:
        os.close(descriptor)


def _same_content_state(first: ObjectState, second: ObjectState) -> bool:
    return (
        first.digest == second.digest
        and first.kind == second.kind
        and first.forbidden == second.forbidden
    )


def _safe_root_digest(
    descriptor: int, excluded_names: Iterable[str] = ()
) -> str:
    return _state_from_open(
        descriptor, safe_only=True, excluded_names=excluded_names
    ).digest


def _hash_file_at(parent_fd: int, name: str) -> str:
    descriptor = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd
    )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _fail("preview artifact is not a regular file: {}".format(name))
        return _hash_open_file(descriptor)
    finally:
        os.close(descriptor)


def _same_filesystem(root_fd: int, run_fd: int) -> bool:
    return os.fstat(root_fd).st_dev == os.fstat(run_fd).st_dev


def _path_ancestors(path: Path) -> Iterable[Path]:
    current = path
    values = []
    while True:
        values.append(current)
        if current.parent == current:
            break
        current = current.parent
    return reversed(values)


def _capture_ambient(paths: Iterable[Path]) -> Dict[str, Identity]:
    result: Dict[str, Identity] = {}
    for path in paths:
        for ancestor in _path_ancestors(path):
            result[str(ancestor)] = _identity_path(ancestor)
    return result


def _verify_ambient(transaction: Transaction) -> None:
    for value, expected in transaction.ambient.items():
        path = Path(value)
        try:
            actual = _identity_path(path)
        except (OSError, ApplyError) as error:
            _fail("ambient topology changed: {}: {}".format(path, error))
        if actual != expected:
            _fail("ambient topology changed: {}".format(path))


def _absent(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        return False
    except FileNotFoundError:
        return True


def _exclusive_file(
    parent_fd: int, name: str, content: bytes, mode: int = 0o600
) -> ObjectState:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
        dir_fd=parent_fd,
    )
    try:
        os.fchmod(descriptor, mode)
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
    finally:
        os.close(descriptor)
    return _state_at(parent_fd, name)


def _mkdir_exclusive(parent_fd: int, name: str, mode: int) -> Tuple[int, Identity]:
    os.mkdir(name, mode, dir_fd=parent_fd)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        dir_fd=parent_fd,
    )
    os.fchmod(descriptor, mode)
    return descriptor, _identity_from_stat(os.fstat(descriptor))


def _affected_paths(manifest: PreviewManifest) -> List[str]:
    standalone = {
        path
        for path in manifest.changed_paths
        if not _inside_renamed_preview(manifest, path)
    }
    return sorted(
        set(manifest.deleted_paths)
        | set(manifest.renamed_paths)
        | standalone
    )


def _output_paths(manifest: PreviewManifest) -> List[Tuple[str, bool]]:
    result = [
        (destination, True)
        for destination in manifest.renamed_paths.values()
    ]
    result.extend(
        (path, False)
        for path in manifest.changed_paths
        if not _inside_renamed_preview(manifest, path)
    )
    return sorted(result)


def _prepare_transaction(
    root: Path,
    run: Path,
    preview: Path,
    manifest: PreviewManifest,
    raw: Mapping[str, object],
) -> Transaction:
    """Pin every authority before creating the empty external backup."""
    fds: List[int] = []
    preview_fd = -1
    backup_fd = -1
    original_fd = -1
    backup_identity: Identity = (-1, -1)
    original_identity: Identity = (-1, -1)
    owner_state = ObjectState((-1, -1), "", "file", False)
    root_fd = _open_directory(root)
    fds.append(root_fd)
    run_fd = _open_directory(run)
    fds.append(run_fd)
    try:
        if not _same_filesystem(root_fd, run_fd):
            _fail(
                "project and run directories must be on the same filesystem "
                "for safe apply"
            )
        for name in _RESULT_ARTIFACTS:
            if not _absent(run_fd, name):
                _fail("successful apply artifact already exists: {}".format(name))
        if not _absent(run_fd, "backup"):
            _fail("preview was already applied or backup directory is unowned")

        preview_fd = os.open(
            "preview",
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=run_fd,
        )
        fds.append(preview_fd)
        if _identity_from_stat(os.fstat(preview_fd)) != _identity_path(preview):
            _fail("preview directory changed while being pinned")

        os.mkdir("backup", 0o700, dir_fd=run_fd)
        backup_fd = os.open(
            "backup",
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=run_fd,
        )
        fds.append(backup_fd)
        os.fchmod(backup_fd, 0o700)
        backup_identity = _identity_from_stat(os.fstat(backup_fd))
        original_fd, original_identity = _mkdir_exclusive(
            backup_fd, "original", 0o700
        )
        fds.append(original_fd)
        owner_payload = json.dumps(
            {"project_root": str(root), "run_id": manifest.run_id},
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        owner_state = _exclusive_file(
            backup_fd, _BACKUP_OWNER, owner_payload
        )

        originals = []
        for index, relpath in enumerate(_affected_paths(manifest)):
            parent_fd, name = _open_parent(root_fd, relpath)
            fds.append(parent_fd)
            expected = _state_at(parent_fd, name)
            backup_device = os.fstat(original_fd).st_dev
            if (
                expected.identity[0] != backup_device
                or os.fstat(parent_fd).st_dev != backup_device
            ):
                _fail(
                    "affected original is not on the external backup "
                    "filesystem: {}".format(relpath)
                )
            if expected.forbidden:
                _fail(
                    "operation root contains excluded secret file or ignored "
                    "metadata: {}".format(relpath)
                )
            originals.append(
                Original(
                    relpath,
                    parent_fd,
                    name,
                    expected,
                    "{:04d}-{}".format(index, uuid.uuid4().hex),
                )
            )

        outputs = []
        rename_destinations = set(manifest.renamed_paths.values())
        for relpath, initially_absent in _output_paths(manifest):
            parent_fd, name = _open_parent(root_fd, relpath)
            fds.append(parent_fd)
            if os.fstat(parent_fd).st_dev != os.fstat(original_fd).st_dev:
                _fail(
                    "output parent is not on the external backup "
                    "filesystem: {}".format(relpath)
                )
            if initially_absent:
                if not _absent(parent_fd, name):
                    _fail(
                        "rename destination already exists: {}".format(relpath)
                    )
            elif _absent(parent_fd, name):
                _fail("standalone source is missing: {}".format(relpath))
            preview_parent_fd, preview_name = _open_parent(
                preview_fd, relpath
            )
            fds.append(preview_parent_fd)
            expected = _state_at(preview_parent_fd, preview_name)
            outputs.append(
                Output(
                    relpath,
                    parent_fd,
                    name,
                    preview_parent_fd,
                    preview_name,
                    expected,
                    relpath in rename_destinations,
                )
            )

        ambient_paths: List[Path] = [root, run, preview, run / "backup", run / "backup" / "original"]
        ambient_paths.extend(
            root / _safe_relpath(item.relpath).parent
            for item in originals
        )
        ambient_paths.extend(
            root / _safe_relpath(item.relpath).parent
            for item in outputs
        )
        transaction = Transaction(
            root,
            run,
            preview,
            manifest,
            raw,
            root_fd,
            run_fd,
            preview_fd,
            backup_fd,
            original_fd,
            backup_identity,
            original_identity,
            owner_state,
            originals,
            outputs,
            _capture_ambient(ambient_paths),
            fds,
        )
        _verify_pinned_approval(transaction)
        return transaction
    except Exception:
        temporary = Transaction(
            root, run, preview, manifest, raw, root_fd, run_fd,
            preview_fd, backup_fd, original_fd,
            backup_identity, original_identity, owner_state, [], [], {}, fds,
        )
        _cleanup_empty_backup(temporary)
        temporary.close()
        raise


def _verify_pinned_approval(transaction: Transaction) -> None:
    """Second verification, through pinned descriptors, before final entry."""
    _verify_ambient(transaction)
    for original in transaction.originals:
        actual = _state_at(original.parent_fd, original.name)
        if actual.forbidden:
            _fail(
                "operation root contains excluded secret file or ignored "
                "metadata: {}".format(original.relpath)
            )
        if actual != original.expected:
            _fail("source changed after preview: {}".format(original.relpath))
    original_by_path = {
        item.relpath: item for item in transaction.originals
    }
    for output in transaction.outputs:
        if output.initially_absent:
            if not _absent(output.parent_fd, output.name):
                _fail(
                    "rename destination appeared after preflight: "
                    "{}".format(output.relpath)
                )
        else:
            original = original_by_path[output.relpath]
            if _state_at(output.parent_fd, output.name) != original.expected:
                _fail("source changed after preview: {}".format(output.relpath))
        if (
            _state_at(output.preview_parent_fd, output.preview_name)
            != output.expected
        ):
            _fail(
                "preview changed after approval token creation: "
                "{}".format(output.relpath)
            )
    if (
        _safe_root_digest(transaction.root_fd)
        != transaction.raw["source_state_hash"]
    ):
        _fail("source changed after preview")
    if (
        _safe_root_digest(transaction.preview_fd, {_OWNER_FILE})
        != transaction.raw["preview_state_hash"]
    ):
        _fail("preview changed after approval token creation")
    for name, expected in transaction.raw["artifact_hashes"].items():
        if _hash_file_at(transaction.run_fd, name) != expected:
            _fail(
                "preview artifact changed after approval token creation: "
                "{}".format(name)
            )


def _move_originals(transaction: Transaction) -> None:
    for original in transaction.originals:
        if not _absent(transaction.original_fd, original.backup_name):
            _fail("unique backup destination was unexpectedly occupied")
        os.rename(
            original.name,
            original.backup_name,
            src_dir_fd=original.parent_fd,
            dst_dir_fd=transaction.original_fd,
        )
        moved = _state_at(transaction.original_fd, original.backup_name)
        original.moved = moved
        if moved != original.expected:
            _fail(
                "source changed at atomic move boundary: "
                "{}".format(original.relpath)
            )


def _copy_children(source_fd: int, destination_fd: int) -> None:
    for name in sorted(os.listdir(source_fd)):
        source = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_fd
        )
        try:
            info = os.fstat(source)
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISREG(info.st_mode):
                destination = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    mode,
                    dir_fd=destination_fd,
                )
                try:
                    os.fchmod(destination, mode)
                    while True:
                        chunk = os.read(source, 1024 * 1024)
                        if not chunk:
                            break
                        view = memoryview(chunk)
                        while view:
                            written = os.write(destination, view)
                            view = view[written:]
                finally:
                    os.close(destination)
            elif stat.S_ISDIR(info.st_mode):
                child, _identity = _mkdir_exclusive(
                    destination_fd, name, mode
                )
                try:
                    _copy_children(source, child)
                finally:
                    os.close(child)
            else:
                _fail("preview contains unsupported filesystem object")
        finally:
            os.close(source)


def _copy_output(output: Output) -> None:
    source = os.open(
        output.preview_name,
        os.O_RDONLY | os.O_NOFOLLOW,
        dir_fd=output.preview_parent_fd,
    )
    try:
        info = os.fstat(source)
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):
            destination = os.open(
                output.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                mode,
                dir_fd=output.parent_fd,
            )
            try:
                os.fchmod(destination, mode)
                output.created = ObjectState(
                    _identity_from_stat(os.fstat(destination)),
                    "",
                    "file",
                    False,
                )
                while True:
                    chunk = os.read(source, 1024 * 1024)
                    if not chunk:
                        break
                    view = memoryview(chunk)
                    while view:
                        written = os.write(destination, view)
                        view = view[written:]
            finally:
                os.close(destination)
        elif stat.S_ISDIR(info.st_mode):
            destination, identity = _mkdir_exclusive(
                output.parent_fd, output.name, mode
            )
            output.created = ObjectState(identity, "", "dir", False)
            try:
                _copy_children(source, destination)
            finally:
                os.close(destination)
        else:
            _fail("preview contains unsupported filesystem object")
        output.created = _state_at(output.parent_fd, output.name)
        if not _same_content_state(output.created, output.expected):
            _fail("created output does not match preview: {}".format(output.relpath))
    finally:
        os.close(source)


def _create_outputs(transaction: Transaction) -> None:
    for output in transaction.outputs:
        if not _absent(output.parent_fd, output.name):
            _fail(
                "output destination appeared during transaction: "
                "{}".format(output.relpath)
            )
        _copy_output(output)


def _verify_backups(transaction: Transaction) -> None:
    if (
        _identity_at(transaction.run_fd, "backup")
        != transaction.backup_identity
        or _identity_at(transaction.backup_fd, "original")
        != transaction.original_identity
        or _state_at(transaction.backup_fd, _BACKUP_OWNER)
        != transaction.owner_state
    ):
        _fail("external backup scaffold identity or state changed")
    for original in transaction.originals:
        if original.moved is None:
            _fail("original was not moved to external backup")
        actual = _state_at(transaction.original_fd, original.backup_name)
        if actual != original.moved or actual != original.expected:
            _fail("external backup verification failed: {}".format(original.relpath))


def _fd_transaction(transaction: Transaction) -> None:
    """Final entry: recheck, move originals externally, then create exclusively."""
    _verify_pinned_approval(transaction)
    _move_originals(transaction)
    _verify_backups(transaction)
    _create_outputs(transaction)


def _verify_success(transaction: Transaction) -> None:
    _verify_ambient(transaction)
    _verify_backups(transaction)
    for original in transaction.originals:
        if not _absent(original.parent_fd, original.name):
            matching_output = next(
                (
                    output
                    for output in transaction.outputs
                    if output.relpath == original.relpath
                ),
                None,
            )
            if matching_output is None:
                _fail(
                    "original name reappeared after move: "
                    "{}".format(original.relpath)
                )
    for output in transaction.outputs:
        if output.created is None:
            _fail("approved output is missing: {}".format(output.relpath))
        actual = _state_at(output.parent_fd, output.name)
        if (
            actual != output.created
            or not _same_content_state(actual, output.expected)
        ):
            _fail(
                "post-apply output identity or state changed: "
                "{}".format(output.relpath)
            )
    if (
        _safe_root_digest(transaction.root_fd)
        != transaction.raw["preview_state_hash"]
    ):
        _fail("post-apply visible project state does not match preview")


def _write_artifact_atomic(
    transaction: Transaction, name: str, content: str
) -> Artifact:
    temporary = ".destarter-artifact-{}".format(uuid.uuid4().hex)
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=transaction.run_fd,
    )
    try:
        os.fchmod(descriptor, 0o600)
        data = content.encode("utf-8")
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
    finally:
        os.close(descriptor)
    try:
        os.link(
            temporary,
            name,
            src_dir_fd=transaction.run_fd,
            dst_dir_fd=transaction.run_fd,
            follow_symlinks=False,
        )
        expected = _state_at(transaction.run_fd, name)
        artifact = Artifact(name, expected)
        transaction.artifacts.append(artifact)
        return artifact
    finally:
        try:
            os.unlink(temporary, dir_fd=transaction.run_fd)
        except OSError:
            pass


def _remove_tree(parent_fd: int, name: str) -> None:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        child = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            for entry in os.listdir(child):
                _remove_tree(child, entry)
        finally:
            os.close(child)
        os.rmdir(name, dir_fd=parent_fd)
    elif stat.S_ISREG(info.st_mode):
        os.unlink(name, dir_fd=parent_fd)
    else:
        _fail("refusing to remove unsupported or linked transaction object")


def _remove_exact_to_trash(
    transaction: Transaction,
    parent_fd: int,
    name: str,
    expected: ObjectState,
    label: str,
) -> Optional[str]:
    if _absent(parent_fd, name):
        return "{} disappeared before rollback".format(label)
    actual = _state_at(parent_fd, name)
    if actual != expected:
        return "{} was raced or replaced; preserved".format(label)
    trash = "rollback-output-{}".format(uuid.uuid4().hex)
    os.rename(
        name,
        trash,
        src_dir_fd=parent_fd,
        dst_dir_fd=transaction.original_fd,
    )
    moved = _state_at(transaction.original_fd, trash)
    if moved != expected:
        if _absent(parent_fd, name):
            os.rename(
                trash,
                name,
                src_dir_fd=transaction.original_fd,
                dst_dir_fd=parent_fd,
            )
        return "{} changed at rollback boundary; preserved".format(label)
    _remove_tree(transaction.original_fd, trash)
    return None


def _rollback(transaction: Transaction) -> List[str]:
    """Restore only identities and complete states owned by this transaction."""
    errors: List[str] = []
    for artifact in reversed(transaction.artifacts):
        error = _remove_exact_to_trash(
            transaction,
            transaction.run_fd,
            artifact.name,
            artifact.expected,
            "artifact {}".format(artifact.name),
        )
        if error:
            errors.append(error)
    for output in reversed(transaction.outputs):
        if output.created is None:
            if not _absent(output.parent_fd, output.name):
                errors.append(
                    "partial output {} was preserved".format(output.relpath)
                )
            continue
        error = _remove_exact_to_trash(
            transaction,
            output.parent_fd,
            output.name,
            output.created,
            "output {}".format(output.relpath),
        )
        if error:
            errors.append(error)
    for original in reversed(transaction.originals):
        if original.moved is None:
            continue
        try:
            backup = _state_at(
                transaction.original_fd, original.backup_name
            )
        except Exception as error:
            errors.append(
                "backup {} cannot be verified: {}".format(
                    original.relpath, error
                )
            )
            continue
        if backup != original.moved:
            errors.append(
                "backup {} changed; preserved".format(original.relpath)
            )
            continue
        if not _absent(original.parent_fd, original.name):
            errors.append(
                "original name {} is occupied; backup preserved".format(
                    original.relpath
                )
            )
            continue
        try:
            os.rename(
                original.backup_name,
                original.name,
                src_dir_fd=transaction.original_fd,
                dst_dir_fd=original.parent_fd,
            )
            restored = _state_at(original.parent_fd, original.name)
            if restored != original.expected:
                errors.append(
                    "original {} was not restored exactly".format(
                        original.relpath
                    )
                )
        except Exception as error:
            errors.append(
                "original {} restore failed: {}".format(
                    original.relpath, error
                )
            )
    try:
        if (
            _safe_root_digest(transaction.root_fd)
            != transaction.raw["source_state_hash"]
        ):
            errors.append("visible project source state was not restored")
    except Exception as error:
        errors.append("restored project verification failed: {}".format(error))
    try:
        _verify_ambient(transaction)
    except Exception as error:
        errors.append(str(error))
    return errors


def _cleanup_empty_backup(transaction: Transaction) -> bool:
    """Remove only the still-owned empty backup scaffold."""
    try:
        if transaction.backup_fd < 0 or transaction.run_fd < 0:
            return False
        if _identity_at(transaction.run_fd, "backup") != transaction.backup_identity:
            return False
        if (
            _identity_at(transaction.backup_fd, "original")
            != transaction.original_identity
        ):
            return False
        if os.listdir(transaction.original_fd):
            return False
        if set(os.listdir(transaction.backup_fd)) != {
            "original", _BACKUP_OWNER,
        }:
            return False
        if (
            _state_at(transaction.backup_fd, _BACKUP_OWNER)
            != transaction.owner_state
        ):
            return False
        os.unlink(_BACKUP_OWNER, dir_fd=transaction.backup_fd)
        os.rmdir("original", dir_fd=transaction.backup_fd)
        os.rmdir("backup", dir_fd=transaction.run_fd)
        transaction.backup_exists = False
        return True
    except (OSError, ApplyError):
        return False


def _restore_payload(transaction: Transaction) -> str:
    operations = []
    for original in transaction.originals:
        operations.append({
            "path": original.relpath,
            "backup": str(
                transaction.run
                / "backup"
                / "original"
                / original.backup_name
            ),
            "sha256": original.expected.digest,
            "identity": list(original.expected.identity),
        })
    return json.dumps({
        "backup_root": str(transaction.run / "backup"),
        "operations": operations,
        "deleted_paths": transaction.manifest.deleted_paths,
        "renamed_paths": transaction.manifest.renamed_paths,
    }, indent=2, sort_keys=True) + "\n"


def apply_preview(
    project_root: Path, run_dir: Path, approval_token: str
) -> ApplyResult:
    """Apply exactly the token-bound preview, preserving originals externally."""
    root = project_root.resolve()
    run = run_dir.resolve()
    if (
        not root.is_dir()
        or not run.is_dir()
        or _contains(root, run)
        or _contains(run, root)
    ):
        _fail("project and run directories must be disjoint real directories")
    _fd_support()
    root_probe = _open_directory(root)
    run_probe = _open_directory(run)
    try:
        if not _same_filesystem(root_probe, run_probe):
            _fail(
                "project and run directories must be on the same filesystem "
                "for safe apply"
            )
    finally:
        os.close(run_probe)
        os.close(root_probe)

    manifest, raw = _load_manifest(run)
    preview = _verify_approval(
        root, run, manifest, raw, approval_token
    )
    for source, destination in manifest.renamed_paths.items():
        source_path = root / _safe_relpath(source)
        destination_path = root / _safe_relpath(destination)
        preview_path = preview / _safe_relpath(destination)
        if (
            not source_path.exists()
            or source_path.is_symlink()
            or destination_path.exists()
            or destination_path.is_symlink()
            or not preview_path.exists()
            or not destination_path.parent.is_dir()
        ):
            _fail(
                "rename preflight failed: {} -> {}".format(
                    source, destination
                )
            )
    for relpath in manifest.changed_paths:
        if _inside_renamed_preview(manifest, relpath):
            continue
        source = root / _safe_relpath(relpath)
        final = preview / _safe_relpath(relpath)
        if (
            not source.is_file()
            or source.is_symlink()
            or not final.is_file()
            or b"\x00" in source.read_bytes()
            or b"\x00" in final.read_bytes()
        ):
            _fail("text replacement preflight failed: {}".format(relpath))
    reverse = _reverse_diff(root, preview, manifest)

    transaction = _prepare_transaction(
        root, run, preview, manifest, raw
    )
    try:
        try:
            _fd_transaction(transaction)
            _verify_success(transaction)
            _write_artifact_atomic(
                transaction,
                "restore.json",
                _restore_payload(transaction),
            )
            _write_artifact_atomic(
                transaction, "reverse.diff", reverse
            )
            _verify_success(transaction)
            for artifact in transaction.artifacts:
                if (
                    _state_at(transaction.run_fd, artifact.name)
                    != artifact.expected
                ):
                    _fail(
                        "successful apply artifact changed: "
                        "{}".format(artifact.name)
                    )
        except Exception as error:
            mutated = any(
                item.moved is not None for item in transaction.originals
            ) or any(
                item.created is not None for item in transaction.outputs
            ) or bool(transaction.artifacts)
            if not mutated:
                if not _cleanup_empty_backup(transaction):
                    raise ApplyError(
                        "apply refused before mutation but empty backup cleanup "
                        "failed: {}".format(error)
                    ) from error
                if isinstance(error, ApplyError):
                    raise
                raise ApplyError(
                    "apply refused before mutation: {}".format(error)
                ) from error
            rollback_errors = _rollback(transaction)
            if rollback_errors:
                raise ApplyError(
                    "apply failed and rollback failed: {}; original error: "
                    "{}".format("; ".join(rollback_errors), error)
                ) from error
            if not _cleanup_empty_backup(transaction):
                raise ApplyError(
                    "apply failed and rollback failed: restored originals but "
                    "could not remove empty backup; original error: "
                    "{}".format(error)
                ) from error
            raise ApplyError(
                "apply failed; changes rolled back: {}".format(error)
            ) from error
    finally:
        transaction.close()

    return ApplyResult(
        manifest.run_id,
        manifest.changed_paths,
        manifest.deleted_paths,
        manifest.renamed_paths,
        str(run / "backup"),
        str(run / "restore.json"),
    )
