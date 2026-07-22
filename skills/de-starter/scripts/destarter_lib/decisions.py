"""Strict validation for the user-authored de-starter decision file."""

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .files import IGNORED_DIRS, is_secret_name
from .models import AuditResult, DecisionAction, DecisionSet, Finding, RiskLevel, TextEdit
from .scanner import path_is_p2


REAL_BRAND_FIELDS = {
    "product_name", "short_name", "url", "domain", "support_email",
    "repository_url", "owner",
}
PLACEHOLDER_PROFILE = {
    "product_name": "Your Product",
    "short_name": "Your Product",
    "url": "https://example.com",
    "domain": "example.com",
    "support_email": "support@example.com",
    "repository_url": "https://github.com/your-org/your-product",
    "owner": "Your Company",
}
_TOP_LEVEL_KEYS = {
    "brand_mode", "brand_profile", "actions", "delete_paths", "rename_paths", "text_edits",
}
_ACTION_KEYS = {"finding_id", "action", "replacement", "migration_plan", "rollback_plan"}
_TEXT_EDIT_KEYS = {
    "path", "expected_sha256", "start_line", "end_line", "replacement", "reason",
    "migration_plan", "rollback_plan",
}
_VALID_ACTIONS = {"keep", "replace"}
_PROTECTED_FILE_STEMS = {"license", "copying", "notice"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DecisionError(ValueError):
    """Raised when a decision file is not safe to apply."""


class _DuplicateKeyError(ValueError):
    pass


def _error_for_unknown_keys(payload: Mapping[str, object], allowed: Set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise DecisionError("unknown {} keys: {}".format(label, ", ".join(unknown)))


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DecisionError("{} must be a positive integer".format(label))
    return value


def _validate_profile(mode: str, raw_profile: object) -> Dict[str, str]:
    if not isinstance(raw_profile, dict):
        raise DecisionError("brand_profile must be an object")
    profile = dict(raw_profile)
    if mode == "real":
        missing = sorted(
            field for field in REAL_BRAND_FIELDS if not _non_empty_string(profile.get(field))
        )
        if missing:
            raise DecisionError("missing brand fields: " + ", ".join(missing))
        if any(not isinstance(key, str) or not _non_empty_string(value) for key, value in profile.items()):
            raise DecisionError("brand_profile values must be non-empty strings")
        return profile
    if any(not isinstance(key, str) or not _non_empty_string(value) for key, value in profile.items()):
        raise DecisionError("brand_profile values must be non-empty strings")
    return {**PLACEHOLDER_PROFILE, **profile}


def _project_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionError("{} must stay inside the project".format(label))
    if "\\" in value or value.startswith("/") or (len(value) >= 2 and value[1] == ":"):
        raise DecisionError("{} must stay inside the project".format(label))
    parts = [part for part in value.split("/") if part]
    if not parts or any(
        part in {".", ".."} or part.endswith(".") or part[-1].isspace()
        for part in parts
    ):
        raise DecisionError("{} must stay inside the project".format(label))
    return "/".join(parts)


def _contains(parent: str, child: str) -> bool:
    return child == parent or child.startswith(parent.rstrip("/") + "/")


def _findings_under(audit: AuditResult, path: str) -> Iterable[Finding]:
    return (item for item in audit.findings if _contains(path, item.relpath))


def _path_finding_authorizes_root(audit: AuditResult, path: str) -> bool:
    for item in _findings_under(audit, path):
        if item.line != 0 or item.category != "file-or-directory-name":
            continue
        start = item.column - 1
        end = start + len(item.matched)
        if (
            start >= 0
            and end <= len(path)
            and path[start:end].casefold() == item.matched.casefold()
        ):
            return True
    return False


def _validate_protected_paths(audit: AuditResult, paths: Iterable[str], operation: str) -> None:
    for path in paths:
        protected = sorted(
            item.finding_id
            for item in _findings_under(audit, path)
            if item.risk in {RiskLevel.P0, RiskLevel.P1}
        )
        if protected:
            raise DecisionError(
                "{} path contains protected finding: {}".format(operation, ", ".join(protected))
            )


def _is_protected_path(path: str) -> bool:
    for part in path.split("/"):
        lowered = part.casefold()
        stem = lowered.split(".", 1)[0]
        if (
            lowered in IGNORED_DIRS
            or stem in _PROTECTED_FILE_STEMS
            or is_secret_name(part)
        ):
            return True
    return False


def _validate_invariant_paths(paths: Iterable[str], operation: str) -> None:
    for path in paths:
        if _is_protected_path(path):
            raise DecisionError(
                "{} path contains protected finding: invariant path {}".format(operation, path)
            )


def _validate_audited_paths(audit: AuditResult, paths: Iterable[str], operation: str) -> None:
    for path in paths:
        files = [item for item in audit.files if _contains(path, item.relpath)]
        if not files:
            scope = "audited P2 scope" if operation == "delete" else "audited scope"
            raise DecisionError(
                "{}_paths must correspond to an {}: {}".format(operation, scope, path)
            )
        if operation == "delete":
            exact_authorized = lambda relpath: any(
                item.relpath == relpath and item.risk is RiskLevel.P2
                for item in audit.findings
            )
            message = "delete_paths must correspond to an audited P2 scope"
        else:
            exact_authorized = lambda relpath: any(
                item.relpath == relpath
                and (item.risk is RiskLevel.P2 or item.category == "file-or-directory-name")
                for item in audit.findings
            )
            message = "rename_paths must correspond to an audited P2 or path finding scope"
        if not all(exact_authorized(item.relpath) for item in files):
            raise DecisionError(message + ": " + path)
        authorized_roots = set()
        for item in files:
            if exact_authorized(item.relpath):
                authorized_roots.add(item.relpath)
                parent = item.relpath.rpartition("/")[0]
                if parent:
                    authorized_roots.add(parent)
        if operation == "rename" and (
            path_is_p2(path) or _path_finding_authorizes_root(audit, path)
        ):
            authorized_roots.add(path)
        if path not in authorized_roots:
            raise DecisionError(message + ": " + path)


def _reject_duplicate_keys(pairs: List[object]) -> Dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def _load_payload(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError, _DuplicateKeyError) as error:
        raise DecisionError("invalid decisions JSON: {}".format(error)) from error
    if not isinstance(payload, dict):
        raise DecisionError("decisions JSON must be an object")
    return payload


def _validate_actions(raw_actions: object, findings: Mapping[str, Finding]) -> List[DecisionAction]:
    if not isinstance(raw_actions, list):
        raise DecisionError("actions must be a list")
    actions = []
    seen = set()
    for raw in raw_actions:
        if not isinstance(raw, dict):
            raise DecisionError("actions must contain objects")
        _error_for_unknown_keys(raw, _ACTION_KEYS, "action")
        finding_id = raw.get("finding_id")
        action = raw.get("action")
        if not isinstance(finding_id, str) or not finding_id:
            raise DecisionError("action finding_id must be a non-empty string")
        if finding_id in seen:
            raise DecisionError("duplicate action for finding: {}".format(finding_id))
        seen.add(finding_id)
        if finding_id not in findings:
            raise DecisionError("unknown finding: {}".format(finding_id))
        if not isinstance(action, str) or action not in _VALID_ACTIONS:
            raise DecisionError("action must be keep or replace")
        finding = findings[finding_id]
        if finding.line == 0 and action == "replace":
            raise DecisionError(
                "path finding requires rename_paths or delete_paths: {}".format(finding_id)
            )
        if finding.risk is RiskLevel.P0 and action != "keep":
            raise DecisionError("P0 finding cannot be modified: {}".format(finding_id))
        replacement = raw.get("replacement")
        if action == "replace" and not _non_empty_string(replacement):
            raise DecisionError("replace action requires a non-empty replacement")
        if action == "keep" and replacement is not None:
            raise DecisionError("keep action cannot include a replacement")
        migration = raw.get("migration_plan")
        rollback = raw.get("rollback_plan")
        if finding.risk is RiskLevel.P1 and action != "keep":
            if not _non_empty_string(migration) or not _non_empty_string(rollback):
                raise DecisionError(
                    "P1 finding requires migration and rollback plans: {}".format(finding_id)
                )
        if migration is not None and not _non_empty_string(migration):
            raise DecisionError("migration_plan must be a non-empty string")
        if rollback is not None and not _non_empty_string(rollback):
            raise DecisionError("rollback_plan must be a non-empty string")
        actions.append(DecisionAction(
            finding_id=finding_id,
            action=action,
            replacement=replacement,
            migration_plan=migration,
            rollback_plan=rollback,
        ))
    return actions


def _intersects(start: int, end: int, lines: Set[int]) -> bool:
    return any(start <= line <= end for line in lines)


def _current_text(project_root: Path, relpath: str) -> Tuple[str, str]:
    if project_root.is_symlink():
        raise DecisionError("text edit path cannot be a symlink: {}".format(relpath))
    current = project_root
    for part in relpath.split("/"):
        current = current / part
        if current.is_symlink():
            raise DecisionError("text edit path cannot be a symlink: {}".format(relpath))
    try:
        data = current.read_bytes()
    except OSError as error:
        raise DecisionError("text edit file is unavailable: {}".format(relpath)) from error
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DecisionError("text edit file must be UTF-8 text: {}".format(relpath)) from error
    return text, sha256(data).hexdigest()


def _validate_text_edits(
    raw_edits: object,
    audit: AuditResult,
    actions: List[DecisionAction],
    project_root: Optional[Path],
) -> List[TextEdit]:
    if not isinstance(raw_edits, list):
        raise DecisionError("text_edits must be a list")
    if raw_edits and project_root is None:
        raise DecisionError("text edits require project_root")

    audited_files = {item.relpath: item for item in audit.files}
    if len(audited_files) != len(audit.files):
        raise DecisionError("audit contains duplicate file records")
    findings = {item.finding_id: item for item in audit.findings}
    p0_lines: Dict[str, Set[int]] = {}
    p1_lines: Dict[str, Set[int]] = {}
    for finding in audit.findings:
        if finding.risk is RiskLevel.P0 and finding.line > 0:
            p0_lines.setdefault(finding.relpath, set()).add(finding.line)
        if finding.risk is RiskLevel.P1 and finding.line > 0:
            p1_lines.setdefault(finding.relpath, set()).add(finding.line)
    action_lines: Dict[str, Set[int]] = {}
    for action in actions:
        finding = findings[action.finding_id]
        if finding.line > 0:
            action_lines.setdefault(finding.relpath, set()).add(finding.line)

    edits = []
    for raw in raw_edits:
        if not isinstance(raw, dict):
            raise DecisionError("text_edits must contain objects")
        _error_for_unknown_keys(raw, _TEXT_EDIT_KEYS, "text edit")
        edit_path = _project_path(raw.get("path"), "text edit path")
        if _is_protected_path(edit_path):
            raise DecisionError("text edit path contains protected finding: invariant path {}".format(edit_path))
        record = audited_files.get(edit_path)
        if record is None:
            raise DecisionError("text edit path must be an audited text file: {}".format(edit_path))
        if not record.is_text:
            raise DecisionError("text edit path must be an audited text file: {}".format(edit_path))
        expected_hash = raw.get("expected_sha256")
        if not isinstance(expected_hash, str) or not _SHA256_RE.fullmatch(expected_hash):
            raise DecisionError("text edit hash must be a lowercase SHA-256")
        if expected_hash != record.sha256:
            raise DecisionError("text edit hash does not match audit: {}".format(edit_path))
        start_line = _positive_int(raw.get("start_line"), "text edit start_line")
        end_line = _positive_int(raw.get("end_line"), "text edit end_line")
        if end_line < start_line:
            raise DecisionError("text edit end_line must not precede start_line")
        replacement = raw.get("replacement")
        if not isinstance(replacement, str):
            raise DecisionError("text edit replacement must be a string")
        reason = raw.get("reason")
        if not _non_empty_string(reason):
            raise DecisionError("text edit reason must be a non-empty string")
        migration = raw.get("migration_plan")
        rollback = raw.get("rollback_plan")
        p1_migration_protected = _intersects(
            start_line, end_line, p1_lines.get(edit_path, set())
        )
        if _intersects(start_line, end_line, p0_lines.get(edit_path, set())):
            raise DecisionError("text edit overlaps protected P0 line: {}".format(edit_path))
        if p1_migration_protected and (
            not _non_empty_string(migration) or not _non_empty_string(rollback)
        ):
            raise DecisionError(
                "P1 text edit requires migration and rollback plans: {}".format(edit_path)
            )
        if migration is not None and not _non_empty_string(migration):
            raise DecisionError("migration_plan must be a non-empty string")
        if rollback is not None and not _non_empty_string(rollback):
            raise DecisionError("rollback_plan must be a non-empty string")
        if _intersects(start_line, end_line, action_lines.get(edit_path, set())):
            raise DecisionError("text edit overlaps finding action: {}".format(edit_path))
        text, current_hash = _current_text(project_root, edit_path)
        if current_hash != expected_hash:
            raise DecisionError("text edit hash does not match current file: {}".format(edit_path))
        line_count = len(text.splitlines())
        if end_line > line_count:
            raise DecisionError("text edit line range is outside file: {}".format(edit_path))
        edits.append(TextEdit(
            path=edit_path,
            expected_sha256=expected_hash,
            start_line=start_line,
            end_line=end_line,
            replacement=replacement,
            reason=reason,
            migration_plan=migration,
            rollback_plan=rollback,
            p1_migration_protected=p1_migration_protected,
        ))

    ordered = sorted(edits, key=lambda item: (item.path, item.start_line, item.end_line))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.path == current.path and current.start_line <= previous.end_line:
            raise DecisionError("text edits overlap: {}".format(current.path))
    return ordered


def load_decisions(
    path: Path,
    audit: AuditResult,
    project_root: Optional[Path] = None,
) -> DecisionSet:
    """Load a decision file only when every requested change is explicit and safe."""
    payload = _load_payload(path)
    _error_for_unknown_keys(payload, _TOP_LEVEL_KEYS, "decision")
    mode = payload.get("brand_mode")
    if not isinstance(mode, str) or mode not in {"real", "placeholder"}:
        raise DecisionError("brand_mode must be real or placeholder")
    profile = _validate_profile(mode, payload.get("brand_profile", {}))
    findings = {item.finding_id: item for item in audit.findings}
    if len(findings) != len(audit.findings):
        raise DecisionError("audit contains duplicate finding IDs")
    actions = _validate_actions(payload.get("actions", []), findings)

    raw_deletes = payload.get("delete_paths", [])
    if not isinstance(raw_deletes, list):
        raise DecisionError("delete_paths must be a list")
    delete_paths = [_project_path(value, "delete_paths") for value in raw_deletes]
    if len(set(delete_paths)) != len(delete_paths):
        raise DecisionError("delete_paths cannot contain duplicates")
    if any(_contains(first, second) for first in delete_paths for second in delete_paths if first != second):
        raise DecisionError("delete_paths cannot overlap")

    raw_renames = payload.get("rename_paths", {})
    if not isinstance(raw_renames, dict):
        raise DecisionError("rename_paths must be an object")
    rename_paths = {}
    for source, destination in raw_renames.items():
        source_path = _project_path(source, "rename_paths")
        destination_path = _project_path(destination, "rename_paths")
        if source_path == destination_path:
            raise DecisionError("rename_paths source and destination must differ")
        if source_path in rename_paths:
            raise DecisionError("rename_paths cannot contain normalized source duplicates")
        rename_paths[source_path] = destination_path
    destinations = list(rename_paths.values())
    if len(set(destinations)) != len(destinations):
        raise DecisionError("rename_paths cannot reuse destinations")
    for source, destination in rename_paths.items():
        if any(_contains(deleted, source) or _contains(source, deleted) for deleted in delete_paths):
            raise DecisionError("rename_paths cannot overlap delete_paths")
        if any(
            _contains(deleted, destination) or _contains(destination, deleted)
            for deleted in delete_paths
        ):
            raise DecisionError("rename_paths destinations cannot overlap delete_paths")
        if any(
            _contains(other_source, destination) or _contains(destination, other_source)
            for other_source in rename_paths
        ):
            raise DecisionError("rename_paths destinations cannot overlap sources")
        if any(
            other != source and (_contains(other, source) or _contains(source, other))
            for other in rename_paths
        ):
            raise DecisionError("rename_paths sources cannot overlap")
        if any(
            other != destination and (_contains(other, destination) or _contains(destination, other))
            for other in destinations
        ):
            raise DecisionError("rename_paths destinations cannot overlap")

    _validate_invariant_paths(delete_paths, "delete")
    _validate_invariant_paths(rename_paths, "rename")
    _validate_invariant_paths(destinations, "rename destination")
    _validate_audited_paths(audit, delete_paths, "delete")
    _validate_audited_paths(audit, rename_paths, "rename")
    _validate_protected_paths(audit, delete_paths, "delete")
    _validate_protected_paths(audit, rename_paths, "rename")
    text_edits = _validate_text_edits(
        payload.get("text_edits", []), audit, actions, project_root
    )
    return DecisionSet(mode, profile, actions, delete_paths, rename_paths, text_edits)
