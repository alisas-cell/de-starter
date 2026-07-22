# Protected Semantic Edits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic, hash-bound line-range semantic edits to de-starter, finish the private Starter acceptance run, and publish sanitized written and visual evidence for a beginner-friendly GitHub and video release.

**Architecture:** Extend `decisions.json` with explicit text-edit records tied to audited file hashes. Validate protected boundaries before preview, materialize edits only in the external preview tree, and bind safe intent metadata plus resulting bytes into the existing approval token. Reuse the descriptor-owned apply transaction, then create separate private evidence and public sanitized media.

**Tech Stack:** Python 3.9+ standard library, `unittest`, Markdown/JSON, Git, headless Chrome for 16:9 documentation PNGs, and pnpm/Next.js validation for the private target.

## Global Constraints

- Never modify `/Users/alisa/Documents/starter` before approval of the exact current preview diff and token.
- Never commit private Starter names, paths, source excerpts, assets, secrets, live-looking IDs, or approval tokens.
- P0 is immutable. P1 still needs a finding replacement with explicit migration and rollback plans.
- Semantic edits are UTF-8, one-based inclusive line ranges; no insert-only mode, binary editing, or fuzzy patching in v0.1.
- Bind every edit to the audited SHA-256; reject overlap with another edit, P0/P1 lines, or finding replacements.
- Preserve external preview, stale-source checks, backup, rollback, restore, and exact-token approval.
- Capture private and public-safe screenshots when each milestone occurs.
- Public content emphasizes 60% capability/value, 25% sanitized real effect, 10% use, and 5% learning reflection.
- Use TDD for runtime behavior and run the full public suite before completion claims.

## File Map

- Modify `models.py`, `decisions.py`, `preview.py`, `apply.py`, and `destarter.py` for semantic edits.
- Modify `SKILL.md`, `references/input-files.md`, `references/report-contract.md`, and `README.md` for the workflow contract.
- Modify `tests/test_decisions.py`, `tests/test_preview_apply.py`, and `tests/test_cli_e2e.py` for runtime coverage.
- Create `docs/video-shot-list.zh-CN.md`, `docs/video-kit.zh-CN.md`, `docs/assets/video/sources/*.html`, `docs/assets/video/*.png`, and `examples/sanitized-real-run-summary.md`.
- Create only outside Git: `$RUN/effect-audit-private.md` and `$RUN/screenshots/private/*.png`.

---

### Task 1: Parse and Protect Semantic Edit Decisions

**Files:**
- Modify: `skills/de-starter/scripts/destarter_lib/models.py`
- Modify: `skills/de-starter/scripts/destarter_lib/decisions.py`
- Test: `tests/test_decisions.py`

**Interfaces:**
- Consumes: `AuditResult.files`, `AuditResult.findings`, `DecisionAction`, and invariant-path rules.
- Produces: `TextEdit` and `load_decisions(path, audit, project_root=None) -> DecisionSet` with `DecisionSet.text_edits`.

- [ ] **Step 1: Write a failing valid-edit/hash test**

```python
def test_text_edit_requires_matching_audited_hash_and_current_file(self) -> None:
    with TemporaryDirectory() as tmp:
        root = copy_fixture("nextjs-starter", Path(tmp))
        audit = scan_project(root, ["Northstar", "starter"])
        page = next(item for item in audit.files if item.relpath == "app/demo/page.tsx")
        payload = self.base_payload()
        payload["text_edits"] = [{
            "path": page.relpath,
            "expected_sha256": page.sha256,
            "start_line": 1,
            "end_line": 1,
            "replacement": "// approved neutral heading\n",
            "reason": "Replace approved sample presentation",
        }]
        decisions = load_decisions(self.write_payload(tmp, payload), audit, root)
        self.assertEqual(decisions.text_edits[0].path, "app/demo/page.tsx")
        payload["text_edits"][0]["expected_sha256"] = "0" * 64
        with self.assertRaisesRegex(DecisionError, "text edit hash"):
            load_decisions(self.write_payload(tmp, payload), audit, root)
```

