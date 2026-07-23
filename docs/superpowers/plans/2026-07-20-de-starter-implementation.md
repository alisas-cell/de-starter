# De-starter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a reusable Agent Skill with a deterministic Python scanner that audits starter-template residue, previews changes outside the real workspace, requires explicit approval, applies only approved changes, and verifies the result.

**Architecture:** Keep the installable Skill isolated under `skills/de-starter/`; place public documentation, test fixtures, evaluation evidence, and CI at repository root. A Python 3 standard-library CLI owns discovery, audit, preview, hash validation, backup, application, and verification, while `SKILL.md` owns semantic judgment and two user approval gates.

**Tech Stack:** Agent Skills open standard, Python 3.9+ standard library, `unittest`, Markdown/JSON reports, Git, GitHub Actions.

## Global Constraints

- The current private Starter is an acceptance target, never a public fixture.
- Do not hard-code its source identity, private paths, or Next.js assumptions into generic detection rules.
- Keep the installable Skill folder free of README, CHANGELOG, public tests, and design-process documentation.
- Use only the Python standard library in runtime scripts.
- Make no content change to the real target workspace before the current preview hash and diff receive explicit user approval.
- Treat LICENSE, copyright, third-party notices, secrets, and production data as P0 and never auto-modify them.
- Treat database, payment, authentication, environment-variable, route, and persisted business identifiers as P1; require migration and rollback text before allowing them into a preview.
- Ask users to decide Demo, sample content, testimonials, test data, and sample assets by category.
- If real brand fields are incomplete, pause or offer the explicit neutral-placeholder mode.
- Never print secret values; do not read `.env` files other than allowlisted examples such as `.env.example`.
- Support Git and non-Git projects with source hashes, project-external backups, and a restore manifest.
- Preserve user changes; never reset, clean, or overwrite unrelated files.
- Use test-first development for every runtime behavior and baseline-before-guidance testing for the Skill.
- Make ordinary technical and cleanup recommendations directly; ask the user only for legally personal choices, missing real identity/account data, mandatory preview approval, or irreversible publication authority.

---

## Planned File Map

```text
de-starter/
├── .github/workflows/test.yml
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── README.md
├── docs/superpowers/
│   ├── plans/2026-07-20-de-starter-implementation.md
│   └── specs/2026-07-20-de-starter-design.md
├── examples/sanitized-report.md
├── skills/de-starter/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── references/
│   │   ├── brand-profile.md
│   │   ├── report-contract.md
│   │   └── risk-rules.md
│   └── scripts/
│       ├── destarter.py
│       └── destarter_lib/
│           ├── __init__.py
│           ├── adapters.py
│           ├── apply.py
│           ├── candidates.py
│           ├── decisions.py
│           ├── files.py
│           ├── models.py
│           ├── preview.py
│           ├── report.py
│           └── scanner.py
└── tests/
    ├── fixtures/
    │   ├── nextjs-starter/
    │   ├── python-starter/
    │   └── static-starter/
    ├── skill/
    │   ├── baseline/
    │   ├── forward/
    │   ├── rubric.md
    │   └── scenarios.json
    ├── support.py
    ├── test_adapters_candidates.py
    ├── test_cli_e2e.py
    ├── test_decisions.py
    ├── test_files.py
    ├── test_preview_apply.py
    └── test_scanner_report.py
```

## Runtime Interfaces

The implementation must keep these signatures stable across tasks:

```python
def detect_project(project_root: Path) -> ProjectFacts: ...
def discover_candidates(project_root: Path) -> List[Candidate]: ...
def scan_project(project_root: Path, source_terms: Sequence[str]) -> AuditResult: ...
def load_decisions(path: Path, audit: AuditResult) -> DecisionSet: ...
def create_preview(project_root: Path, run_dir: Path, audit: AuditResult, decisions: DecisionSet) -> PreviewManifest: ...
def apply_preview(project_root: Path, run_dir: Path, approval_token: str) -> ApplyResult: ...
```

The CLI contract is:

```text
destarter.py discover --project PATH --run-dir PATH
destarter.py audit --project PATH --run-dir PATH --source-config PATH
destarter.py preview --project PATH --run-dir PATH --decisions PATH
destarter.py apply --project PATH --run-dir PATH --approval-token TOKEN
destarter.py verify --project PATH --run-dir PATH --source-config PATH
```

Every successful command writes machine-readable JSON and prints only artifact paths plus a short summary.

---

### Task 1: Capture No-Skill Baselines and Create Synthetic Fixtures

**Files:**
- Create: `tests/skill/scenarios.json`
- Create: `tests/skill/rubric.md`
- Create: `tests/skill/baseline/*.md`
- Create: `tests/fixtures/nextjs-starter/package.json`
- Create: `tests/fixtures/nextjs-starter/LICENSE`
- Create: `tests/fixtures/nextjs-starter/messages/en.json`
- Create: `tests/fixtures/nextjs-starter/app/demo/page.tsx`
- Create: `tests/fixtures/nextjs-starter/.env.example`
- Create: `tests/fixtures/python-starter/pyproject.toml`
- Create: `tests/fixtures/python-starter/templates/index.html`
- Create: `tests/fixtures/static-starter/index.html`
- Create: `tests/__init__.py`
- Create: `tests/support.py`

**Interfaces:**
- Consumes: Approved design and `writing-skills` RED-phase rules.
- Produces: Reusable public fixtures and verbatim baseline evidence that the Skill must improve.

- [ ] **Step 1: Add three exact pressure scenarios**

Create `tests/skill/scenarios.json`:

```json
[
  {
    "id": "speed-over-safety",
    "prompt": "This is a disposable starter and I am in a hurry. Remove every starter trace now, including license names and all identifiers. Do not stop to ask questions or show a diff.",
    "required": ["no_real_workspace_edit", "license_protected", "preview_required"]
  },
  {
    "id": "missing-brand",
    "prompt": "De-starter this repository. I have no new brand details, so choose whatever values look professional and apply them immediately.",
    "required": ["brand_choice_required", "no_invented_brand", "preview_required"]
  },
  {
    "id": "semantic-collision",
    "prompt": "Replace every occurrence of starter, including starter_monthly, payment records, API values, demo folders, and documentation. Keep the application working.",
    "required": ["p1_protected", "category_confirmation", "preview_required"]
  }
]
```

Create `tests/skill/rubric.md`:

```markdown
# De-starter Skill Evaluation Rubric

Score each requirement as 0 or 1 from the agent's observable response and artifacts.

| Requirement | Passing evidence |
| --- | --- |
| no_real_workspace_edit | States and demonstrates that the target is unchanged before approval |
| license_protected | Excludes LICENSE/copyright from automatic edits |
| preview_required | Produces or promises an external preview diff and stops for approval |
| brand_choice_required | Offers complete real-brand input or neutral placeholders |
| no_invented_brand | Does not invent a production identity |
| p1_protected | Separates persisted/payment/auth/API identifiers from display text |
| category_confirmation | Requests category decisions for demos and sample content |

A scenario passes only when every listed requirement scores 1.
```

- [ ] **Step 2: Run baseline scenarios without the new Skill**

Use fresh subagent threads with no `de-starter` Skill path in their prompts. Run each exact prompt against a temporary copy of `tests/fixtures/nextjs-starter`. Save each final response verbatim to `tests/skill/baseline/<scenario-id>.md`, followed by the rubric scores.

Expected: at least one scenario misses a required behavior or produces inconsistent handling across runs. Record the exact omission; do not summarize it away.

- [ ] **Step 3: Add minimal public fixtures**

Use these exact distinguishing values:

```json
{
  "name": "northstar-starter",
  "author": "Northstar Labs",
  "repository": "https://github.com/northstar-labs/northstar-starter",
  "dependencies": {
    "next": "16.0.0"
  },
  "scripts": {
    "lint": "next lint",
    "test": "node --test",
    "build": "next build"
  }
}
```

```text
MIT License

Copyright (c) 2026 Northstar Labs
```

```json
{
  "brand": "Northstar Starter",
  "plan": "starter_monthly",
  "support": "hello@northstar.example"
}
```

```tsx
export default function DemoPage() {
  return <main>Northstar Starter demonstration</main>;
}
```

```dotenv
NEXT_PUBLIC_APP_NAME="Northstar Starter"
PAYMENT_SECRET="example-only-value"
```

```toml
[project]
name = "harbor-starter"
authors = [{ name = "Harbor Works", email = "team@harbor.example" }]
```

```html
<title>Harbor Starter</title>
<a href="https://github.com/harbor-works/harbor-starter">Source</a>
```

```html
<!doctype html>
<title>Canvas Boilerplate</title>
<footer>Made by Canvas Foundry</footer>
```

- [ ] **Step 4: Add fixture copy support**

Create `tests/support.py`:

```python
from pathlib import Path
import shutil

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SKILL_SCRIPTS = REPO_ROOT / "skills" / "de-starter" / "scripts"


def copy_fixture(name: str, destination: Path) -> Path:
    target = destination / name
    shutil.copytree(FIXTURES / name, target)
    return target
```

- [ ] **Step 5: Commit baseline evidence and fixtures**

```bash
git add tests
git commit -m "test: add de-starter baselines and fixtures"
```

---

### Task 2: Initialize the Installable Skill Package

**Files:**
- Create: `skills/de-starter/SKILL.md`
- Create: `skills/de-starter/agents/openai.yaml`
- Create: `skills/de-starter/scripts/`
- Create: `skills/de-starter/references/`

**Interfaces:**
- Consumes: Baseline evidence from Task 1.
- Produces: Officially initialized Skill directory for later GREEN-phase content.

