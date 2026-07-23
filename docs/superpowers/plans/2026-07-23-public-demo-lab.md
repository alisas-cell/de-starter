# Public Demo Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a synthetic, reproducible public demo that proves de-starter's approved-change behavior and fail-closed safety without publishing purchased Starter source or bypassing human approval.

**Architecture:** Keep the published cleanup engine unchanged. Add a standard-library Python helper that creates and validates only sentinel-owned disposable demo workspaces, a committed synthetic Next.js-like seed and transparent example decisions, acceptance tests that invoke the real CLI, and beginner-facing documentation/media. The public walkthrough remains staged at both approval gates and never auto-extracts or auto-submits a preview token.

**Tech Stack:** Python 3.9+ standard library, `unittest`, the existing `skills/de-starter/scripts/destarter.py` CLI, Markdown, GitHub Actions.

## Global Constraints

- Never publish or reconstruct purchased Starter source, private paths, credentials, usable approval tokens, or private diff excerpts.
- Keep the cleanup engine under `skills/de-starter` unchanged unless a failing public-demo test reveals a genuine general defect.
- Require macOS/Linux POSIX behavior already declared by v0.1.1; do not claim Windows support.
- Do not automate user approval, preview-token extraction, or `apply` in one unattended quick-start command.
- Describe v0.1.1 accurately: transactional rollback on failed apply plus external byte backup and recovery evidence; no user-facing one-command restore operation.
- State that risk is reduced, not zero; require Git or a verified backup, both approval reviews, preserved run artifacts, and post-apply validation.
- Use only fictional `Northstar Labs` data and neutral placeholders in the public demo.
- Use test-first development for every helper behavior and safety regression.

## File map

- Create `examples/public-demo/demo.py`: sentinel-bound prepare, inventory, tamper, check, and reset commands for disposable workspaces.
- Create `examples/public-demo/README.md`: five-minute staged walkthrough and refusal exercises.
- Create `examples/public-demo/source-config.example.json`: fixed fictional source-term proposal that the learner explicitly reviews and copies.
- Create `examples/public-demo/decisions.example.json`: exact, valid decisions for the fixed seed; the learner explicitly reviews and copies after audit.
- Create `examples/public-demo/seed/**`: synthetic project evidence for P0/P1/P2/P3 and path residue.
- Create `tests/test_public_demo.py`: helper boundary, real CLI lifecycle, refusal, invariant, and privacy tests.
- Modify `README.md`: public demo entry point and safety boundary.
- Modify `docs/self-media-package.zh-CN.md`: continuous public-demo narration, claims, and screen directions.
- Modify `docs/video-shot-list.zh-CN.md`: new demo capture sequence.
- Modify `docs/video-production-log.zh-CN.md`: implementation and safety-test record.
- Create `docs/assets/video/08-public-demo-safety.png` and its HTML source: redacted 1600×900 demo evidence card.

---

### Task 1: Sentinel-owned disposable workspace

**Files:**
- Create: `tests/test_public_demo.py`
- Create: `examples/public-demo/demo.py`
- Create: `examples/public-demo/seed/LICENSE`
- Create: `examples/public-demo/seed/.env.example`
- Create: `examples/public-demo/seed/app/demo/page.tsx`
- Create: `examples/public-demo/seed/app/page.tsx`
- Create: `examples/public-demo/seed/messages/en.json`
- Create: `examples/public-demo/seed/package.json`
- Create: `examples/public-demo/seed/public/starter-logo.svg`

**Interfaces:**
- Produces: `prepare_workspace(workspace: Path) -> dict`, `inventory_project(workspace: Path) -> dict`, `require_owned_workspace(workspace: Path) -> dict`, and `reset_workspace(workspace: Path) -> None`.
- Produces CLI commands: `prepare --workspace PATH`, `inventory --workspace PATH`, and `reset --workspace PATH`.
- Creates: `PATH/project`, `PATH/run`, `PATH/project/public/starter`, `PATH/project/public/uploads`, `PATH/.de-starter-public-demo.json`, and `PATH/baseline-inventory.json`.

- [ ] **Step 1: Write the failing preparation and boundary tests**

Add tests that load `demo.py` with `importlib.util`, then exercise only temporary paths:

