import re
from hashlib import sha256
from pathlib import Path
from typing import Sequence, Tuple

from .adapters import detect_project
from .files import iter_project_files, read_text
from .models import AuditResult, Finding, RiskLevel


LEGAL_NAMES = {"license", "license.md", "copying", "notice", "notice.md"}
P1_PATTERNS = (
    re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b"),
    re.compile(r"\b(?:prod|price|plan|sub|cus)_[A-Za-z0-9]+\b"),
    re.compile(r"\b[a-z0-9]+_(?:monthly|yearly|annual|plan)\b", re.I),
    re.compile(r"/api/[A-Za-z0-9_./:-]+"),
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?ix)\b(?P<name>[A-Z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*)[\"']?"
    r"\s*(?:=\s*|:\s*(?:[A-Z_$][A-Z0-9_$<>\[\]| ,.?]*\s*=\s*)?)"
    r"(?P<quote>[\"'])(?P<value>(?:\\.|(?! (?P=quote) ).){8,})(?P=quote)"
)
P2_PARTS = {
    "demo", "demos", "example", "examples", "sample", "samples", "testimonials",
    "fixtures",
}


def _risk(relpath: str, line_text: str) -> Tuple[RiskLevel, str]:
    """Classify a match using the highest applicable risk level."""
    path = Path(relpath)
    if path.name.lower() in LEGAL_NAMES:
        return RiskLevel.P0, "legal-or-copyright"
    if any(pattern.search(line_text) for pattern in P1_PATTERNS):
        return RiskLevel.P1, "possible-persisted-or-public-identifier"
    if any(part.lower() in P2_PARTS for part in path.parts):
        return RiskLevel.P2, "user-decides-sample-content"
    return RiskLevel.P3, "display-or-metadata"


def _finding_id(raw_id: str) -> str:
    return "F-" + sha256(raw_id.encode("utf-8")).hexdigest()[:12]


def _source_terms(source_terms: Sequence[str]) -> Sequence[str]:
    """Canonicalize case variants and make equal-length ordering reproducible."""
    canonical = {}
    for source_term in source_terms:
        term = source_term.strip()
        if not term:
            continue
        key = term.casefold()
        previous = canonical.get(key)
        if previous is None or term < previous:
            canonical[key] = term
    return sorted(canonical.values(), key=lambda value: (-len(value), value.casefold(), value))


def scan_project(project_root: Path, source_terms: Sequence[str]) -> AuditResult:
    """Find confirmed source terms and high-risk literal secrets in a project."""
    terms = _source_terms(source_terms)
    files = list(iter_project_files(project_root))
    findings = []

    for record in files:
        path = Path(record.relpath)
        path_is_p2 = any(part.lower() in P2_PARTS for part in path.parts)

        for term in terms:
            for match in re.finditer(re.escape(term), record.relpath, re.I):
                risk, _ = _risk(record.relpath, "")
                raw_id = "{}:path:{}:{}".format(
                    record.relpath, match.start(), match.group(0)
                )
                findings.append(
                    Finding(
                        finding_id=_finding_id(raw_id),
                        relpath=record.relpath,
                        line=0,
                        column=match.start() + 1,
                        matched=match.group(0),
                        category="file-or-directory-name",
                        risk=risk,
                        evidence="path contains confirmed source term: {}".format(
                            match.group(0)
                        ),
                        sha256=record.sha256,
                    )
                )

        if path_is_p2:
            raw_id = "{}:path-inventory".format(record.relpath)
            findings.append(
                Finding(
                    finding_id=_finding_id(raw_id),
                    relpath=record.relpath,
                    line=0,
                    column=0,
                    matched="<path>",
                    category="user-decides-sample-content",
                    risk=RiskLevel.P2,
                    evidence="binary-or-path inventory: {} bytes".format(record.size),
                    sha256=record.sha256,
                )
            )

        if not record.is_text:
            continue
        text = read_text(project_root / record.relpath)
        if text is None:
            continue

        for line_number, line_text in enumerate(text.splitlines(), start=1):
            for secret_match in SECRET_ASSIGNMENT_RE.finditer(line_text):
                if "example" in secret_match.group("value").lower():
                    continue
                raw_id = "{}:{}:secret:{}:{}".format(
                    record.relpath,
                    line_number,
                    secret_match.start("name"),
                    secret_match.group("name"),
                )
                findings.append(
                    Finding(
                        finding_id=_finding_id(raw_id),
                        relpath=record.relpath,
                        line=line_number,
                        column=secret_match.start("name") + 1,
                        matched=secret_match.group("name"),
                        category="possible-secret",
                        risk=RiskLevel.P0,
                        evidence=line_text.strip()[:240],
                        sha256=record.sha256,
                    )
                )

            for term in terms:
                for match in re.finditer(re.escape(term), line_text, re.I):
                    risk, category = _risk(record.relpath, line_text)
                    raw_id = "{}:{}:{}:{}".format(
                        record.relpath,
                        line_number,
                        match.start(),
                        match.group(0),
                    )
                    findings.append(
                        Finding(
                            finding_id=_finding_id(raw_id),
                            relpath=record.relpath,
                            line=line_number,
                            column=match.start() + 1,
                            matched=match.group(0),
                            category=category,
                            risk=risk,
                            evidence=line_text.strip()[:240],
                            sha256=record.sha256,
                        )
                    )

    return AuditResult(detect_project(project_root), list(terms), findings, files)