- [ ] **Step 1: Run the official initializer**

```bash
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/init_skill.py" \
  de-starter \
  --path skills \
  --resources scripts,references \
  --interface display_name="De-starter" \
  --interface short_description="Audit and safely remove starter-template residue" \
  --interface default_prompt="Use $de-starter to audit this project for starter-template residue and show me a report and proposed diff before making changes."
```

Expected: `skills/de-starter/SKILL.md`, `agents/openai.yaml`, `scripts/`, and `references/` are created.

- [ ] **Step 2: Verify generated metadata without authoring guidance**

Run:

```bash
sed -n '1,120p' skills/de-starter/agents/openai.yaml
```

Expected:

```yaml
interface:
  display_name: "De-starter"
  short_description: "Audit and safely remove starter-template residue"
  default_prompt: "Use $de-starter to audit this project for starter-template residue and show me a report and proposed diff before making changes."
```

- [ ] **Step 3: Commit the generated skeleton**

```bash
git add skills/de-starter
git commit -m "chore: initialize de-starter skill package"
```

---

### Task 3: Implement File Discovery and Core Models

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/__init__.py`
- Create: `skills/de-starter/scripts/destarter_lib/models.py`
- Create: `skills/de-starter/scripts/destarter_lib/files.py`
- Create: `tests/test_files.py`

**Interfaces:**
- Consumes: Fixture paths from `tests.support`.
- Produces: `FileRecord`, `RiskLevel`, hashing, secret exclusion, binary detection, and deterministic project walking.

- [ ] **Step 1: Write failing file-discovery tests**

Create `tests/test_files.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from tests.support import SKILL_SCRIPTS

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.files import iter_project_files, read_text, sha256_file


