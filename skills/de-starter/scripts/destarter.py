#!/usr/bin/env python3
"""Fail-closed command line entry point for the de-starter lifecycle."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from destarter_lib.adapters import detect_project
from destarter_lib.apply import ApplyError, apply_preview
from destarter_lib.candidates import discover_candidates
from destarter_lib.decisions import DecisionError, load_decisions
from destarter_lib.files import iter_project_files, safe_write_text
from destarter_lib.models import (
    AuditResult,
    DirectoryRecord,
    FileRecord,
    Finding,
    ProjectFacts,
    RiskLevel,
)
from destarter_lib.preview import create_preview
from destarter_lib.report import audit_to_dict, redact_evidence, write_audit_reports
from destarter_lib.scanner import _source_terms as canonical_source_terms, scan_project


class CliError(ValueError):
    """An expected input or lifecycle validation error."""


def _json(path: Path, label: str) -> object:
    def duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CliError("invalid {}: duplicate key".format(label))
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=duplicates)
    except CliError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise CliError("invalid {}".format(label)) from error


def _real_directory(path: Path, label: str, must_exist: bool = True) -> Path:
    if must_exist and (not path.exists() or path.is_symlink() or not path.is_dir()):
        raise CliError("{} must be an existing real directory".format(label))
    return path.resolve()


def _validate_locations(project: Path, run_dir: Path) -> tuple:
    root = _real_directory(project, "project")
    raw_run = run_dir.absolute()
    # System temporary paths commonly include an implementation symlink (for
    # example /var -> /private/var on macOS). Reject the requested run target,
    # while resolving its parents before containment checks.
    if run_dir.is_symlink() or (run_dir.exists() and not run_dir.is_dir()):
        raise CliError("run directory must be absent or a real directory")
    run = raw_run.resolve()
    if run == root or _contains(root, run) or _contains(run, root):
        raise CliError("run directory must be outside and disjoint from project")
    return root, run


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _source_terms(path: Path) -> list:
    payload = _json(path, "source config")
    if not isinstance(payload, dict) or set(payload) != {"source_terms"}:
        raise CliError("invalid source config")
    terms = payload["source_terms"]
    if not isinstance(terms, list) or not terms or any(not isinstance(value, str) or not value.strip() for value in terms):
        raise CliError("source_terms must be a nonempty list of nonempty strings")
    canonical = list(_source_terms_runtime(terms))
    if terms != canonical:
        raise CliError("source_terms must be deterministic and canonical")
    return canonical


def _source_terms_runtime(terms: Sequence[str]) -> Sequence[str]:
    return canonical_source_terms(terms)


def _relpath(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CliError("invalid audit {}".format(label))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CliError("invalid audit {}".format(label))
    return path.as_posix()


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise CliError("invalid audit {}".format(label))
    return value


def _audit_dict(value: object, label: str, keys: set) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CliError("invalid audit {}".format(label))
    return value


def _load_finding(value: object, label: str) -> Finding:
    item = _audit_dict(value, label, {"finding_id", "relpath", "line", "column", "matched", "category", "risk", "evidence", "sha256"})
    if (any(not isinstance(item[name], str) or not item[name] for name in ("finding_id", "matched", "category", "evidence"))
            or any(type(item[name]) is not int or item[name] < 0 for name in ("line", "column"))):
        raise CliError("invalid audit {}".format(label))
    try:
        risk = RiskLevel(item["risk"])
    except (ValueError, TypeError) as error:
        raise CliError("invalid audit risk") from error
    if redact_evidence(item["evidence"]) != item["evidence"]:
        raise CliError("invalid audit secret evidence")
    return Finding(
        item["finding_id"],
        _relpath(item["relpath"], "finding path"),
        item["line"],
        item["column"],
        item["matched"],
        item["category"],
        risk,
        item["evidence"],
        _sha(item["sha256"], "finding hash"),
    )


def _load_audit(path: Path) -> AuditResult:
    payload = _audit_dict(_json(path, "audit"), "schema", {
        "project", "source_terms", "findings", "files", "directories",
        "directory_findings",
    })
    source_terms = payload["source_terms"]
    if not isinstance(source_terms, list) or not source_terms or any(not isinstance(item, str) or not item.strip() for item in source_terms):
        raise CliError("invalid audit source_terms")
    if source_terms != list(_source_terms_runtime(source_terms)):
        raise CliError("invalid audit source_terms")
    project_raw = _audit_dict(payload["project"], "project", {"kind", "package_manager", "validation_commands", "git_present", "git_dirty"})
    if (not isinstance(project_raw["kind"], str) or not isinstance(project_raw["validation_commands"], list)
            or any(not isinstance(item, str) for item in project_raw["validation_commands"])
            or (project_raw["package_manager"] is not None and not isinstance(project_raw["package_manager"], str))
            or type(project_raw["git_present"]) is not bool or (project_raw["git_dirty"] is not None and type(project_raw["git_dirty"]) is not bool)):
        raise CliError("invalid audit project")
    files = []
    if not isinstance(payload["files"], list):
        raise CliError("invalid audit files")
    for value in payload["files"]:
        item = _audit_dict(value, "file", {"relpath", "size", "sha256", "is_text"})
        if type(item["size"]) is not int or item["size"] < 0 or type(item["is_text"]) is not bool:
            raise CliError("invalid audit file")
        files.append(FileRecord(_relpath(item["relpath"], "file path"), item["size"], _sha(item["sha256"], "file hash"), item["is_text"]))
    if len({item.relpath for item in files}) != len(files):
        raise CliError("invalid audit duplicate file")
    if not isinstance(payload["findings"], list):
        raise CliError("invalid audit findings")
    findings = [_load_finding(value, "finding") for value in payload["findings"]]
    if len({item.finding_id for item in findings}) != len(findings):
        raise CliError("invalid audit duplicate finding")
    directories = []
    if not isinstance(payload["directories"], list):
        raise CliError("invalid audit directories")
    for value in payload["directories"]:
        item = _audit_dict(value, "directory", {"relpath", "mode", "state_sha256", "is_empty"})
        if (type(item["mode"]) is not int or item["mode"] < 0 or item["mode"] > 0o7777
                or type(item["is_empty"]) is not bool):
            raise CliError("invalid audit directory")
        directories.append(DirectoryRecord(
            _relpath(item["relpath"], "directory path"),
            item["mode"],
            _sha(item["state_sha256"], "directory state hash"),
            item["is_empty"],
        ))
    if len({item.relpath for item in directories}) != len(directories):
        raise CliError("invalid audit duplicate directory")
    if not isinstance(payload["directory_findings"], list):
        raise CliError("invalid audit directory findings")
    directory_findings = [
        _load_finding(value, "directory finding")
        for value in payload["directory_findings"]
    ]
    if len({item.finding_id for item in directory_findings}) != len(directory_findings):
        raise CliError("invalid audit duplicate directory finding")
    directories_by_path = {item.relpath: item for item in directories}
    for finding in directory_findings:
        directory = directories_by_path.get(finding.relpath)
        if (finding.line != 0 or finding.category != "directory-name"
                or directory is None or finding.sha256 != directory.state_sha256):
            raise CliError("invalid audit directory finding")
    return AuditResult(
        ProjectFacts(**project_raw), list(source_terms), findings, files,
        directories, directory_findings,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="destarter")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("discover", "audit", "preview", "apply", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--project", required=True, type=Path)
        command.add_argument("--run-dir", required=True, type=Path)
    sub.choices["audit"].add_argument("--source-config", required=True, type=Path)
    sub.choices["verify"].add_argument("--source-config", required=True, type=Path)
    sub.choices["preview"].add_argument("--decisions", required=True, type=Path)
    sub.choices["apply"].add_argument("--approval-token", required=True)
    return parser


def main(argv: Sequence[str] = ()) -> int:
    args = build_parser().parse_args(list(argv) or None)
    root, run = _validate_locations(args.project, args.run_dir)
    if args.command == "discover":
        _write(run / "discovery.json", {"project": asdict(detect_project(root)), "candidates": [asdict(item) for item in discover_candidates(root)], "files": [asdict(item) for item in iter_project_files(root)]})
        print(run / "discovery.json")
    elif args.command in {"audit", "verify"}:
        audit = scan_project(root, _source_terms(args.source_config))
        target = run if args.command == "audit" else run / "verification"
        write_audit_reports(audit, target)
        if args.command == "verify":
            print("remaining findings: {}".format(len(audit.findings)))
        print(target / "audit.md")
        if args.command == "verify" and audit.findings:
            return 3
    elif args.command == "preview":
        audit = _load_audit(run / "audit.json")
        if audit_to_dict(audit) != audit_to_dict(scan_project(root, audit.source_terms)):
            raise CliError("audit does not match current scan")
        decisions = load_decisions(args.decisions, audit, root)
        manifest = create_preview(root, run, audit, decisions)
        print(run / "preview.diff")
        print(manifest.approval_token)
    else:
        result = apply_preview(root, run, args.approval_token)
        _write(run / "apply-result.json", asdict(result))
        print(run / "apply-result.json")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CliError as error:
        print("destarter: {}".format(str(error) or "operation failed"), file=sys.stderr)
        raise SystemExit(1)
    except DecisionError:
        print("destarter: invalid decisions", file=sys.stderr)
        raise SystemExit(1)
    except ApplyError:
        print("destarter: approval failed", file=sys.stderr)
        raise SystemExit(1)
    except OSError:
        print("destarter: artifact write failed", file=sys.stderr)
        raise SystemExit(1)
    except ValueError:
        print("destarter: preview failed", file=sys.stderr)
        raise SystemExit(1)
