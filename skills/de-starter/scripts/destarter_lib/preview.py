"""Create reviewable, project-external de-starter previews without touching source."""

import difflib
import json
import os
import re
import shutil
import stat
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from .files import IGNORED_DIRS, is_secret_name, read_text, safe_write_text, sha256_file
from .models import AuditResult, DecisionSet, PreviewManifest
from .report import redact_evidence
from .decisions import PLACEHOLDER_PROFILE


_OWNER_FILE = ".destarter-preview-owner.json"
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


def _state_hash(root: Path, excluded_names: Iterable[str] = ()) -> str:
    """Bind every safe file, directory (including empty ones), and permission mode."""
    excluded = set(excluded_names)
    entries = []
    for directory, dirs, files in os.walk(str(root), followlinks=False):
        current = Path(directory)
        dirs[:] = [name for name in dirs if not _is_ignored_name(name) and not _is_secret_name(name)]
        rel_dir = current.relative_to(root).as_posix()
        entries.append({"kind": "dir", "path": rel_dir, "mode": stat.S_IMODE(current.stat().st_mode)})
        for name in sorted(files):
            if name in excluded or _is_ignored_name(name) or _is_secret_name(name):
                continue
            path = current / name
            if path.is_symlink() or not path.is_file():
                continue
            entries.append({"kind": "file", "path": path.relative_to(root).as_posix(),
                            "mode": stat.S_IMODE(path.stat().st_mode), "sha256": sha256_file(path)})
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
    operation_roots = deleted + list(renames) + list(renames.values())
    for relpath in operation_roots:
        _safe_relpath(relpath)
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
    actions_by_path: Dict[str, List[Tuple[object, object]]] = {}
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
        safe_write_text(path, "".join(lines))
        changed.add(relpath)

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
    safe_write_text(run / "preview.diff", _redact_report_text("".join(diff_lines), decisions))

    binary_operations = _operation_records(root, deleted, "delete", renames)
    binary_operations.extend(_operation_records(root, renames, "rename", renames))
    for relpath in sorted(changed):
        binary_operations.append({"operation": "replace", "path": relpath, "destination": _preview_relpath(relpath, renames), "is_text": True})
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
        "delete_paths": deleted, "rename_paths": renames,
    })
    artifact_hashes = {
        name: sha256_file(run / name)
        for name in ("preview.diff", "binary-changes.json", "placeholders.json")
    }
    core = {
        "run_id": sha256(str(run).encode("utf-8")).hexdigest()[:16],
        "project_root": str(root), "preview_root": str(preview_root.resolve()),
        "source_hashes": dict(sorted(source_hashes.items())),
        "preview_hashes": dict(sorted(preview_hashes.items())),
        "delete_tree_hashes": delete_tree_hashes, "rename_tree_hashes": rename_tree_hashes,
        "changed_paths": sorted(preview_hashes), "deleted_paths": deleted, "renamed_paths": renames,
    }
    profile_hash = _token({"brand_profile": decisions.brand_profile})
    brand_result_hash = _token({
        "brand_mode": decisions.brand_mode,
        "profile_hash": profile_hash,
        "preview_hashes": core["preview_hashes"],
        "delete_tree_hashes": core["delete_tree_hashes"],
        "rename_tree_hashes": core["rename_tree_hashes"],
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
        "- Renamed paths: `{}`".format(len(renames)), "- Approval token: `{}`".format(manifest.approval_token), "",
        "Review `audit.md`, `preview.diff`, `binary-changes.json`, and `placeholders.json` before approval.", "",
    ]))
    return manifest