```python
class PublicDemoWorkspaceTests(unittest.TestCase):
    def test_prepare_creates_owned_disjoint_demo_and_expected_empty_directories(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            result = DEMO.prepare_workspace(workspace)
            self.assertEqual(Path(result["project"]), workspace / "project")
            self.assertEqual(Path(result["run_dir"]), workspace / "run")
            self.assertTrue((workspace / "project" / "public" / "starter").is_dir())
            self.assertTrue((workspace / "project" / "public" / "uploads").is_dir())
            self.assertTrue((workspace / ".de-starter-public-demo.json").is_file())
            self.assertTrue((workspace / "baseline-inventory.json").is_file())

    def test_prepare_refuses_nonempty_unowned_destination(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            workspace.mkdir()
            (workspace / "foreign.txt").write_text("keep\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "empty|owned"):
                DEMO.prepare_workspace(workspace)
            self.assertEqual((workspace / "foreign.txt").read_text(), "keep\n")

    def test_reset_requires_exact_sentinel_and_keeps_unowned_directory(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "lab"
            workspace.mkdir()
            (workspace / "foreign.txt").write_text("keep\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sentinel"):
                DEMO.reset_workspace(workspace)
            self.assertTrue(workspace.is_dir())
```

- [ ] **Step 2: Run the focused tests and observe RED**

Run: `python3 -m unittest tests.test_public_demo.PublicDemoWorkspaceTests -v`

Expected: import or attribute failure because `examples/public-demo/demo.py` does not exist.

- [ ] **Step 3: Add the exact synthetic seed**

Use these evidence-bearing values:

```text
LICENSE: Copyright (c) 2026 Northstar Labs
.env.example: NEXT_PUBLIC_APP_NAME="Northstar Starter"
messages/en.json brand: Northstar Starter
messages/en.json plan: starter_monthly
messages/en.json support: hello@northstar.example
package.json name: northstar-starter
package.json author: Northstar Labs
package.json repository: https://github.com/northstar-labs/northstar-starter
app/demo/page.tsx: a local Northstar Starter demonstration component
app/page.tsx: a working page that imports no deleted demo component
public/starter-logo.svg: a small text-only synthetic SVG titled Northstar Starter
```

The seed contains no real dependency installation, proprietary asset, secret, or real external service.

- [ ] **Step 4: Implement minimal sentinel-bound helper behavior**

Use a versioned sentinel and exclude the sentinel/run artifacts from project inventory:

```python
SENTINEL = ".de-starter-public-demo.json"
SENTINEL_PAYLOAD = {"kind": "de-starter-public-demo", "version": 1}

def require_owned_workspace(workspace: Path) -> dict:
    root = workspace.expanduser().resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError("refusing unsafe workspace root")
    marker = root / SENTINEL
    if not marker.is_file():
        raise ValueError("public demo sentinel is missing")
    payload = json.loads(marker.read_text(encoding="utf-8"))
    if payload != SENTINEL_PAYLOAD:
        raise ValueError("public demo sentinel is invalid")
    return {"workspace": root, "project": root / "project", "run_dir": root / "run"}

def inventory_project(workspace: Path) -> dict:
    owned = require_owned_workspace(workspace)
    project = owned["project"]
    files = {
        path.relative_to(project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project.rglob("*")) if path.is_file() and not path.is_symlink()
    }
    directories = [
        path.relative_to(project).as_posix()
        for path in sorted(project.rglob("*")) if path.is_dir() and not path.is_symlink()
    ]
    return {"files": files, "directories": directories}
```

`prepare_workspace` must accept only an absent or empty destination, copy the committed seed, create the two empty directories, write the sentinel atomically, and record the baseline inventory. `reset_workspace` must call `require_owned_workspace`, verify that `project` and `run` are direct children, and then remove only the resolved workspace.

- [ ] **Step 5: Run focused tests and helper smoke commands**

Run:

```bash
python3 -m unittest tests.test_public_demo.PublicDemoWorkspaceTests -v
python3 examples/public-demo/demo.py prepare --workspace /tmp/de-starter-public-demo-plan
python3 examples/public-demo/demo.py inventory --workspace /tmp/de-starter-public-demo-plan
python3 examples/public-demo/demo.py reset --workspace /tmp/de-starter-public-demo-plan
```

