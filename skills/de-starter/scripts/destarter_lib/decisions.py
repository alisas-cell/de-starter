"""Strict validation for the user-authored de-starter decision file."""

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Set

from .files import IGNORED_DIRS
from .models import AuditResult, DecisionAction, DecisionSet, Finding, RiskLevel


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
_TOP_LEVEL_KEYS = {"brand_mode", "brand_profile", "actions", "delete_paths", "rename_paths"}
_ACTION_KEYS = {"finding_id", "action", "replacement", "migration_plan", "rollback_plan"}
_VALID_ACTIONS = {"keep", "replace"}
_PROTECTED_FILE_STEMS = {"license", "copying", "notice"}


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
        if lowered in IGNORED_DIRS or stem in _PROTECTED_FILE_STEMS:
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


def load_decisions(path: Path, audit: AuditResult) -> DecisionSet:
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
    return DecisionSet(mode, profile, actions, delete_paths, rename_paths)