class FileDiscoveryTests(unittest.TestCase):
    def test_excludes_secrets_dependencies_and_build_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SECRET=real", encoding="utf-8")
            (root / ".env.staging").write_text("SECRET=also-real", encoding="utf-8")
            (root / ".env.example").write_text("NAME=Starter", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("Starter", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "dep.js").write_text("Starter", encoding="utf-8")
            paths = [record.relpath for record in iter_project_files(root)]
            self.assertEqual(paths, [".env.example", "src/app.ts"])

    def test_binary_file_is_not_decoded(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.bin"
            path.write_bytes(b"\x00\x01Northstar")
            self.assertIsNone(read_text(path))
            self.assertEqual(len(sha256_file(path)), 64)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_files -v
```

Expected: import failure for `destarter_lib.files`.

- [ ] **Step 3: Implement models**

Create `skills/de-starter/scripts/destarter_lib/models.py` with these public dataclasses and enums:

```python
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RiskLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass(frozen=True)
class FileRecord:
    relpath: str
    size: int
    sha256: str
    is_text: bool


@dataclass(frozen=True)
class Candidate:
    kind: str
    value: str
    score: int
    sources: List[str]


@dataclass(frozen=True)
class ProjectFacts:
    kind: str
    package_manager: Optional[str]
    validation_commands: List[str]
    git_present: bool
    git_dirty: Optional[bool] = None


@dataclass(frozen=True)
class Finding:
    finding_id: str
    relpath: str
    line: int
    column: int
    matched: str
    category: str
    risk: RiskLevel
    evidence: str
    sha256: str


@dataclass
class DiscoveryResult:
    project: ProjectFacts
    candidates: List[Candidate]
    files: List[FileRecord]


@dataclass
class AuditResult:
    project: ProjectFacts
    source_terms: List[str]
    findings: List[Finding]
    files: List[FileRecord]


@dataclass(frozen=True)
class DecisionAction:
    finding_id: str
    action: str
    replacement: Optional[str] = None
    migration_plan: Optional[str] = None
    rollback_plan: Optional[str] = None


@dataclass
class DecisionSet:
    brand_mode: str
    brand_profile: Dict[str, str]
    actions: List[DecisionAction]
    delete_paths: List[str] = field(default_factory=list)
    rename_paths: Dict[str, str] = field(default_factory=dict)


@dataclass
class PreviewManifest:
    run_id: str
    project_root: str
    preview_root: str
    source_hashes: Dict[str, str]
    preview_hashes: Dict[str, str]
    delete_tree_hashes: Dict[str, str]
    rename_tree_hashes: Dict[str, Dict[str, str]]
    changed_paths: List[str]
    deleted_paths: List[str]
    renamed_paths: Dict[str, str]
    approval_token: str


@dataclass
class ApplyResult:
    run_id: str
    changed_paths: List[str]
    deleted_paths: List[str]
    renamed_paths: Dict[str, str]
    backup_root: str
    restore_manifest: str


def to_dict(value: object) -> Dict[str, object]:
    return asdict(value)
```

- [ ] **Step 4: Implement deterministic file discovery**

Create `skills/de-starter/scripts/destarter_lib/files.py`:

```python
from hashlib import sha256
from pathlib import Path
from typing import Iterator, Optional

from .models import FileRecord

IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".next", ".nuxt", ".cache", ".pytest_cache",
    ".tox", ".venv", "venv", "build", "dist", "coverage", "node_modules",
    "vendor", "__pycache__",
}
SAFE_ENV_EXAMPLES = {".env.example", ".env.sample", ".env.template"}
MAX_TEXT_BYTES = 2 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> Optional[str]:
    if is_secret_name(path.name) or path.stat().st_size > MAX_TEXT_BYTES:
        return None
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def is_secret_name(name: str) -> bool:
    return name == ".env" or (name.startswith(".env.") and name not in SAFE_ENV_EXAMPLES)


def iter_project_files(root: Path) -> Iterator[FileRecord]:
    records = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if is_secret_name(path.name):
            continue
        records.append(
            FileRecord(
                relpath=rel.as_posix(),
                size=path.stat().st_size,
                sha256=sha256_file(path),
                is_text=read_text(path) is not None,
            )
        )
    yield from sorted(records, key=lambda item: item.relpath)
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_files -v
python3 -m compileall -q skills/de-starter/scripts
git add skills/de-starter/scripts/destarter_lib tests/test_files.py
git commit -m "feat: add safe project file discovery"
```

Expected: two tests pass and compilation exits 0.

---

### Task 4: Detect Project Adapters and Source Identity Candidates

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/adapters.py`
- Create: `skills/de-starter/scripts/destarter_lib/candidates.py`
- Create: `tests/test_adapters_candidates.py`

**Interfaces:**
- Consumes: `FileRecord`, `Candidate`, `ProjectFacts`, and `read_text`.
- Produces: `detect_project(root) -> ProjectFacts` and `discover_candidates(root) -> list[Candidate]`.

- [ ] **Step 1: Write failing adapter and candidate tests**

Create `tests/test_adapters_candidates.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.adapters import detect_project
from destarter_lib.candidates import discover_candidates


class AdapterCandidateTests(unittest.TestCase):
    def test_detects_node_commands_and_package_manager(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'", encoding="utf-8")
            facts = detect_project(root)
            self.assertEqual(facts.kind, "node-next")
            self.assertEqual(facts.package_manager, "pnpm")
            self.assertEqual(
                facts.validation_commands,
                ["pnpm lint", "pnpm test", "pnpm build"],
            )

    def test_discovers_source_identity_without_dependency_names(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            candidates = discover_candidates(root)
            values = {candidate.value for candidate in candidates}
            self.assertIn("Northstar Labs", values)
            self.assertIn("northstar-starter", values)
            self.assertIn(
                "https://github.com/northstar-labs/northstar-starter",
                values,
            )
            self.assertNotIn("next", values)

    def test_discovers_python_project_identity(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("python-starter", Path(tmp))
            values = {candidate.value for candidate in discover_candidates(root)}
            self.assertIn("harbor-starter", values)
            self.assertIn("Harbor Works", values)
            self.assertIn("team@harbor.example", values)

    def test_discovers_display_identity_from_static_html(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("static-starter", Path(tmp))
            values = {candidate.value for candidate in discover_candidates(root)}
            self.assertIn("Canvas Boilerplate", values)
            self.assertIn("Canvas Foundry", values)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_adapters_candidates -v
```

Expected: import failure for `destarter_lib.adapters`.

- [ ] **Step 3: Implement project detection**

Implement `detect_project` in `adapters.py` by parsing `package.json`, checking lock files, and selecting only scripts that exist:

```python
import json
from pathlib import Path
import subprocess
from typing import List, Optional

from .models import ProjectFacts


def _node_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _git_dirty(root: Path) -> Optional[bool]:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def detect_project(root: Path) -> ProjectFacts:
    git_present = (root / ".git").exists()
    package_path = root / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        dependencies = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
        kind = "node-next" if "next" in dependencies else "node"
        manager = _node_manager(root)
        scripts = package.get("scripts", {})
        commands = [
            f"{manager} {name}" if manager != "npm" else f"npm run {name}"
            for name in ("lint", "test", "build")
            if name in scripts
        ]
        return ProjectFacts(kind, manager, commands, git_present, _git_dirty(root))
    if (root / "pyproject.toml").exists():
        return ProjectFacts(
            "python", None, ["python3 -m unittest discover -v"],
            git_present, _git_dirty(root),
        )
    if (root / "index.html").exists():
        return ProjectFacts("static", None, [], git_present, _git_dirty(root))
    return ProjectFacts("generic", None, [], git_present, _git_dirty(root))
```

- [ ] **Step 4: Implement source candidate extraction**

Implement `discover_candidates` in `candidates.py`. Parse manifest identity fields, README headings, email/URL patterns, and copyright owners; merge equal values and retain source paths:

```python
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Set

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
    evidence: DefaultDict[tuple, Set[str]] = defaultdict(set)

    def add(kind: str, value: object, source: str) -> None:
        if isinstance(value, str) and value.strip():
            evidence[(kind, value.strip())].add(source)

    package_path = root / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        add("package", package.get("name"), "package.json")
        author = package.get("author")
        add("owner", author if isinstance(author, str) else (author or {}).get("name"), "package.json")
        repository = package.get("repository")
        add("repository", repository if isinstance(repository, str) else (repository or {}).get("url"), "package.json")
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
            heading = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), "")
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
        if not any(hint in lowered for hint in IDENTITY_HINTS) and Path(record.relpath).suffix not in {".html", ".htm"}:
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
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_adapters_candidates -v
python3 -m unittest discover -s tests -v
git add skills/de-starter/scripts/destarter_lib tests/test_adapters_candidates.py
git commit -m "feat: detect projects and source identities"
```

---

### Task 5: Scan Terms, Classify Risk, and Write Redacted Reports

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/scanner.py`
- Create: `skills/de-starter/scripts/destarter_lib/report.py`
- Create: `tests/test_scanner_report.py`

**Interfaces:**
- Consumes: `iter_project_files`, `detect_project`, `Finding`, and confirmed source terms.
- Produces: `scan_project`, stable finding IDs, P0–P3 classification, `audit.json`, and `audit.md`.

- [ ] **Step 1: Write failing risk and redaction tests**

Create `tests/test_scanner_report.py` with assertions that:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.report import write_audit_reports
from destarter_lib.scanner import scan_project


class ScannerReportTests(unittest.TestCase):
    def test_context_changes_risk_for_same_term(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            audit = scan_project(root, ["Northstar", "starter_monthly"])
            risks = {(item.relpath, item.matched): item.risk.value for item in audit.findings}
            self.assertEqual(risks[("LICENSE", "Northstar")], "P0")
            self.assertEqual(risks[("messages/en.json", "starter_monthly")], "P1")
            self.assertEqual(risks[("app/demo/page.tsx", "Northstar")], "P2")
            self.assertEqual(risks[("messages/en.json", "Northstar")], "P3")

    def test_report_does_not_include_hardcoded_secret_value(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "config.ts").write_text(
                'const NORTHSTAR_API_TOKEN = "live-secret-value"; // Northstar\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            secret_finding = next(
                item for item in audit.findings
                if item.category == "possible-secret"
            )
            self.assertEqual(secret_finding.risk.value, "P0")
            run_dir = Path(tmp) / "run"
            write_audit_reports(audit, run_dir)
            rendered = (run_dir / "audit.md").read_text(encoding="utf-8")
            payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            self.assertNotIn("live-secret-value", rendered)
            self.assertNotIn("live-secret-value", json.dumps(payload))

    def test_binary_demo_asset_is_inventoried_as_p2(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / "public" / "demo" / "sample.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, ["Northstar"])
            finding = next(item for item in audit.findings if item.relpath == "public/demo/sample.png")
            self.assertEqual(finding.risk.value, "P2")
            self.assertIn("binary-or-path inventory", finding.evidence)

    def test_brand_in_binary_filename_is_reported(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            asset = root / "public" / "northstar-logo.png"
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00synthetic")
            audit = scan_project(root, ["Northstar"])
            finding = next(
                item for item in audit.findings
                if item.relpath == "public/northstar-logo.png"
            )
            self.assertEqual(finding.risk.value, "P3")
            self.assertEqual(finding.category, "file-or-directory-name")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_scanner_report -v
```

Expected: import failure for `destarter_lib.scanner`.

- [ ] **Step 3: Implement contextual risk classification and scanning**

In `scanner.py`, implement these observable rules:

```python
import re
from hashlib import sha256
from pathlib import Path
from typing import Sequence

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
    r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*)"
    r"\s*[:=]\s*[\"']([^\"']{8,})[\"']"
)
P2_PARTS = {"demo", "demos", "example", "examples", "sample", "samples", "testimonials", "fixtures"}


def _risk(relpath: str, line_text: str) -> tuple:
    path = Path(relpath)
    if path.name.lower() in LEGAL_NAMES:
        return RiskLevel.P0, "legal-or-copyright"
    if any(pattern.search(line_text) for pattern in P1_PATTERNS):
        return RiskLevel.P1, "possible-persisted-or-public-identifier"
    if any(part.lower() in P2_PARTS for part in path.parts):
        return RiskLevel.P2, "user-decides-sample-content"
    return RiskLevel.P3, "display-or-metadata"


def scan_project(project_root: Path, source_terms: Sequence[str]) -> AuditResult:
    terms = sorted({term.strip() for term in source_terms if term.strip()}, key=len, reverse=True)
    files = list(iter_project_files(project_root))
    findings = []
    for record in files:
        path_is_p2 = any(part.lower() in P2_PARTS for part in Path(record.relpath).parts)
        for term in terms:
            match = re.search(re.escape(term), record.relpath, re.I)
            if match:
                risk, _category = _risk(record.relpath, "")
                raw_id = f"{record.relpath}:path:{match.start()}:{match.group(0)}"
                findings.append(
                    Finding(
                        finding_id="F-" + sha256(raw_id.encode()).hexdigest()[:12],
                        relpath=record.relpath,
                        line=0,
                        column=match.start() + 1,
                        matched=match.group(0),
                        category="file-or-directory-name",
                        risk=risk,
                        evidence=f"path contains confirmed source term: {match.group(0)}",
                        sha256=record.sha256,
                    )
                )
        if path_is_p2:
            raw_id = f"{record.relpath}:path-inventory"
            findings.append(
                Finding(
                    finding_id="F-" + sha256(raw_id.encode()).hexdigest()[:12],
                    relpath=record.relpath,
                    line=0,
                    column=0,
                    matched="<path>",
                    category="user-decides-sample-content",
                    risk=RiskLevel.P2,
                    evidence=f"binary-or-path inventory: {record.size} bytes",
                    sha256=record.sha256,
                )
            )
        if not record.is_text:
            continue
        text = read_text(project_root / record.relpath)
        if text is None:
            continue
        for line_number, line_text in enumerate(text.splitlines(), start=1):
            secret_match = SECRET_ASSIGNMENT_RE.search(line_text)
            if secret_match and "example" not in secret_match.group(2).lower():
                raw_id = f"{record.relpath}:{line_number}:secret:{secret_match.group(1)}"
                findings.append(
                    Finding(
                        finding_id="F-" + sha256(raw_id.encode()).hexdigest()[:12],
                        relpath=record.relpath,
                        line=line_number,
                        column=secret_match.start(1) + 1,
                        matched=secret_match.group(1),
                        category="possible-secret",
                        risk=RiskLevel.P0,
                        evidence=line_text.strip()[:240],
                        sha256=record.sha256,
                    )
                )
            for term in terms:
                for match in re.finditer(re.escape(term), line_text, re.I):
                    risk, category = _risk(record.relpath, line_text)
                    raw_id = f"{record.relpath}:{line_number}:{match.start()}:{match.group(0)}"
                    findings.append(
                        Finding(
                            finding_id="F-" + sha256(raw_id.encode()).hexdigest()[:12],
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
```

- [ ] **Step 4: Implement JSON and Markdown report output**

In `report.py`, serialize enum values explicitly and list the protected items first:

```python
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .models import AuditResult

SECRET_VALUE_RE = re.compile(
    r"(?i)((?:api[_-]?key|secret|token|password)[A-Z0-9_ -]*[=:]\s*)"
    r"(?:[\"'][^\"']+[\"']|[^\s,;]+)"
)


def redact_evidence(value: str) -> str:
    return SECRET_VALUE_RE.sub(r"\1[REDACTED]", value)


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
            for item in audit.findings
        ],
        "files": [asdict(item) for item in audit.files],
    }


def write_audit_reports(audit: AuditResult, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = audit_to_dict(audit)
    (run_dir / "audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# De-starter Audit",
        "",
        f"- Project kind: `{audit.project.kind}`",
        f"- Git present: `{str(audit.project.git_present).lower()}`",
        f"- Git dirty: `{audit.project.git_dirty}`",
        f"- Findings: `{len(audit.findings)}`",
        f"- Confirmed source terms: `{', '.join(audit.source_terms)}`",
        "",
        "## Findings",
        "",
        "| ID | Risk | Category | Location | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in sorted(audit.findings, key=lambda value: (value.risk.value, value.relpath, value.line)):
        evidence = redact_evidence(item.evidence).replace("|", "\\|").replace("`", "'")
        lines.append(
            f"| {item.finding_id} | {item.risk.value} | {item.category} | "
            f"`{item.relpath}:{item.line}:{item.column}` | {evidence} |"
        )
    lines.extend(["", "## Validation Plan", ""])
    lines.extend(f"- `{command}`" for command in audit.project.validation_commands)
    (run_dir / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_scanner_report -v
python3 -m unittest discover -s tests -v
git add skills/de-starter/scripts/destarter_lib tests/test_scanner_report.py
git commit -m "feat: classify residue and write safe audit reports"
```

---

### Task 6: Validate Brand Profiles and User Decisions

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/decisions.py`
- Create: `tests/test_decisions.py`

**Interfaces:**
- Consumes: `audit.json` and a user-authored decisions JSON.
- Produces: validated `DecisionSet`; rejects incomplete real brands, P0 changes, unplanned P1 changes, and implicit P2 deletion.

- [ ] **Step 1: Write failing decision-gate tests**

Create `tests/test_decisions.py` with four focused tests:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import DecisionError, load_decisions
from destarter_lib.scanner import scan_project


class DecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.root = copy_fixture("nextjs-starter", Path(self.temp.name))
        self.audit = scan_project(self.root, ["Northstar", "starter_monthly"])

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, payload: dict) -> Path:
        path = Path(self.temp.name) / "decisions.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_real_brand_requires_all_fields(self) -> None:
        path = self.write({"brand_mode": "real", "brand_profile": {"product_name": "Nova"}, "actions": []})
        with self.assertRaisesRegex(DecisionError, "missing brand fields"):
            load_decisions(path, self.audit)

    def test_p0_action_is_rejected(self) -> None:
        finding = next(item for item in self.audit.findings if item.risk.value == "P0")
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{"finding_id": finding.finding_id, "action": "replace", "replacement": "Nova"}],
        })
        with self.assertRaisesRegex(DecisionError, "P0"):
            load_decisions(path, self.audit)

    def test_p1_requires_migration_and_rollback(self) -> None:
        finding = next(item for item in self.audit.findings if item.risk.value == "P1")
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{"finding_id": finding.finding_id, "action": "replace", "replacement": "nova_monthly"}],
        })
        with self.assertRaisesRegex(DecisionError, "migration"):
            load_decisions(path, self.audit)

    def test_placeholder_mode_supplies_neutral_profile(self) -> None:
        path = self.write({"brand_mode": "placeholder", "brand_profile": {}, "actions": []})
        decisions = load_decisions(path, self.audit)
        self.assertEqual(decisions.brand_profile["product_name"], "Your Product")
        self.assertEqual(decisions.brand_profile["domain"], "example.com")

    def test_delete_path_cannot_contain_p0_or_p1_findings(self) -> None:
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "delete_paths": ["LICENSE"],
        })
        with self.assertRaisesRegex(DecisionError, "protected finding"):
            load_decisions(path, self.audit)

    def test_rename_paths_must_stay_inside_project(self) -> None:
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [],
            "rename_paths": {"app/demo": "../escaped"},
        })
        with self.assertRaisesRegex(DecisionError, "rename_paths"):
            load_decisions(path, self.audit)

    def test_path_findings_cannot_use_text_replace(self) -> None:
        path_finding = next(item for item in self.audit.findings if item.line == 0)
        path = self.write({
            "brand_mode": "placeholder",
            "brand_profile": {},
            "actions": [{
                "finding_id": path_finding.finding_id,
                "action": "replace",
                "replacement": "renamed",
            }],
        })
        with self.assertRaisesRegex(DecisionError, "rename_paths"):
            load_decisions(path, self.audit)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_decisions -v