Expected: workspace tests pass; inventory is JSON; reset removes only `/tmp/de-starter-public-demo-plan`.

- [ ] **Step 6: Commit the independently testable workspace helper**

```bash
git add examples/public-demo/demo.py examples/public-demo/seed tests/test_public_demo.py
git commit -m "feat: add sentinel-owned public demo workspace"
```

---

### Task 2: Transparent decisions and successful real-CLI lifecycle

**Files:**
- Create: `examples/public-demo/source-config.example.json`
- Create: `examples/public-demo/decisions.example.json`
- Modify: `tests/test_public_demo.py`
- Modify: `examples/public-demo/demo.py`

**Interfaces:**
- Consumes: Task 1 `prepare_workspace`, `inventory_project`, and the real `destarter.py` CLI.
- Produces: `check_applied(workspace: Path) -> dict` and CLI command `check --workspace PATH`.
- Produces fixed example JSON whose finding IDs must match an audit of the committed seed; no runtime decision generation.

- [ ] **Step 1: Write failing lifecycle and invariant tests**

The test must run `discover`, copy the reviewed example source config, run `audit`, assert every committed decision ID exists, run `preview`, apply the exact token, and run `verify`:

```python
CLI = REPO_ROOT / "skills" / "de-starter" / "scripts" / "destarter.py"
SOURCE_EXAMPLE = REPO_ROOT / "examples" / "public-demo" / "source-config.example.json"
DECISIONS_EXAMPLE = REPO_ROOT / "examples" / "public-demo" / "decisions.example.json"

class PublicDemoLifecycleTests(unittest.TestCase):
    def run_cli(self, *args, expected=None):
        result = subprocess.run(
            [sys.executable, str(CLI), *args], text=True,
            capture_output=True, check=False,
        )
        if expected is not None:
            self.assertEqual(result.returncode, expected, result.stderr)
        return result

def test_documented_success_lifecycle_changes_only_approved_scope(self):
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "lab"
        DEMO.prepare_workspace(workspace)
        project, run = workspace / "project", workspace / "run"
        before = DEMO.inventory_project(workspace)
        self.run_cli("discover", "--project", str(project), "--run-dir", str(run), expected=0)
        shutil.copy2(SOURCE_EXAMPLE, run / "source-config.json")
        self.run_cli("audit", "--project", str(project), "--run-dir", str(run),
                     "--source-config", str(run / "source-config.json"), expected=0)
        decisions = json.loads(DECISIONS_EXAMPLE.read_text(encoding="utf-8"))
        audit = json.loads((run / "audit.json").read_text(encoding="utf-8"))
        ids = {item["finding_id"] for item in audit["findings"]}
        self.assertTrue({item["finding_id"] for item in decisions["actions"]} <= ids)
        shutil.copy2(DECISIONS_EXAMPLE, run / "decisions.json")
        preview = self.run_cli("preview", "--project", str(project), "--run-dir", str(run),
                               "--decisions", str(run / "decisions.json"), expected=0)
        token = preview.stdout.strip().splitlines()[-1]
        self.run_cli("apply", "--project", str(project), "--run-dir", str(run),
                     "--approval-token", token, expected=0)
        self.run_cli("verify", "--project", str(project), "--run-dir", str(run),
                     "--source-config", str(run / "source-config.json"), expected=3)
        result = DEMO.check_applied(workspace)
        self.assertEqual(result["status"], "approved-scope-verified")
        self.assertNotEqual(DEMO.inventory_project(workspace), before)
```

Add a separate test asserting `LICENSE` and `starter_monthly` bytes/values remain unchanged, `public/uploads` remains, `public/starter` is gone, the approved P2 route is gone, the approved asset rename exists, neutral P3 values exist, and `backup`, `restore.json`, `reverse.diff`, and `apply-result.json` exist only in the external run directory.

- [ ] **Step 2: Run the lifecycle tests and observe RED**

Run: `python3 -m unittest tests.test_public_demo.PublicDemoLifecycleTests -v`

Expected: failure because example JSON and `check_applied` are absent.

- [ ] **Step 3: Audit the fixed seed and commit exact example inputs**

Run the real CLI against a Task 1 disposable workspace. Commit:

