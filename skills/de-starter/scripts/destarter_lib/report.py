import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .models import AuditResult
from .files import safe_write_text
from .scanner import SECRET_ASSIGNMENT_RE


RISK_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def redact_evidence(value: str) -> str:
    """Replace the complete detected secret assignment before reporting it."""
    return SECRET_ASSIGNMENT_RE.sub(
        lambda match: "{} = [REDACTED]".format(match.group("name")),
        value,
    )


def _ordered_findings(findings):
    return sorted(
        findings,
        key=lambda item: (
            RISK_ORDER[item.risk.value],
            item.relpath,
            item.line,
            item.column,
            item.category,
            item.matched,
            item.finding_id,
        ),
    )


def audit_to_dict(audit: AuditResult) -> Dict[str, object]:
    return {
        "project": asdict(audit.project),
        "source_terms": audit.source_terms,
        "findings": [
            {
                **asdict(item),
                "risk": item.risk.value,
                "evidence": redact_evidence(item.evidence),
            }
            for item in _ordered_findings(audit.findings)
        ],
        "files": [asdict(item) for item in audit.files],
        "directories": [asdict(item) for item in audit.directories],
        "directory_findings": [
            {
                **asdict(item),
                "risk": item.risk.value,
                "evidence": redact_evidence(item.evidence),
            }
            for item in _ordered_findings(audit.directory_findings)
        ],
    }


def write_audit_reports(audit: AuditResult, run_dir: Path) -> None:
    """Write JSON and Markdown audit reports with redacted evidence."""
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = audit_to_dict(audit)
    safe_write_text(run_dir / "audit.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# De-starter Audit",
        "",
        "- Project kind: `{}`".format(audit.project.kind),
        "- Git present: `{}`".format(str(audit.project.git_present).lower()),
        "- Git dirty: `{}`".format(audit.project.git_dirty),
        "- Findings: `{}`".format(len(audit.findings)),
        "- Directory findings: `{}`".format(len(audit.directory_findings)),
        "- Confirmed source terms: `{}`".format(", ".join(audit.source_terms)),
        "",
        "## Findings",
        "",
        "| ID | Risk | Category | Location | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in _ordered_findings(audit.findings):
        evidence = redact_evidence(item.evidence).replace("|", "\\|").replace("`", "'")
        lines.append(
            "| {} | {} | {} | `{}:{}:{}` | {} |".format(
                item.finding_id,
                item.risk.value,
                item.category,
                item.relpath,
                item.line,
                item.column,
                evidence,
            )
        )
    lines.extend(
        [
            "",
            "## Directory residue",
            "",
            "- Directories inventoried: `{}`".format(len(audit.directories)),
            "- Directory findings: `{}`".format(len(audit.directory_findings)),
            "",
            "| ID | Risk | Location | Empty | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    directories = {item.relpath: item for item in audit.directories}
    for item in _ordered_findings(audit.directory_findings):
        evidence = redact_evidence(item.evidence).replace("|", "\\|").replace("`", "'")
        lines.append(
            "| {} | {} | `{}` | {} | {} |".format(
                item.finding_id,
                item.risk.value,
                item.relpath,
                str(directories[item.relpath].is_empty).lower(),
                evidence,
            )
        )
    lines.extend(["", "## Validation Plan", ""])
    lines.extend("- `{}`".format(command) for command in audit.project.validation_commands)
    safe_write_text(run_dir / "audit.md", "\n".join(lines) + "\n")