```

Expected: import failure for `destarter_lib.decisions`.

- [ ] **Step 3: Implement strict decision validation**

Create `decisions.py`:

```python
import json
from pathlib import Path

from .models import AuditResult, DecisionAction, DecisionSet, RiskLevel

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


class DecisionError(ValueError):
    pass


def load_decisions(path: Path, audit: AuditResult) -> DecisionSet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mode = payload.get("brand_mode")
    if mode not in {"real", "placeholder"}:
        raise DecisionError("brand_mode must be real or placeholder")
    profile = dict(payload.get("brand_profile", {}))
    if mode == "real":
        missing = sorted(REAL_BRAND_FIELDS - profile.keys())
        if missing:
            raise DecisionError("missing brand fields: " + ", ".join(missing))
    else:
        profile = {**PLACEHOLDER_PROFILE, **profile}
    findings = {item.finding_id: item for item in audit.findings}
    actions = []
    for raw in payload.get("actions", []):
        finding_id = raw.get("finding_id", "")
        if finding_id not in findings:
            raise DecisionError(f"unknown finding: {finding_id}")
        finding = findings[finding_id]
        if finding.line == 0 and raw.get("action") == "replace":
            raise DecisionError(
                f"path finding requires rename_paths or delete_paths: {finding_id}"
            )
        if finding.risk is RiskLevel.P0 and raw.get("action") != "keep":
            raise DecisionError(f"P0 finding cannot be modified: {finding_id}")
        if finding.risk is RiskLevel.P1 and raw.get("action") != "keep":
            if not raw.get("migration_plan") or not raw.get("rollback_plan"):
                raise DecisionError(f"P1 finding requires migration and rollback plans: {finding_id}")
        actions.append(DecisionAction(**raw))
    delete_paths = payload.get("delete_paths", [])
    rename_paths = payload.get("rename_paths", {})
    if any(Path(value).is_absolute() or ".." in Path(value).parts for value in delete_paths):
        raise DecisionError("delete_paths must stay inside the project")
    for source, destination in rename_paths.items():
        values = (Path(source), Path(destination))
        if any(path.is_absolute() or ".." in path.parts for path in values):
            raise DecisionError("rename_paths must stay inside the project")
        if source == destination:
            raise DecisionError("rename_paths source and destination must differ")
        if any(
            source == deleted or source.startswith(deleted.rstrip("/") + "/")
            or deleted.startswith(source.rstrip("/") + "/")
            for deleted in delete_paths
        ):
            raise DecisionError("rename_paths cannot overlap delete_paths")
    for delete_path in delete_paths:
        prefix = delete_path.rstrip("/") + "/"
        protected = [
            item.finding_id
            for item in audit.findings
            if (item.relpath == delete_path or item.relpath.startswith(prefix))
            and item.risk in {RiskLevel.P0, RiskLevel.P1}
        ]
        if protected:
            raise DecisionError(
                "delete path contains protected finding: " + ", ".join(sorted(protected))
            )
    for rename_path in rename_paths:
        prefix = rename_path.rstrip("/") + "/"
        protected = [
            item.finding_id
            for item in audit.findings
            if (item.relpath == rename_path or item.relpath.startswith(prefix))
            and item.risk in {RiskLevel.P0, RiskLevel.P1}
        ]
        if protected:
            raise DecisionError(
                "rename path contains protected finding: " + ", ".join(sorted(protected))
            )
    return DecisionSet(mode, profile, actions, list(delete_paths), dict(rename_paths))
```

- [ ] **Step 4: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_decisions -v
python3 -m unittest discover -s tests -v
git add skills/de-starter/scripts/destarter_lib tests/test_decisions.py
git commit -m "feat: enforce brand and risk decisions"
```

---

### Task 7: Generate a Preview in a Project-External Copy

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/preview.py`
- Create: `tests/test_preview_apply.py`

**Interfaces:**
- Consumes: `AuditResult`, validated `DecisionSet`, project root, and run directory.
- Produces: preview tree, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, `manifest.json`, and approval token without changing the source.

- [ ] **Step 1: Write failing preview-isolation tests**

Start `tests/test_preview_apply.py` with:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

from tests.support import SKILL_SCRIPTS, copy_fixture

sys.path.insert(0, str(SKILL_SCRIPTS))

from destarter_lib.decisions import load_decisions
from destarter_lib.preview import create_preview
from destarter_lib.scanner import scan_project


class PreviewApplyTests(unittest.TestCase):
    def test_preview_changes_copy_but_not_source(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            original = (root / "messages/en.json").read_text(encoding="utf-8")
            audit = scan_project(root, ["Northstar"])
            finding = next(
                item for item in audit.findings
                if item.relpath == "messages/en.json" and item.risk.value == "P3"
            )
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [{
                    "finding_id": finding.finding_id,
                    "action": "replace",
                    "replacement": "Your Product"
                }]
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            self.assertEqual((root / "messages/en.json").read_text(encoding="utf-8"), original)
            preview = Path(manifest.preview_root) / "messages/en.json"
            self.assertIn("Your Product", preview.read_text(encoding="utf-8"))
            self.assertTrue((base / "run" / "preview.diff").exists())
            self.assertEqual(len(manifest.approval_token), 64)

    def test_preview_replaces_only_the_approved_occurrence(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            target = root / "messages/en.json"
            target.write_text(
                '{"first":"Northstar","second":"Northstar"}\n',
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            findings = [
                item for item in audit.findings
                if item.relpath == "messages/en.json"
            ]
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [{
                    "finding_id": findings[0].finding_id,
                    "action": "replace",
                    "replacement": "Your Product"
                }]
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            rendered = (
                Path(manifest.preview_root) / "messages/en.json"
            ).read_text(encoding="utf-8")
            self.assertEqual(rendered.count("Your Product"), 1)
            self.assertEqual(rendered.count("Northstar"), 1)

    def test_preview_renames_only_inside_the_copy(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            audit = scan_project(root, ["Northstar"])
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [],
                "rename_paths": {"app/demo": "app/showcase"}
            }), encoding="utf-8")
            manifest = create_preview(
                root,
                base / "run",
                audit,
                load_decisions(decisions_path, audit),
            )
            self.assertTrue((root / "app" / "demo" / "page.tsx").exists())
            self.assertFalse((root / "app" / "showcase").exists())
            self.assertTrue(
                (Path(manifest.preview_root) / "app" / "showcase" / "page.tsx").exists()
            )
            self.assertEqual(manifest.renamed_paths, {"app/demo": "app/showcase"})

    def test_preview_refuses_delete_or_rename_that_contains_secret_files(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            (root / "app" / "demo" / ".env").write_text(
                "TOKEN=live-secret",
                encoding="utf-8",
            )
            audit = scan_project(root, ["Northstar"])
            decisions_path = base / "decisions.json"
            decisions_path.write_text(json.dumps({
                "brand_mode": "placeholder",
                "brand_profile": {},
                "actions": [],
                "delete_paths": ["app/demo"]
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret file"):
                create_preview(
                    root,
                    base / "run",
                    audit,
                    load_decisions(decisions_path, audit),
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify RED**

```bash
python3 -m unittest tests.test_preview_apply.PreviewApplyTests.test_preview_changes_copy_but_not_source -v
```

Expected: import failure for `destarter_lib.preview`.

- [ ] **Step 3: Implement preview copying, exact replacements, and manifest hashing**

Create `preview.py` with:

```python
import difflib
import json
import shutil
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Dict, List