```json
{"source_terms":["Northstar","starter"]}
```

Generate `decisions.example.json` once during implementation from the immutable seed audit with this checked selector script. The resulting committed file contains only concrete `F-...` IDs; this generator is not committed or exposed as a runtime command:

```python
from pathlib import Path
import json

audit = json.loads(Path("/tmp/de-starter-public-demo-plan/run/audit.json").read_text(encoding="utf-8"))

def one(relpath, evidence_fragment):
    matches = [
        item for item in audit["findings"]
        if item["risk"] == "P3"
        and item["relpath"] == relpath
        and evidence_fragment in item["evidence"]
    ]
    if len(matches) != 1:
        raise SystemExit("expected exactly one fixed-seed match for %s %s, got %d" % (
            relpath, evidence_fragment, len(matches),
        ))
    return matches[0]["finding_id"]

payload = {
    "brand_mode": "placeholder",
    "brand_profile": {},
    "actions": [
        {"finding_id": one("messages/en.json", '"brand"'), "action": "replace", "replacement": "Your Product"},
        {"finding_id": one("messages/en.json", '"support"'), "action": "replace", "replacement": "support@example.com"},
        {"finding_id": one("package.json", '"name"'), "action": "replace", "replacement": "your-product"},
        {"finding_id": one("package.json", '"author"'), "action": "replace", "replacement": "Your Company"},
        {"finding_id": one("package.json", '"repository"'), "action": "replace", "replacement": "https://github.com/your-org/your-product"},
    ],
    "delete_paths": ["app/demo"],
    "rename_paths": {"public/starter-logo.svg": "public/product-logo.svg"},
    "text_edits": [],
    "cleanup_empty_dirs": ["public/starter"],
}
print(json.dumps(payload, indent=2))
```

Inspect the emitted JSON, then add those concrete values with `apply_patch`. The lifecycle test rejects any stale ID. Do not add P0 or P1 actions.

- [ ] **Step 4: Implement post-apply invariant checking**

`check_applied` must require the sentinel and validate the committed public contract:

```python
def check_applied(workspace: Path) -> dict:
    owned = require_owned_workspace(workspace)
    project, run = owned["project"], owned["run_dir"]
    errors = []
    if (project / "LICENSE").read_text(encoding="utf-8") != (SEED / "LICENSE").read_text(encoding="utf-8"):
        errors.append("LICENSE changed")
    messages = json.loads((project / "messages/en.json").read_text(encoding="utf-8"))
    if messages.get("plan") != "starter_monthly":
        errors.append("retained P1 plan key changed")
    if messages.get("brand") != "Your Product" or messages.get("support") != "support@example.com":
        errors.append("neutral display placeholders are missing")
    if (project / "app/demo").exists():
        errors.append("approved P2 demo path remains")
    if (project / "public/starter").exists() or not (project / "public/uploads").is_dir():
        errors.append("empty-directory scope is incorrect")
    for artifact in ("backup", "restore.json", "reverse.diff", "apply-result.json"):
        if not (run / artifact).exists():
            errors.append("missing external recovery artifact: " + artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return {"status": "approved-scope-verified", "checks": 8}
```

- [ ] **Step 5: Run focused lifecycle tests and the full existing suite**

Run:

```bash
python3 -m unittest tests.test_public_demo.PublicDemoLifecycleTests -v
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

Expected: focused lifecycle tests pass; full suite increases from 195 tests with zero failures or warnings.

- [ ] **Step 6: Commit the successful lifecycle**

```bash
git add examples/public-demo/source-config.example.json examples/public-demo/decisions.example.json examples/public-demo/demo.py tests/test_public_demo.py
git commit -m "test: prove public demo approved lifecycle"
```

---

### Task 3: Wrong-token and stale-preview refusal exercises

**Files:**
- Modify: `tests/test_public_demo.py`
- Modify: `examples/public-demo/demo.py`

**Interfaces:**
- Consumes: Task 1 inventory and Task 2 fixed lifecycle inputs.
- Produces: `tamper_previewed_project(workspace: Path) -> Path` and CLI command `tamper --workspace PATH`.
- Produces no arbitrary-path mutation API; tamper target is fixed to sentinel-owned `project/messages/en.json`.

- [ ] **Step 1: Write failing refusal tests**

```python
def prepare_preview(self):
    temp = TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    workspace = Path(temp.name) / "lab"
    DEMO.prepare_workspace(workspace)
    project, run = workspace / "project", workspace / "run"
    self.run_cli("discover", "--project", str(project), "--run-dir", str(run), expected=0)
    shutil.copy2(SOURCE_EXAMPLE, run / "source-config.json")
    self.run_cli("audit", "--project", str(project), "--run-dir", str(run),
                 "--source-config", str(run / "source-config.json"), expected=0)
    shutil.copy2(DECISIONS_EXAMPLE, run / "decisions.json")
    preview = self.run_cli("preview", "--project", str(project), "--run-dir", str(run),
                           "--decisions", str(run / "decisions.json"), expected=0)
    return workspace, project, run, preview.stdout.strip().splitlines()[-1]

