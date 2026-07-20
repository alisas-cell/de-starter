import json
import re
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, List, Set, Tuple

from .files import iter_project_files, read_text
from .models import Candidate

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
URL_RE = re.compile(r"https?://[^\s)>\"]+")
COPYRIGHT_RE = re.compile(r"Copyright\s*(?:\(c\)|©)?\s*\d{4}(?:-\d{4})?\s+(.+)", re.I)
DISPLAY_RE = re.compile(r"\b[A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+){1,2}\b")
IDENTITY_HINTS = {
    "readme", "metadata", "website", "site", "brand", "logo", "footer",
    "header", "email", "message", "seo", "manifest",
}


def discover_candidates(root: Path) -> List[Candidate]:
    evidence: DefaultDict[Tuple[str, str], Set[str]] = defaultdict(set)

    def add(kind: str, value: object, source: str) -> None:
        if isinstance(value, str) and value.strip():
            evidence[(kind, value.strip())].add(source)

    package_path = root / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        add("package", package.get("name"), "package.json")
        author = package.get("author")
        add(
            "owner",
            author if isinstance(author, str) else (author or {}).get("name"),
            "package.json",
        )
        repository = package.get("repository")
        add(
            "repository",
            repository if isinstance(repository, str) else (repository or {}).get("url"),
            "package.json",
        )
        add("url", package.get("homepage"), "package.json")

    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        text = pyproject_path.read_text(encoding="utf-8", errors="ignore")
        project_name = re.search(r'(?m)^name\s*=\s*"([^"]+)"', text)
        if project_name:
            add("package", project_name.group(1), "pyproject.toml")
        for owner in re.findall(r'name\s*=\s*"([^"]+)"', text):
            if not project_name or owner != project_name.group(1):
                add("owner", owner, "pyproject.toml")
        for email in EMAIL_RE.findall(text):
            add("email", email, "pyproject.toml")

    for name in ("README.md", "README", "LICENSE", "NOTICE"):
        path = root / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if name.startswith("README"):
            heading = next(
                (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
                "",
            )
            add("display", heading, name)
        for value in EMAIL_RE.findall(text):
            add("email", value, name)
        for value in URL_RE.findall(text):
            add("url", value.rstrip(".,;"), name)
        for line in text.splitlines():
            match = COPYRIGHT_RE.search(line)
            if match:
                add("owner", match.group(1).strip(), name)

    for record in iter_project_files(root):
        lowered = record.relpath.lower()
        if not record.is_text:
            continue
        if (
            not any(hint in lowered for hint in IDENTITY_HINTS)
            and Path(record.relpath).suffix not in {".html", ".htm"}
        ):
            continue
        text = read_text(root / record.relpath) or ""
        for value in EMAIL_RE.findall(text):
            add("email", value, record.relpath)
        for value in URL_RE.findall(text):
            add("url", value.rstrip(".,;"), record.relpath)
        for value in DISPLAY_RE.findall(text):
            if value.lower() not in {"terms of service", "privacy policy"}:
                add("display", value, record.relpath)

    candidates = [
        Candidate(kind, value, len(sources), sorted(sources))
        for (kind, value), sources in evidence.items()
    ]
    return sorted(candidates, key=lambda item: (-item.score, item.kind, item.value.lower()))
