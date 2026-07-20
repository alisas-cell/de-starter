import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .models import AuditResult
from .scanner import SECRET_ASSIGNMENT_RE


RISK_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def redact_evidence(value: str) -> str:
    """Replace the complete detected secret assignment before reporting it."""
    return SECRET_ASSIGNMENT_RE.sub(
        lambda match: "{} = [REDACTED]".format(match.group("name")),
        value,
    )


def _ordered_findings(audit: AuditResult):
    return sorted(
        audit.findings,
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
            for item in _ordered_findings(audit)
        ],
        "files": [asdict(item) for item in audit.files],
    }


def write_audit_reports(audit: AuditResult, run_dir: Path) -> None:
    """Write JSON and Markdown audit reports with redacted evidence."""
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = audit_to_dict(audit)
    (run_dir / "audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# De-starter Audit",
        "",
        "- Project kind: `{}`".format(audit.project.kind),
        "- Git present: `{}`".format(str(audit.project.git_present).lower()),
        "- Git dirty: `{}`".format(audit.project.git_dirty),
        "- Findings: `{}`".format(len(audit.findings)),
        "- Confirmed source terms: `{}`".format(", ".join(audit.source_terms)),
        "",
        "## Findings",
        "",
        "| ID | Risk | Category | Location | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in _ordered_findings(audit):
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
    lines.extend(["", "## Validation Plan", ""])
    lines.extend("- `{}`".format(command) for command in audit.project.validation_commands)
    (run_dir / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