def test_wrong_token_rejects_before_any_project_write(self):
    workspace, project, run, valid_token = self.prepare_preview()
    before = DEMO.inventory_project(workspace)
    result = self.run_cli("apply", "--project", str(project), "--run-dir", str(run),
                          "--approval-token", "intentionally-wrong-demo-token")
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("approval", result.stderr.lower())
    self.assertEqual(DEMO.inventory_project(workspace), before)
    self.assertFalse((run / "apply-result.json").exists())

def test_stale_preview_rejects_before_partial_approved_edits(self):
    workspace, project, run, valid_token = self.prepare_preview()
    tampered = DEMO.tamper_previewed_project(workspace)
    tampered_bytes = tampered.read_bytes()
    result = self.run_cli("apply", "--project", str(project), "--run-dir", str(run),
                          "--approval-token", valid_token)
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(tampered.read_bytes(), tampered_bytes)
    self.assertTrue((project / "app/demo").is_dir())
    self.assertTrue((project / "public/starter").is_dir())
    self.assertFalse((run / "apply-result.json").exists())
```

Also test that `tamper_previewed_project` refuses an unowned directory and leaves its files unchanged.

- [ ] **Step 2: Run refusal tests and observe RED**

Run: `python3 -m unittest tests.test_public_demo.PublicDemoRefusalTests -v`

Expected: attribute failure because `tamper_previewed_project` is absent; wrong-token test may already pass and provides the baseline safety evidence.

- [ ] **Step 3: Implement the minimal fixed-target tamper helper**

```python
def tamper_previewed_project(workspace: Path) -> Path:
    owned = require_owned_workspace(workspace)
    target = owned["project"] / "messages" / "en.json"
    if not target.is_file() or target.is_symlink():
        raise ValueError("expected demo message file is missing")
    target.write_bytes(target.read_bytes() + b"\n")
    return target
```

The CLI help must label this as an intentional disposable-demo safety exercise.

- [ ] **Step 4: Run refusal tests and full regression tests**

Run:

```bash
python3 -m unittest tests.test_public_demo.PublicDemoRefusalTests -v
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

Expected: all refusal tests and the enlarged full suite pass; failed applies create no partial approved changes.

- [ ] **Step 5: Commit refusal evidence**

```bash
git add examples/public-demo/demo.py tests/test_public_demo.py
git commit -m "test: demonstrate token and stale-preview refusal"
```

---

### Task 4: Beginner walkthrough and safety boundary

**Files:**
- Create: `examples/public-demo/README.md`
- Modify: `README.md`
- Modify: `tests/test_public_demo.py`

**Interfaces:**
- Consumes: Tasks 1–3 CLI commands and exact example JSON.
- Produces: a copy-paste walkthrough that pauses before `preview` and `apply` and never exposes a real token.

- [ ] **Step 1: Add failing documentation-contract tests**

Read both Markdown files and assert they contain:

```python
required_demo_phrases = (
    "Risk is reduced, not zero",
    "Git or a verified backup",
    "review the private preview.diff",
    "paste the exact token yourself",
    "exit code 3 is expected",
    "no one-command restore",
)
for phrase in required_demo_phrases:
    self.assertIn(phrase, demo_readme)
self.assertNotRegex(demo_readme, r"approval-token\s+[0-9a-f]{64}")
self.assertNotIn("$(python", demo_readme)
```