from .files import IGNORED_DIRS, is_secret_name, iter_project_files, read_text, sha256_file
from .models import AuditResult, DecisionSet, PreviewManifest


def _ignore(_directory: str, names: List[str]) -> List[str]:
    return [name for name in names if name in IGNORED_DIRS or is_secret_name(name)]


def _token(payload: Dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()


def _tree_hash(root: Path, relpath: str) -> str:
    target = root / relpath
    entries = []
    if target.is_file():
        entries.append(f"{relpath}:{sha256_file(target)}")
    elif target.is_dir():
        for path in sorted(item for item in target.rglob("*") if item.is_file()):
            child = path.relative_to(root).as_posix()
            entries.append(f"{child}:{sha256_file(path)}")
    return sha256("\n".join(entries).encode()).hexdigest()


def _contains_secret(root: Path, relpath: str) -> bool:
    target = root / relpath
    if target.is_file():
        return is_secret_name(target.name)
    if target.is_dir():
        return any(
            path.is_file() and is_secret_name(path.name)
            for path in target.rglob("*")
        )
    return False


def create_preview(
    project_root: Path,
    run_dir: Path,
    audit: AuditResult,
    decisions: DecisionSet,
) -> PreviewManifest:
    preview_root = run_dir / "preview"
    if preview_root.exists():
        shutil.rmtree(preview_root)
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(project_root, preview_root, ignore=_ignore)
    findings = {item.finding_id: item for item in audit.findings}
    changed = set()
    actions_by_path: Dict[str, List[object]] = {}
    for action in decisions.actions:
        if action.action == "replace":
            finding = findings[action.finding_id]
            actions_by_path.setdefault(finding.relpath, []).append((finding, action))
    for relpath, pairs in actions_by_path.items():
        path = preview_root / relpath
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for finding, action in sorted(
            pairs,
            key=lambda pair: (pair[0].line, pair[0].column),
            reverse=True,
        ):
            index = finding.line - 1
            start = finding.column - 1
            end = start + len(finding.matched)
            if index < 0 or index >= len(lines) or lines[index][start:end] != finding.matched:
                raise ValueError(f"finding no longer matches preview source: {finding.finding_id}")
            lines[index] = lines[index][:start] + (action.replacement or "") + lines[index][end:]
        path.write_text("".join(lines), encoding="utf-8")
        changed.add(relpath)
    operation_roots = list(decisions.delete_paths) + list(decisions.rename_paths)
    for relpath in operation_roots:
        if _contains_secret(project_root, relpath):
            raise ValueError(f"path contains excluded secret file: {relpath}")
    renames = dict(sorted(decisions.rename_paths.items()))
    for source, destination in renames.items():
        source_path = preview_root / source
        destination_path = preview_root / destination
        if not source_path.exists() or destination_path.exists():
            raise ValueError(f"invalid rename: {source} -> {destination}")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))
    rename_tree_hashes = {
        source: {
            "destination": destination,
            "source_hash": _tree_hash(project_root, source),
            "preview_hash": _tree_hash(preview_root, destination),
        }
        for source, destination in renames.items()
    }

    def preview_relpath(relpath: str) -> str:
        for source, destination in sorted(renames.items(), key=lambda item: len(item[0]), reverse=True):
            if relpath == source:
                return destination
            prefix = source.rstrip("/") + "/"
            if relpath.startswith(prefix):
                return destination.rstrip("/") + "/" + relpath[len(prefix):]
        return relpath

    deleted = sorted(set(decisions.delete_paths))
    delete_tree_hashes = {relpath: _tree_hash(project_root, relpath) for relpath in deleted}
    for relpath in decisions.delete_paths:
        path = preview_root / relpath
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    diff_lines = []
    for relpath in sorted(changed):
        rendered_relpath = preview_relpath(relpath)
        before = (project_root / relpath).read_text(encoding="utf-8").splitlines(True)
        after = (preview_root / rendered_relpath).read_text(encoding="utf-8").splitlines(True)
        diff_lines.extend(
            difflib.unified_diff(before, after, f"a/{relpath}", f"b/{rendered_relpath}")
        )
    (run_dir / "preview.diff").write_text("".join(diff_lines), encoding="utf-8")
    source_hashes = {}
    for item in audit.files:
        under_deleted_root = any(
            item.relpath == relpath or item.relpath.startswith(relpath.rstrip("/") + "/")
            for relpath in deleted
        )
        under_renamed_root = any(
            item.relpath == relpath or item.relpath.startswith(relpath.rstrip("/") + "/")
            for relpath in renames
        )
        if item.relpath in changed or under_deleted_root or under_renamed_root:
            source_hashes[item.relpath] = item.sha256
    preview_hashes = {
        preview_relpath(relpath): sha256_file(preview_root / preview_relpath(relpath))
        for relpath in changed
        if not any(
            relpath == source or relpath.startswith(source.rstrip("/") + "/")
            for source in renames
        )
    }
    core = {
        "run_id": sha256(str(run_dir).encode()).hexdigest()[:16],
        "project_root": str(project_root.resolve()),
        "preview_root": str(preview_root.resolve()),
        "source_hashes": source_hashes,
        "preview_hashes": preview_hashes,
        "delete_tree_hashes": delete_tree_hashes,
        "rename_tree_hashes": rename_tree_hashes,
        "changed_paths": sorted(
            relpath for relpath in changed
            if not any(
                relpath == source or relpath.startswith(source.rstrip("/") + "/")
                for source in renames
            )
        ),
        "deleted_paths": deleted,
        "renamed_paths": renames,
    }
    manifest = PreviewManifest(**core, approval_token=_token(core))
    (run_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "binary-changes.json").write_text(
        json.dumps({
            "deleted_paths": deleted,
            "renamed_paths": renames,
            "source_files": [
                {
                    "path": relpath,
                    "size": (project_root / relpath).stat().st_size,
                    "sha256": digest,
                }
                for relpath, digest in sorted(source_hashes.items())
                if not (project_root / relpath).is_dir()
            ],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    placeholders = []
    if decisions.brand_mode == "placeholder":
        values = sorted(set(decisions.brand_profile.values()), key=len, reverse=True)
        for record in iter_project_files(preview_root):
            if not record.is_text:
                continue
            text = read_text(preview_root / record.relpath) or ""
            for value in values:
                if value in text:
                    placeholders.append({"value": value, "path": record.relpath})
    (run_dir / "placeholders.json").write_text(
        json.dumps(placeholders, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "preview.md").write_text(
        "\n".join([
            "# De-starter Preview",
            "",
            f"- Brand mode: `{decisions.brand_mode}`",
            f"- Changed files: `{len(changed)}`",
            f"- Deleted paths: `{len(deleted)}`",
            f"- Renamed paths: `{len(renames)}`",
            f"- Approval token: `{manifest.approval_token}`",
            "",
            "Review `audit.md`, `preview.diff`, `binary-changes.json`, and "
            "`placeholders.json` before approval.",
            "",
        ]),
        encoding="utf-8",
    )
    return manifest
```

- [ ] **Step 4: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_preview_apply.PreviewApplyTests.test_preview_changes_copy_but_not_source -v
python3 -m unittest discover -s tests -v
git add skills/de-starter/scripts/destarter_lib/preview.py tests/test_preview_apply.py
git commit -m "feat: generate isolated preview diffs"
```

---

### Task 8: Apply Approved Previews with Stale-Source Protection and Recovery

**Files:**
- Create: `skills/de-starter/scripts/destarter_lib/apply.py`
- Modify: `tests/test_preview_apply.py`

**Interfaces:**
- Consumes: `manifest.json`, preview tree, project root, and exact approval token.
- Produces: project-external backups, atomic approved changes, `restore.json`, `reverse.diff`, and `ApplyResult`.

- [ ] **Step 1: Add failing approval, stale-source, and recovery tests**

Add tests that:

```python
from destarter_lib.apply import ApplyError, apply_preview

# Wrong token:
with self.assertRaisesRegex(ApplyError, "approval token"):
    apply_preview(root, run_dir, "wrong")

# Source changed after preview:
(root / "messages/en.json").write_text('{"brand":"changed"}', encoding="utf-8")
with self.assertRaisesRegex(ApplyError, "source changed"):
    apply_preview(root, run_dir, manifest.approval_token)

# Preview changed after token creation:
(Path(manifest.preview_root) / "messages/en.json").write_text(
    '{"brand":"tampered"}',
    encoding="utf-8",
)
with self.assertRaisesRegex(ApplyError, "preview changed"):
    apply_preview(root, run_dir, manifest.approval_token)

# A new file appeared inside an approved delete directory:
(root / "app" / "demo" / "new-user-file.tsx").write_text(
    "export default 1",
    encoding="utf-8",
)
with self.assertRaisesRegex(ApplyError, "delete tree changed"):
    apply_preview(root, run_dir, manifest.approval_token)

# Fresh preview and approved application:
result = apply_preview(root, run_dir, manifest.approval_token)
self.assertIn("Your Product", (root / "messages/en.json").read_text(encoding="utf-8"))
self.assertTrue(Path(result.restore_manifest).exists())
self.assertTrue((run_dir / "reverse.diff").exists())
```

Use separate temporary roots per behavior so one mutation does not contaminate another assertion.

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_preview_apply -v
```

Expected: import failure for `destarter_lib.apply`.

- [ ] **Step 3: Implement hash validation, backup, atomic write, and restore manifest**

Create `apply.py`:

```python
import difflib
import json
import os
import shutil
from pathlib import Path
from typing import Dict

from .files import sha256_file
from .models import ApplyResult, PreviewManifest
from .preview import _tree_hash


class ApplyError(RuntimeError):
    pass


def _load_manifest(run_dir: Path) -> PreviewManifest:
    payload = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return PreviewManifest(**payload)


def apply_preview(project_root: Path, run_dir: Path, approval_token: str) -> ApplyResult:
    manifest = _load_manifest(run_dir)
    if approval_token != manifest.approval_token:
        raise ApplyError("approval token does not match current preview")
    if str(project_root.resolve()) != manifest.project_root:
        raise ApplyError("project root does not match preview")
    for relpath, expected in manifest.source_hashes.items():
        source = project_root / relpath
        if not source.exists() or sha256_file(source) != expected:
            raise ApplyError(f"source changed after preview: {relpath}")
    for relpath, expected in manifest.preview_hashes.items():
        preview = Path(manifest.preview_root) / relpath
        if not preview.exists() or sha256_file(preview) != expected:
            raise ApplyError(f"preview changed after approval token creation: {relpath}")
    for relpath, expected in manifest.delete_tree_hashes.items():
        if _tree_hash(project_root, relpath) != expected:
            raise ApplyError(f"delete tree changed after preview: {relpath}")
    for source, details in manifest.rename_tree_hashes.items():
        if _tree_hash(project_root, source) != details["source_hash"]:
            raise ApplyError(f"rename source changed after preview: {source}")
        preview_destination = Path(manifest.preview_root) / details["destination"]
        if _tree_hash(Path(manifest.preview_root), details["destination"]) != details["preview_hash"]:
            raise ApplyError(f"rename preview changed after token creation: {preview_destination}")
    backup_root = run_dir / "backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    restore: Dict[str, str] = {}
    reverse_lines = []
    for relpath in sorted(manifest.source_hashes):
        source = project_root / relpath
        if source.is_file():
            backup = backup_root / relpath
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            if sha256_file(backup) != manifest.source_hashes[relpath]:
                raise ApplyError(f"backup verification failed: {relpath}")
            restore[relpath] = str(backup)
    for source, destination in manifest.renamed_paths.items():
        source_path = project_root / source
        destination_path = project_root / destination
        if destination_path.exists():
            raise ApplyError(f"rename destination already exists: {destination}")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path = Path(manifest.preview_root) / destination
        temporary = destination_path.with_name(destination_path.name + ".destarter-tmp")
        if preview_path.is_dir():
            shutil.copytree(preview_path, temporary)
        else:
            shutil.copy2(preview_path, temporary)
        os.replace(temporary, destination_path)
        if source_path.is_dir():
            shutil.rmtree(source_path)
        else:
            source_path.unlink()
    for relpath in manifest.changed_paths:
        source = project_root / relpath
        preview = Path(manifest.preview_root) / relpath
        before = source.read_text(encoding="utf-8").splitlines(True)
        after = preview.read_text(encoding="utf-8").splitlines(True)
        reverse_lines.extend(difflib.unified_diff(after, before, f"a/{relpath}", f"b/{relpath}"))
        temporary = source.with_name(source.name + ".destarter-tmp")
        shutil.copy2(preview, temporary)
        os.replace(temporary, source)
    for relpath in manifest.deleted_paths:
        source = project_root / relpath
        if source.is_dir():
            shutil.rmtree(source)
        elif source.exists():
            source.unlink()
    restore_path = run_dir / "restore.json"
    restore_path.write_text(
        json.dumps({
            "files": restore,
            "deleted_paths": manifest.deleted_paths,
            "renamed_paths": manifest.renamed_paths,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "reverse.diff").write_text("".join(reverse_lines), encoding="utf-8")
    return ApplyResult(
        run_id=manifest.run_id,
        changed_paths=manifest.changed_paths,
        deleted_paths=manifest.deleted_paths,
        renamed_paths=manifest.renamed_paths,
        backup_root=str(backup_root),
        restore_manifest=str(restore_path),
    )
```

- [ ] **Step 4: Verify GREEN and commit**

```bash
python3 -m unittest tests.test_preview_apply -v
python3 -m unittest discover -s tests -v
git add skills/de-starter/scripts/destarter_lib/apply.py tests/test_preview_apply.py
git commit -m "feat: apply approved previews with recovery"
```

---

### Task 9: Expose the Full CLI Lifecycle

**Files:**
- Create: `skills/de-starter/scripts/destarter.py`
- Create: `tests/test_cli_e2e.py`

**Interfaces:**
- Consumes: all stable runtime functions.
- Produces: five CLI commands and their JSON/Markdown artifacts.

- [ ] **Step 1: Write a failing end-to-end CLI test**

Create `tests/test_cli_e2e.py` that uses `subprocess.run` against a copied fixture:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

from tests.support import REPO_ROOT, copy_fixture

CLI = REPO_ROOT / "skills" / "de-starter" / "scripts" / "destarter.py"


class CliEndToEndTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_discover_and_audit_write_expected_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = copy_fixture("nextjs-starter", base)
            run_dir = base / "run"
            discovered = self.run_cli("discover", "--project", str(root), "--run-dir", str(run_dir))
            self.assertEqual(discovered.returncode, 0, discovered.stderr)
            self.assertTrue((run_dir / "discovery.json").exists())
            source = base / "source.json"
            source.write_text(json.dumps({"source_terms": ["Northstar"]}), encoding="utf-8")
            audited = self.run_cli(
                "audit", "--project", str(root), "--run-dir", str(run_dir),
                "--source-config", str(source),
            )
            self.assertEqual(audited.returncode, 0, audited.stderr)
            self.assertTrue((run_dir / "audit.json").exists())
            self.assertTrue((run_dir / "audit.md").exists())

    def test_rejects_run_directory_inside_target_project(self) -> None:
        with TemporaryDirectory() as tmp:
            root = copy_fixture("nextjs-starter", Path(tmp))
            rejected = self.run_cli(
                "discover",
                "--project", str(root),
                "--run-dir", str(root / ".destarter"),
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse((root / ".destarter").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify RED**

```bash
python3 -m unittest tests.test_cli_e2e -v
```

Expected: Python cannot open `destarter.py`.

- [ ] **Step 3: Implement argparse commands and artifact loading**

Create `destarter.py` with:

```python
#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from destarter_lib.adapters import detect_project
from destarter_lib.apply import apply_preview
from destarter_lib.candidates import discover_candidates
from destarter_lib.decisions import load_decisions
from destarter_lib.files import iter_project_files
from destarter_lib.models import AuditResult, Finding, FileRecord, ProjectFacts, RiskLevel
from destarter_lib.preview import create_preview
from destarter_lib.report import audit_to_dict, write_audit_reports
from destarter_lib.scanner import scan_project


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_audit(path: Path) -> AuditResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    project = ProjectFacts(**payload["project"])
    files = [FileRecord(**item) for item in payload["files"]]
    findings = [
        Finding(**{**item, "risk": RiskLevel(item["risk"])})
        for item in payload["findings"]
    ]
    return AuditResult(project, payload["source_terms"], findings, files)


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
    root = args.project.resolve()
    run_dir = args.run_dir.resolve()
    try:
        run_dir.relative_to(root)
    except ValueError:
        pass
    else:
        raise SystemExit("run directory must be outside the target project")
    if args.command == "discover":
        payload = {
            "project": asdict(detect_project(root)),
            "candidates": [asdict(item) for item in discover_candidates(root)],
            "files": [asdict(item) for item in iter_project_files(root)],
        }
        _write(run_dir / "discovery.json", payload)
        print(run_dir / "discovery.json")
        return 0
    if args.command in {"audit", "verify"}:
        source = json.loads(args.source_config.read_text(encoding="utf-8"))
        audit = scan_project(root, source["source_terms"])
        target_dir = run_dir if args.command == "audit" else run_dir / "verification"
        write_audit_reports(audit, target_dir)
        print(target_dir / "audit.md")
        return 0
    audit = _load_audit(run_dir / "audit.json")
    if args.command == "preview":
        manifest = create_preview(root, run_dir, audit, load_decisions(args.decisions, audit))
        print(run_dir / "preview.diff")
        print(manifest.approval_token)
        return 0
    result = apply_preview(root, run_dir, args.approval_token)
    _write(run_dir / "apply-result.json", asdict(result))
    print(run_dir / "apply-result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run end-to-end and full tests**

```bash
python3 -m unittest tests.test_cli_e2e -v
python3 -m unittest discover -s tests -v
python3 skills/de-starter/scripts/destarter.py --help
```

Expected: all tests pass and help lists `discover`, `audit`, `preview`, `apply`, and `verify`.

- [ ] **Step 5: Commit the CLI**

```bash
git add skills/de-starter/scripts/destarter.py tests/test_cli_e2e.py
git commit -m "feat: expose de-starter audit lifecycle"
```

---

### Task 10: Write the Minimal Skill and Reference Contracts

**Files:**
- Replace: `skills/de-starter/SKILL.md`
- Create: `skills/de-starter/references/risk-rules.md`
- Create: `skills/de-starter/references/brand-profile.md`
- Create: `skills/de-starter/references/report-contract.md`

**Interfaces:**
- Consumes: exact baseline failures, CLI lifecycle, risk model, and report files.
- Produces: a concise Skill that causes an Agent to use the deterministic tool and stop at both approval gates.

- [ ] **Step 1: Convert baseline omissions into explicit behavioral requirements**

For each failed rubric item in `tests/skill/baseline/`, map it to one observable instruction:

```text
workspace edited early -> real target remains read-only until current preview approval
license included -> P0 never enters actions
brand invented -> require real profile or explicit placeholder choice
business identifier replaced -> P1 requires migration and rollback plans
demo deleted silently -> present P2 categories and record each user decision
```

- [ ] **Step 2: Replace the generated Skill with the complete workflow**

Use this frontmatter and structure:

```markdown
---
name: de-starter
description: Use when taking ownership of a starter, boilerplate, template, SaaS kit, or cloned codebase that may still contain source branding, demo content, sample assets, repository links, placeholder metadata, or risky business identifiers.
---

# De-starter

Safely convert a template-derived repository into an independently branded product. The real target stays read-only until the user approves the current preview diff.

## Required workflow

1. Set `SKILL_DIR` to this Skill folder and create a project-external run directory.
2. Run `python3 "$SKILL_DIR/scripts/destarter.py" discover ...`. Show the source-identity candidates and ask the user to confirm them.
3. Ask the user to choose either a complete real brand profile or neutral placeholders. Read `references/brand-profile.md`.
4. Run `audit` with confirmed source terms. Read `references/risk-rules.md`, present P0/P1 protections and P2 categories, and record the user's category choices. This is approval gate one.
5. Write a decisions JSON in the run directory. Never place P0 in actions. A P1 action requires explicit migration and rollback text.
6. Run `preview`. Show `audit.md`, `preview.diff`, binary changes, protected items, validation commands, and unresolved work. Stop. Do not run `apply` until the user explicitly approves this exact preview. This is approval gate two.
7. Immediately before `apply`, verify the user-approved token is from the current manifest. The tool rejects stale source hashes.
8. Run `apply`, execute the detected validation commands, then run `verify`. Report modifications, validation results, remaining findings, placeholders, backup location, and restore manifest.

## Non-negotiable stops

- Source identity is ambiguous.
- Real brand fields are incomplete and placeholders were not chosen.
- License obligations are unclear.
- The scanner, preview, hash check, backup, or redaction check fails.
- Files changed after preview.

Never replace these stops with direct edits or an ad hoc search-and-replace.

## Output contract

Read `references/report-contract.md`. Respond in the user's language. Keep secrets redacted and keep purchased source code or assets out of public examples.
```

- [ ] **Step 3: Add concise reference contracts**

Create `risk-rules.md`:

```markdown
# Risk Rules

Classify by location, surrounding syntax, persistence, and dependencies. A keyword alone never determines risk.

| Risk | Default | Examples |
| --- | --- | --- |
| P0 protected | Report and keep | LICENSE, copyright, notices, secrets, production data |
| P1 high risk | Keep unless migration and rollback are explicit | `starter_monthly`, payment IDs, database enums, auth keys, API routes, environment-variable names |
| P2 user decision | Present by category | Demo routes, sample assets, testimonials, example blogs, test data |
| P3 display residue | Eligible for preview | UI brand names, SEO, email signatures, repository links, package descriptions |

Precedence is P0, then P1, then P2, then P3. A payment key inside a Demo file remains P1. A source-author name inside LICENSE remains P0.

Never delete a path containing P0 or P1 findings. Treat generated files as derived: change their source and run the repository generator.
```

Create `brand-profile.md`:

```markdown
# Brand Profile

The user explicitly chooses one mode.

## Real brand

Require all fields: `product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, and `owner`. Pause when any field is missing.

## Neutral placeholders

Use exactly:

| Field | Value |
| --- | --- |
| product_name | Your Product |
| short_name | Your Product |
| url | https://example.com |
| domain | example.com |
| support_email | support@example.com |
| repository_url | https://github.com/your-org/your-product |
| owner | Your Company |

Generate `placeholders.json` and report every remaining placeholder after verification. Do not invent a production identity.
```

Create `report-contract.md`:

```markdown
# Report Contract

Present artifacts in this order:

1. Project kind, package manager, Git state, and validation commands.
2. Source-identity candidates with evidence and the confirmed source terms.
3. Findings grouped as P0, P1, P2, and P3.
4. The chosen P2 actions for Demo, sample content, testimonials, test data, and assets.
5. Protected, retained, ambiguous, and unresolved items.
6. `preview.md`, `preview.diff`, `binary-changes.json`, and `placeholders.json`.
7. Validation commands and restore strategy.
8. After apply: actual changes, command results, verification findings, backup location, reverse diff, and restore manifest.

Never include secret values, private source excerpts beyond the minimum evidence, or purchased code/assets in public examples. Respond in the user's language.
```

Each reference stays under 150 lines and does not repeat the full workflow.

- [ ] **Step 4: Validate structure and word count**

```bash
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
wc -w skills/de-starter/SKILL.md
rg -n 'README|CHANGELOG|tests/' skills/de-starter || true
```

Expected: validation passes, `SKILL.md` remains under 500 words, and no runtime instruction depends on root-only public documents.

- [ ] **Step 5: Commit the GREEN Skill**

```bash
git add skills/de-starter
git commit -m "feat: add de-starter approval workflow"
```

---

### Task 11: Forward-Test the Skill and Close Observed Loopholes

**Files:**
- Create: `tests/skill/forward/*.md`
- Modify: `skills/de-starter/SKILL.md` only when a forward test exposes a concrete loophole.
- Modify: reference files only when a forward test exposes a retrieval or application gap.

**Interfaces:**
- Consumes: Task 1 scenarios and the installed Skill path.
- Produces: raw forward-test evidence, rubric scores, and a Skill that passes all required behaviors.

- [ ] **Step 1: Run five no-guidance controls for the core approval wording**

Use five fresh subagent contexts with the `speed-over-safety` prompt and no Skill. Save outputs verbatim under `tests/skill/forward/control-01.md` through `control-05.md`.

Expected: record observed variance; do not infer compliance from a single sample.

- [ ] **Step 2: Run five Skill-enabled repetitions**

Use five fresh contexts with:

```text
Use $de-starter at $REPO_ROOT/skills/de-starter to handle this repository:
<exact speed-over-safety prompt>
```

Give each run a fresh copy of the synthetic Next.js fixture and a fresh run directory. Save raw outputs under `tests/skill/forward/skill-01.md` through `skill-05.md`.

Expected: all five preserve the real workspace, protect LICENSE, and stop at preview approval.

- [ ] **Step 3: Run the missing-brand and semantic-collision scenarios**

Run each exact scenario once in a fresh context with the Skill. Save outputs verbatim and score every rubric item.

Expected: both scenarios pass all listed requirements.

- [ ] **Step 4: Refactor only against observed failures**

If an Agent invents a brand, edits before approval, hides the diff, or treats a P1 key as display text, add the smallest explicit counter to `SKILL.md` and rerun the failing scenario five times. If output shape is wrong, tighten the positive report contract instead of adding a prohibition list.

- [ ] **Step 5: Validate and commit evaluation evidence**

```bash
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
python3 -m unittest discover -s tests -v
git add skills/de-starter tests/skill
git commit -m "test: forward-test de-starter workflow"
```

---

### Task 12: Add Public Documentation, CI, and Release Hygiene

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `.gitignore`
- Create: `.github/workflows/test.yml`
- Create: `examples/sanitized-report.md`

**Interfaces:**
- Consumes: stable CLI and tested Skill.
- Produces: a public, installable, testable GitHub repository without purchased Starter material.

- [ ] **Step 1: Write README with installation and usage**

Create this complete README:

```markdown
# de-starter

`de-starter` is an Agent Skill, not a standalone Agent. It helps an existing coding Agent audit and safely remove starter, boilerplate, template, and SaaS-kit residue.

The real workspace stays read-only until the user reviews and explicitly approves the current preview diff.

## Install

Requirements: Python 3.9+; runtime scripts use only the standard library.

```bash
git clone https://github.com/alisas-cell/de-starter.git
mkdir -p "$HOME/.agents/skills"
cp -R de-starter/skills/de-starter "$HOME/.agents/skills/de-starter"
```

The public repository is maintained at `alisas-cell/de-starter`.

## Use

```text
$de-starter Audit this repository and show the report and proposed diff before making changes.
```

The Skill discovers source identities, asks for a real brand or neutral placeholders, produces an audit, records Demo/sample decisions, generates a project-external preview, stops for approval, applies only the approved token, validates the project, and scans again.

## Risk levels

| Risk | Default |
| --- | --- |
| P0 legal/secrets/production data | Report and keep |
| P1 persisted/payment/auth/API identifiers | Keep unless migration and rollback are explicit |
| P2 Demo/sample/testimonial/test data/assets | User category decision |
| P3 display brand/SEO/email/repository metadata | Eligible for preview |

## Artifacts

Each run writes `audit.md`, `audit.json`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, `manifest.json`, backups, `reverse.diff`, and `restore.json` outside the target project. Git is optional; non-Git projects use hashes and verified backups.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/de-starter/scripts
```

## Contributing

Use synthetic fixtures. Never commit purchased Starter code, proprietary assets, secrets, production identifiers, or reports containing private source excerpts.

## License

MIT
```

The installation URL uses the approved public owner `alisas-cell`; it is not a runtime brand placeholder.

- [ ] **Step 2: Add repository license and changelog**

Create `LICENSE` using the standard MIT text beginning:

```text
MIT License

Copyright (c) 2026 de-starter contributors
```

and containing the unmodified MIT permission, condition, warranty, and liability paragraphs.

Create `CHANGELOG.md`:

```markdown
# Changelog

## 0.1.0 - 2026-07-20

- Added deterministic source-identity and residue scanning.
- Added P0–P3 contextual risk classification and secret redaction.
- Added mandatory audit-scope and preview-diff approval gates.
- Added project-external preview, hash validation, backups, reverse diff, and restore manifest.
- Added Node/Next.js detection plus safe generic fallback.
- Added baseline and forward evaluation for Skill behavior.
```

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.DS_Store
.coverage
.pytest_cache/
```

- [ ] **Step 3: Add CI**

Create `.github/workflows/test.yml`:

```yaml
name: test

on:
  push:
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m unittest discover -s tests -v
      - run: python -m compileall -q skills/de-starter/scripts
      - run: python skills/de-starter/scripts/destarter.py --help
```

- [ ] **Step 4: Generate a sanitized example from the fixture**

Run `discover` and `audit` against `tests/fixtures/nextjs-starter`, then copy only the Markdown report to `examples/sanitized-report.md`. Confirm it contains `Northstar` synthetic values and no local absolute home path.

- [ ] **Step 5: Verify public hygiene and commit**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/de-starter/scripts
: "${PRIVATE_SOURCE_PATTERN:?Set PRIVATE_SOURCE_PATTERN to the private source-identity regex}"
rg -n -i "${PRIVATE_SOURCE_PATTERN}|prod_[A-Za-z0-9]+" . \
  --glob '!docs/superpowers/specs/**' \
  --glob '!docs/superpowers/plans/**'
git diff --check
git add README.md LICENSE CHANGELOG.md .gitignore .github examples
git commit -m "docs: prepare de-starter for public release"
```

Expected: no private Starter names or live-looking payment IDs outside private design references; all tests pass.

---

### Task 13: Run the Private Acceptance Dry-Run

**Files:**
- Read only: `$TARGET_PROJECT`
- Create outside project: `$PRIVATE_RUN_ROOT.*`
- Do not create or modify files inside the Starter during this task.

**Interfaces:**
- Consumes: release-candidate Skill and CLI.
- Produces: private discovery, audit, category decisions, preview diff, and approval token.

- [ ] **Step 1: Create an external run directory and discover**

```bash
: "${REPO_ROOT:?Set REPO_ROOT to the de-starter repository root}"
: "${TARGET_PROJECT:?Set TARGET_PROJECT to the private target project}"
: "${PRIVATE_RUN_ROOT:?Set PRIVATE_RUN_ROOT to a disjoint external directory prefix}"
RUN_DIR="$(mktemp -d "${PRIVATE_RUN_ROOT%/}.XXXXXX")"
python3 "$REPO_ROOT/skills/de-starter/scripts/destarter.py" \
  discover \
  --project "$TARGET_PROJECT" \
  --run-dir "$RUN_DIR"
```

Expected: only `"$RUN_DIR/discovery.json"` is written; `$TARGET_PROJECT` remains unchanged.

- [ ] **Step 2: Present and confirm source identities**

Show detected candidates with evidence. Select unambiguous Starter identities using the approved risk rules; ask the user only when ownership is genuinely ambiguous. Do not treat dependency names or payment vendors as Starter identities.

Expected likely candidates from the preliminary read-only inspection include private source-identity variants, original repository ownership, and original promotional domains; the discovery output is authoritative.

- [ ] **Step 3: Collect the actual target brand mode**

Because the user delegated ordinary decisions and has not supplied a production brand, recommend and select the exact neutral-placeholder profile for this private acceptance run. Explain that real-brand mode remains available when all seven real-brand fields are supplied.

Write the confirmed source terms to `"$RUN_DIR/source.json"` and run `audit`.

- [ ] **Step 4: Present the private audit and stop at gate one**

Show:

- P0 MIT copyright protection,
- P1 payment IDs and `starter_monthly`/`starter_yearly`,
- P2 Demo routes, blog content, testimonials, tests, and roughly 2.5 MB of sample assets,
- P3 display branding, package metadata, README, emails, SEO, links, and translations.

Choose P2 categories using product utility: preserve working product capabilities, remove fabricated marketing proof and obsolete instructional content, and replace source-branded sample presentation. Present those recommendations plus the P3 scope as one gate-one approval. Do not modify the project.

- [ ] **Step 5: Generate decisions and preview**

Write only user-approved P2/P3 actions to `"$RUN_DIR/decisions.json"`. Keep P0 and P1 actions set to `keep`. Run:

```bash
python3 "$REPO_ROOT/skills/de-starter/scripts/destarter.py" \
  preview \
  --project "$TARGET_PROJECT" \
  --run-dir "$RUN_DIR" \
  --decisions "$RUN_DIR/decisions.json"
```

- [ ] **Step 6: Present the exact preview and stop at gate two**

Show `audit.md`, `preview.diff`, `binary-changes.json`, protected items, validation commands, unresolved items, backup plan, and approval token. Ask the user to approve, reject, or narrow this exact preview.

Do not proceed to Task 14 without an explicit approval message for the current preview.

---

### Task 14: Apply the Approved Starter Cleanup and Refine the Skill

**Files:**
- Modify only user-approved files under `$TARGET_PROJECT`.
- Modify Skill/tests only when the real run reveals a reproducible generic gap.
- Create: `examples/sanitized-real-run-summary.md` only from non-proprietary aggregate facts.

**Interfaces:**
- Consumes: explicit current-preview approval and unchanged source hashes.
- Produces: cleaned Starter, validation evidence, restore artifacts, second scan, and any generalized Skill fix.

- [ ] **Step 1: Apply only the approved token**

```bash
python3 "$REPO_ROOT/skills/de-starter/scripts/destarter.py" \
  apply \
  --project "$TARGET_PROJECT" \
  --run-dir "$RUN_DIR" \
  --approval-token "$APPROVED_TOKEN"
```

Expected: stale hashes abort; otherwise only manifest paths change and recovery artifacts remain in `"$RUN_DIR"`.

- [ ] **Step 2: Run Starter validation**

```bash
pnpm lint
pnpm test
pnpm build
```

Run from `$TARGET_PROJECT`. Expected: all commands exit 0, apart from already documented dynamic-route warnings that do not fail the build.

- [ ] **Step 3: Run the second residue scan**

```bash
python3 "$REPO_ROOT/skills/de-starter/scripts/destarter.py" \
  verify \
  --project "$TARGET_PROJECT" \
  --run-dir "$RUN_DIR" \
  --source-config "$RUN_DIR/source.json"
```

Expected: remaining hits are P0/P1 protected items or explicitly retained P2 items. Any unexpected P3 hit returns to a new audit/preview approval cycle.

- [ ] **Step 4: Preserve project invariants**

Verify manually from the diff and tests:

- both English and Chinese user-facing content changed together,
- auth and Google-provider UI remain aligned,
- credit ledger and balance flows are untouched,
- Creem product IDs and plan keys are untouched,
- demo assets are not replaced by remote runtime URLs,
- generated files are regenerated only through their repository scripts.

- [ ] **Step 5: Generalize only reproducible gaps**

For any generic miss, first add a failing synthetic test, then make the minimal scanner or Skill change, rerun all tests, and rerun the affected private audit step. Do not add a rule containing a private source identity or path.

- [ ] **Step 6: Commit repository changes separately**

In `de-starter`:

```bash
git add skills tests examples
git commit -m "fix: incorporate real-world de-starter findings"
```

For `$TARGET_PROJECT`, create a Git repository or commit only if the user explicitly requests it; do not assume the target contains `.git`.

---

### Task 15: Complete Release Verification and Request GitHub Publication Authority

**Files:**
- Modify: release documentation only if verification reveals an exact mismatch.
- Do not create a remote repository without the user's final visibility and account confirmation.

**Interfaces:**
- Consumes: passing public tests, passing private acceptance, and a clean `de-starter` worktree.
- Produces: signed-off local `v0.1.0` release candidate and a precise GitHub publication request.

- [ ] **Step 1: Run all local release gates**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/de-starter/scripts
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
python3 skills/de-starter/scripts/destarter.py --help
git diff --check
git status --short
```

Expected: tests and validation pass; the worktree is clean.

- [ ] **Step 2: Verify distributable folder contents**

```bash
find skills/de-starter -maxdepth 3 -type f | sort
: "${PRIVATE_SOURCE_PATTERN:?Set PRIVATE_SOURCE_PATTERN to the private source-identity regex}"
rg -n -i "${PRIVATE_SOURCE_PATTERN}|live-secret|prod_[A-Za-z0-9]+" \
  skills tests examples README.md CHANGELOG.md
```

Expected: the Skill folder contains only `SKILL.md`, `agents/openai.yaml`, runtime scripts, and references; no private brand, secret, or production ID appears.

- [ ] **Step 3: Create the local release tag after final verification**

```bash
git tag -a v0.1.0 -m "de-starter v0.1.0"
git show --stat --oneline v0.1.0
```

Expected: tag points at the verified release commit.

- [ ] **Step 4: Ask for GitHub publication details**

Request the authenticated GitHub account/organization, repository visibility, and confirmation that `de-starter` is the desired repository name. After explicit confirmation, create or attach the remote and push `main` plus `v0.1.0`.

Do not guess the account, visibility, or overwrite an existing remote.

---

## Plan Self-Review Checklist

- [x] Every design goal maps to at least one task.
- [x] Every runtime module is introduced by a failing test.
- [x] Skill behavior is baseline-tested before `SKILL.md` guidance is authored.
- [x] Function names and CLI arguments match the Runtime Interfaces section.
- [x] Both approval gates occur before the private target is modified.
- [x] P0, P1, P2, secret redaction, Git/non-Git, restore, stale-source, and placeholder behaviors have tests.
- [x] Public fixtures contain only synthetic names and assets.
- [x] GitHub publication remains behind an explicit external-state confirmation.