- [ ] **Step 2: Run it and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_decisions.DecisionTests.test_text_edit_requires_matching_audited_hash_and_current_file -v
```

Expected: FAIL because `text_edits` is unknown or absent from `DecisionSet`.

- [ ] **Step 3: Add the model and strict parser**

```python
@dataclass(frozen=True)
class TextEdit:
    path: str
    expected_sha256: str
    start_line: int
    end_line: int
    replacement: str
    reason: str
```

Add `text_edits: List[TextEdit] = field(default_factory=list)` to `DecisionSet`. Add `text_edits` to the allowed top-level keys and use:

```python
_TEXT_EDIT_KEYS = {
    "path", "expected_sha256", "start_line", "end_line", "replacement", "reason",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DecisionError("{} must be a positive integer".format(label))
    return value
```

Canonicalize the path, require an audited text record, compare the supplied/audited/current hashes, reject symlinks and invariant paths, read current UTF-8 text, and validate the inclusive range. Preserve compatibility for old decisions; reject nonempty edits when `project_root` is omitted.

- [ ] **Step 4: Add failing boundary tests**

Add separate tests for P0/P1 line overlap, finding-action overlap, edit overlap, traversal/absolute/Windows paths, secret/legal/binary paths, missing audit files, unknown keys, blank reason, non-string replacement, invalid ranges, stale current hash, and omitted project root.

```python
with self.assertRaisesRegex(DecisionError, "protected P0/P1 line"):
    load_decisions(protected_edit_path, audit, root)
with self.assertRaisesRegex(DecisionError, "overlaps finding action"):
    load_decisions(conflicting_edit_path, audit, root)
with self.assertRaisesRegex(DecisionError, "text edits overlap"):
    load_decisions(overlap_path, audit, root)
```

- [ ] **Step 5: Implement line and overlap protection**

Build protected lines from P0/P1 findings and action lines from referenced findings. Sort by `(path, start_line, end_line)` and reject inclusive intersections.

```python
def _intersects(start: int, end: int, lines: Set[int]) -> bool:
    return any(start <= line <= end for line in lines)
```

- [ ] **Step 6: Verify and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_decisions -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
git diff --check
git add skills/de-starter/scripts/destarter_lib/models.py skills/de-starter/scripts/destarter_lib/decisions.py tests/test_decisions.py
git commit -m "feat: validate protected semantic edits"
```

---

### Task 2: Materialize Semantic Edits in the External Preview

**Files:**
- Modify: `skills/de-starter/scripts/destarter_lib/preview.py`
- Modify: `skills/de-starter/scripts/destarter_lib/apply.py`
- Test: `tests/test_preview_apply.py`

**Interfaces:**
- Consumes: validated `DecisionSet.text_edits` and current audit inventory.
- Produces: changed preview bytes, `semantic-edits.json`, updated artifact hashes, and a token bound to edit intent/result.

- [ ] **Step 1: Write the failing preview/source-isolation test**

```python
def test_preview_applies_semantic_edit_only_to_external_copy(self) -> None:
    root, run, audit = self.semantic_fixture()
    original = (root / "app/page.tsx").read_bytes()
    decisions = self.semantic_decisions(root, audit, replacement="export default function Page() {\n  return <main>Neutral</main>;\n}\n")
    manifest = create_preview(root, run, audit, decisions)
    self.assertEqual((root / "app/page.tsx").read_bytes(), original)
    self.assertIn("Neutral", (Path(manifest.preview_root) / "app/page.tsx").read_text())
    metadata = json.loads((run / "semantic-edits.json").read_text())
    self.assertEqual(metadata["edits"][0]["path"], "app/page.tsx")
    self.assertNotIn("Neutral", json.dumps(metadata))
```

- [ ] **Step 2: Run it and verify RED**

Expected: FAIL because preview ignores edits and the artifact is absent.

- [ ] **Step 3: Implement bottom-up preview edits**

After finding replacements and before renames/deletes, group edits by path, recheck the preview preimage, preserve mode, and apply:

```python
for edit in sorted(edits, key=lambda item: (item.start_line, item.end_line), reverse=True):
    lines[edit.start_line - 1:edit.end_line] = edit.replacement.splitlines(keepends=True)
```

Add paths to `changed`. Emit only path, range, reason, and before/after hashes to `semantic-edits.json`.

- [ ] **Step 4: Bind artifact and intent into the token**

Include normalized edit records in `decision_hash`; add `semantic-edits.json` to artifact hashes; keep replacement text out of manifest/preview summaries. Update:

```python
_ARTIFACTS = (
    "preview.diff", "binary-changes.json", "placeholders.json", "semantic-edits.json",
)
```

- [ ] **Step 5: Add token, tamper, rollback, and redaction tests**

Prove that changing reason/range/replacement changes the token; artifact tampering, project drift, and preview drift reject apply; forced failure restores original bytes; replacement content is absent from safe metadata.

- [ ] **Step 6: Verify and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
git diff --check
git add skills/de-starter/scripts/destarter_lib/preview.py skills/de-starter/scripts/destarter_lib/apply.py tests/test_preview_apply.py
git commit -m "feat: preview hash-bound semantic edits"
```

---

### Task 3: Expose and Document the Semantic Workflow

**Files:**
- Modify: `skills/de-starter/scripts/destarter.py`
- Modify: `skills/de-starter/SKILL.md`
- Modify: `skills/de-starter/references/input-files.md`
- Modify: `skills/de-starter/references/report-contract.md`
- Modify: `README.md`
- Test: `tests/test_cli_e2e.py`

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: CLI root validation, installable Skill guidance, and an end-to-end semantic lifecycle test.

- [ ] **Step 1: Write a failing CLI lifecycle test**

Use a synthetic page importing a synthetic testimonial. Audit it, approve deletion of the P2 component plus semantic removal of import/usage, preview, apply, and verify that LICENSE/P1 values remain unchanged.

- [ ] **Step 2: Verify RED**

Expected: `destarter: invalid decisions` because CLI does not pass the project root.

- [ ] **Step 3: Update CLI and Skill contract**

```python
decisions = load_decisions(args.decisions, audit, root)
manifest = create_preview(root, run, audit, decisions)
```

Document the exact schema. Require named semantic path/purpose at gate one and `semantic-edits.json` at gate two. Distinguish private full diff from public screenshots.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q skills/de-starter/scripts
python3 /Users/alisa/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/de-starter
python3 skills/de-starter/scripts/destarter.py --help
git diff --check
git add skills/de-starter README.md tests/test_cli_e2e.py
git commit -m "docs: add protected semantic edit workflow"
```

---

### Task 4: Re-Audit the Private Starter and Capture Gate-One Evidence

**Files:**
- Read only: `/Users/alisa/Documents/starter`
- Update outside project: `/Users/alisa/Documents/de-starter-sistine.MRtoO4/`
- Create: `docs/video-shot-list.zh-CN.md`
- Create: `docs/assets/video/sources/01-audit-overview.html`
- Create: `docs/assets/video/01-audit-overview.png`

**Interfaces:**
- Consumes: verified Skill and confirmed source terms/neutral profile.
- Produces: current private audit, recommended P2/path/semantic scope, exact deletion names, and safe screenshot evidence.

- [ ] **Step 1: Prove the target remains unchanged**

Run `discover` into a fresh external directory and compare all 350 inventory entries with the stored baseline. Expected: added 0, removed 0, changed 0.

- [ ] **Step 2: Rerun audit**

Use confirmed `source-config.json`. Produce aggregate counts and map product functions so working chat/image/video Demo capability is not confused with disposable sample presentation.

- [ ] **Step 3: Present gate-one scope and stop**

Name every proposed deletion, rename, semantic-edit path/purpose, retained P0/P1 item, and unresolved placeholder. Do not write `decisions.json` until explicit approval.

- [ ] **Step 4: Capture private and public-safe audit images**

Render the private summary to `$RUN/screenshots/private/01-audit-overview.png`. Separately render a 1600×900 sanitized HTML card using only generic labels and aggregate counts, inspect the PNG, and record screenshot ID, source, privacy, focus, narration, and filename in `docs/video-shot-list.zh-CN.md`.

- [ ] **Step 5: Commit only sanitized assets**

```bash
git add docs/video-shot-list.zh-CN.md docs/assets/video/sources/01-audit-overview.html docs/assets/video/01-audit-overview.png
git commit -m "docs: capture sanitized audit evidence"
```

---

### Task 5: Generate the Approved Preview and Capture Gate-Two Evidence

**Files:**
- Create outside project: `$RUN/decisions.json`, preview artifacts, and private screenshots
- Create: `docs/assets/video/sources/02-safety-gates.html`
- Create: `docs/assets/video/02-safety-gates.png`
- Update: `docs/video-shot-list.zh-CN.md`

**Interfaces:**
- Consumes: explicit gate-one approval.
- Produces: exact private preview/token and a public explanation of the approval gates.

- [ ] **Step 1: Write only approved decisions**

Include exact P3 actions, retained P1 actions, confirmed path operations, and semantic edits with current hashes. Keep P0 out of actions.

- [ ] **Step 2: Generate preview and re-prove immutability**

Run `preview`, then compare the real Starter inventory with baseline. Expected: byte-identical real target.

- [ ] **Step 3: Review preview integrity**

Inspect `audit.md`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, manifest hashes, validation commands, and restore plan. Reject broken imports, one-locale edits, P1 drift, or remote demo-asset dependencies.

- [ ] **Step 4: Present exact preview/token and stop**

Show private artifacts and the exact current token. Do not apply before explicit approval.

- [ ] **Step 5: Capture safe gate screenshots**

Save the private full preview screenshot outside Git. Render public 1600×900 two-gate and sanitized diff-summary cards with no token or source excerpt; add their editing/narration instructions to the ledger.

---

### Task 6: Apply, Validate, Verify, and Produce the Effect Audit

**Files:**
- Modify only approved paths: `/Users/alisa/Documents/starter`
- Create outside project: `$RUN/effect-audit-private.md`, backups, restore files, private screenshots
- Create: `examples/sanitized-real-run-summary.md`
- Create: `docs/assets/video/sources/03-before-after.html`
- Create: `docs/assets/video/03-before-after.png`
- Update: `docs/video-shot-list.zh-CN.md`

**Interfaces:**
- Consumes: exact gate-two approval and unchanged hashes.
- Produces: cleaned Starter, validation/verification evidence, restore evidence, private detailed report, and sanitized case study.

- [ ] **Step 1: Apply only the approved token**

Run CLI `apply`. Expected: either fail closed with no mutation or produce verified backup/restore artifacts and only manifest-approved changes.

- [ ] **Step 2: Run target validation**

```bash
pnpm lint
pnpm test
pnpm build
```

Record exit codes, test counts, and known non-failing warnings.

- [ ] **Step 3: Run residue verification**

Run `verify` with confirmed source config. Exit code 3 means remaining findings. Classify each as protected, retained, placeholder, or unexpected; unexpected P3 starts another approval cycle.

- [ ] **Step 4: Write the private effect audit**

Include project facts; P0–P3 before/after counts; paths/categories/decisions; changed/deleted/renamed/semantic paths; validation; residue; placeholders; backup, restore, and reverse-diff locations. Exclude secret values and large source excerpts.

- [ ] **Step 5: Write sanitized case study and screenshots**

Create a generic before/after table, explain retained legal/compatibility residue, render public validation/comparison cards from sanitized HTML, record narration, and visually inspect each PNG.

- [ ] **Step 6: Commit public evidence**

```bash
git add examples/sanitized-real-run-summary.md docs/video-shot-list.zh-CN.md docs/assets/video
git commit -m "docs: publish sanitized acceptance evidence"
```

---

### Task 7: Produce the Beginner Video Kit with Embedded Screenshots

**Files:**
- Create: `docs/video-kit.zh-CN.md`
- Update: `docs/video-shot-list.zh-CN.md`
- Update: `docs/assets/video/`

**Interfaces:**
- Consumes: verified acceptance results and completed screenshot ledger.
- Produces: ready-to-record long/short scripts and distribution copy with images embedded at exact narration points.

- [ ] **Step 1: Write the product-first long script**

Create an 8–12 minute first-person script with the 60/25/10/5 balance. Explain P0–P3, why normal chat is less repeatable, functions, good/bad use cases, real effect, limitations, installation, and GitHub call to action in beginner language.

- [ ] **Step 2: Embed screenshots at spoken locations**

Use relative Markdown image links. Under each image specify display duration, crop/focus, optional highlight, caption, and exact spoken sentence. No missing or detached images.

- [ ] **Step 3: Add the distribution package**

Include a 60–90 second script, at least five titles, cover text, description, chapters, tags, pinned comment, FAQ, common mistakes, approval checklist, unsuitable scenarios, limitations, AI disclosure, and roadmap.

- [ ] **Step 4: Review beginner clarity and privacy**

Define Agent, Skill, Agent Skill, audit, diff, hash, token, backup, and rollback before relying on them. Scan text/source HTML for private names, paths, secrets, IDs, and tokens. Visually inspect every PNG.

- [ ] **Step 5: Commit**

```bash
git add docs/video-kit.zh-CN.md docs/video-shot-list.zh-CN.md docs/assets/video
git commit -m "docs: add beginner de-starter video kit"
```

---

### Task 8: Complete Release Verification and Publish to GitHub

**Files:**
- Modify release docs only for verified mismatches or the final URL.
- Create final GitHub screenshot after publication.

**Interfaces:**
- Consumes: passing public suite/private acceptance, complete media kit, and explicit GitHub authority.
- Produces: local `v0.1.0`, public remote, pushed tag, final repository screenshot, and URL-complete video copy.

- [ ] **Step 1: Run release gates**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q skills/de-starter/scripts
python3 /Users/alisa/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/de-starter
python3 skills/de-starter/scripts/destarter.py --help
git diff --check
git status --short
```

Scan public files for private identities, absolute paths, secrets, live IDs, and raw tokens. Expected: validations pass and worktree is clean.

- [ ] **Step 2: Request mandatory GitHub details**

Ask for authenticated account/organization, confirmation of repository name `de-starter`, and public/private visibility. Do not guess or overwrite a remote.

- [ ] **Step 3: Tag and publish after authority**

Create annotated `v0.1.0`, create or attach the confirmed remote, push the release branch/main and tag, then verify the public page and installation path.

- [ ] **Step 4: Capture final repository screen and complete links**

Capture/inspect a public 16:9 GitHub screenshot, embed it in the final video section, and replace URL placeholders in installation commands, description, pinned comment, and call to action.

- [ ] **Step 5: Final handoff**

Provide links to repository, Skill folder, private effect audit, sanitized case study, video kit, screenshot ledger, restore manifest, and release tag. State limitations and protected residue.

---

## Plan Self-Review

- [x] Input schema, protections, preview, token, recovery, reports, screenshots, acceptance, video, and publication each map to a task.
- [x] Runtime tasks begin with failing tests and end with focused/full verification.
- [x] `TextEdit`, `DecisionSet.text_edits`, `load_decisions(..., project_root=None)`, and `semantic-edits.json` use consistent names.
- [x] Gate one precedes `decisions.json`; gate two precedes Starter mutation.
- [x] Private/public screenshot sources are separate and public video never requires replaying purchased code.
- [x] GitHub account, name, and visibility remain explicitly confirmed.