Also assert root `README.md` links to `examples/public-demo/README.md` and contains the low-risk/non-zero boundary.

- [ ] **Step 2: Run documentation-contract tests and observe RED**

Run: `python3 -m unittest tests.test_public_demo.PublicDemoDocumentationTests -v`

Expected: missing-file or missing-phrase failures.

- [ ] **Step 3: Write the staged five-minute walkthrough**

Document exactly these phases:

1. prepare `/tmp/de-starter-public-demo`;
2. inspect sentinel-created paths;
3. run `discover`;
4. review and copy `source-config.example.json`, then run `audit`;
5. review `audit.md` and `decisions.example.json`, then copy decisions;
6. run `preview`, review every listed artifact and the local private diff;
7. optionally run wrong-token and stale-preview refusal exercises on separate fresh prepares;
8. paste the current token manually into `apply`;
9. run `verify` and explain expected exit code 3;
10. run `check`, inspect recovery evidence, and reset only the disposable workspace.

Use shell variables only for paths. Never use command substitution to extract a token or automatically chain preview to apply.

- [ ] **Step 4: Add root README public-demo and safety sections**

Place the demo link after `Use`. Include this exact meaning in plain English:

```text
Risk is reduced, not zero. Run de-starter only in Git or with a verified backup, review both approval gates, keep the external run directory, and validate after apply. A wrong decision that the user explicitly approves can still produce an unwanted change.
```

State that the public demo is synthetic and never contains the purchased Starter.

- [ ] **Step 5: Run docs tests and link checks**

Run:

```bash
python3 -m unittest tests.test_public_demo.PublicDemoDocumentationTests -v
python3 - <<'PY'
from pathlib import Path
import re
root = Path('.')
bad = []
for md in root.rglob('*.md'):
    for target in re.findall(r'\[[^]]+\]\(([^)]+)\)', md.read_text(encoding='utf-8')):
        if '://' not in target and not target.startswith('#'):
            path = (md.parent / target.split('#', 1)[0]).resolve()
            if not path.exists(): bad.append((str(md), target))
assert not bad, bad
print('Markdown links OK')
PY
```

Expected: documentation tests pass; `Markdown links OK`.

- [ ] **Step 6: Commit the public walkthrough**

```bash
git add README.md examples/public-demo/README.md tests/test_public_demo.py
git commit -m "docs: add reproducible public demo walkthrough"
```

---

### Task 5: Chinese video narrative and redacted visual evidence

**Files:**
- Modify: `docs/self-media-package.zh-CN.md`
- Modify: `docs/video-shot-list.zh-CN.md`
- Modify: `docs/video-production-log.zh-CN.md`
- Create: `docs/assets/video/sources/08-public-demo-safety.html`
- Create: `docs/assets/video/08-public-demo-safety.png`
- Modify: `tests/test_public_demo.py`

**Interfaces:**
- Consumes: verified Task 3 refusal and Task 4 walkthrough results.
- Produces: a 1600×900 evidence card and a continuous filming segment using only fictional paths and redacted token text.

- [ ] **Step 1: Add failing media-contract tests**

Assert the three Chinese documents mention `公开合成演示`, `错误令牌`, `过期预览`, `低风险不等于零风险`, and `没有一键恢复命令`. Assert the HTML contains `REDACTED`, does not contain a 64-hex token, private workspace prefixes, or purchased source terms. Validate the PNG dimensions after generation.

- [ ] **Step 2: Run media-contract tests and observe RED**

Run: `python3 -m unittest tests.test_public_demo.PublicDemoMediaTests -v`

Expected: missing content and missing image failures.

- [ ] **Step 3: Update the Chinese production materials**

Add a continuous segment that tells viewers:

- this is a synthetic public project, not the purchased Starter;
- the same released CLI is executing the demo;
- wrong token and stale preview stop before partial approved changes;
- a user-approved wrong decision is still possible, so review and Git/backup remain mandatory;
- transaction failure rollback and recovery evidence exist, but v0.1.1 has no one-command restore.

Add exact screen directions for audit, decision file, redacted preview token, refusal outputs, applied check, and external recovery artifacts.

- [ ] **Step 4: Create and render the 16:9 evidence card**

The HTML should show this evidence chain without a usable token or absolute path:

```text
Synthetic project prepared
Wrong token → REJECTED → project inventory unchanged
Stale preview → REJECTED → no partial approved edits
Exact reviewed token → approved scope applied
P0 LICENSE kept · P1 plan key kept · ordinary empty directory kept
External backup · restore.json · reverse.diff present
```

Render at 1600×900 using the existing repository screenshot process, then visually inspect the PNG.

On macOS, the deterministic render command is:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --window-size=1600,900 --screenshot="$PWD/docs/assets/video/08-public-demo-safety.png" "file://$PWD/docs/assets/video/sources/08-public-demo-safety.html"
```

Inspect the result with the available local image viewer before accepting it.

- [ ] **Step 5: Run media tests and privacy scan**

Run:

```bash
python3 -m unittest tests.test_public_demo.PublicDemoMediaTests -v
rg -n '/(Users|home)/|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{20,}|approval-token[[:space:]]+[0-9a-f]{64}' examples/public-demo docs/assets/video/sources/08-public-demo-safety.html docs/self-media-package.zh-CN.md docs/video-shot-list.zh-CN.md docs/video-production-log.zh-CN.md
```

Expected: media tests pass; privacy `rg` exits 1 with no matches.

- [ ] **Step 6: Commit the video materials**

```bash
git add docs/self-media-package.zh-CN.md docs/video-shot-list.zh-CN.md docs/video-production-log.zh-CN.md docs/assets/video/sources/08-public-demo-safety.html docs/assets/video/08-public-demo-safety.png tests/test_public_demo.py
git commit -m "docs: capture public demo safety evidence"
```

---

### Task 6: Release-grade verification and GitHub publication

**Files:**
- Modify: `CHANGELOG.md`
- Modify: version-facing release notes only if the verified change warrants a new patch tag.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: fresh local evidence, clean-clone evidence, a pushed main commit, and green GitHub Actions before any release claim.

- [ ] **Step 1: Run the complete local verification matrix**

Run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/de-starter-demo-pyc python3 -m compileall -q skills/de-starter/scripts examples/public-demo
git diff --check
```

Expected: Skill valid; the enlarged suite passes with zero warnings; compile and diff checks exit 0.

- [ ] **Step 2: Run public privacy, links, JSON, and image checks**

Validate all new JSON with `json.load`, all local Markdown links, all eight PNG dimensions as 1600×900, and privacy patterns across tracked files. The privacy scan must have zero matches for machine paths, private key headers, common GitHub/OpenAI token formats, exact approval tokens, and known private Starter identifiers.

- [ ] **Step 3: Run a fresh-clone public demo rehearsal**

Clone the candidate commit to `/tmp/de-starter-public-demo-clean`, execute the documented prepare/discover/audit/preview steps, manually use the current token for this disposable rehearsal, apply, verify with expected exit code 3, run `check`, and reset. Then run the full test suite in the clean clone.

Expected: the walkthrough matches the documentation; approved-scope check passes; full tests pass.

- [ ] **Step 4: Update changelog with exact verified claims**

Record the synthetic demo, refusal exercises, safety boundary, and final test count. Do not describe the core cleanup engine as changed if only examples/tests/docs changed.

- [ ] **Step 5: Commit final release metadata**

```bash
git add CHANGELOG.md
git commit -m "docs: record public demo release evidence"
```

- [ ] **Step 6: Push and wait for public CI**

Push the current branch/main using the existing GitHub workflow. Verify every Python 3.9, 3.11, and 3.13 job is green. If CI exposes a new cross-platform issue, follow systematic debugging and TDD before changing code.

- [ ] **Step 7: Publish without rewriting immutable tags**

If a release tag is appropriate, create the next immutable patch release rather than moving `v0.1.1`. Mark it Latest only after its tag CI is green. If the changes remain documentation/examples only, keep `v0.1.1` as the Skill runtime release and present the public demo from main without inventing a runtime version change.

- [ ] **Step 8: Final evidence handoff**

Report repository and demo links, exact test totals, CI matrix, refusal results, fresh-clone rehearsal, privacy boundary, and the honest non-zero-risk statement. Link the local Chinese production package, shot list, log, and eighth screenshot.
