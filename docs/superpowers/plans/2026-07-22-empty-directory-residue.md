# Empty Directory Residue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, audited, token-bound, transactional `cleanup_empty_dirs` operation to the generic `de-starter` Skill, then use a new approval preview to remove only the already-approved `public/starter/` residue while preserving `public/` and rollback evidence.

**Architecture:** Extend the audit snapshot with safe directory records and exact directory-name findings. Validate cleanup decisions independently from file/tree deletion. The preview first applies owned child operations, proves each approved directory is empty, removes it from the external preview, and binds its source state to the manifest and approval token. Apply pins the directory and parent with descriptors, performs ordinary child moves first, proves the same directory is now empty, and atomically moves the empty directory into the external backup. Rollback restores cleanup parents before restoring child originals, so no ad hoc deletion or overwrite is required.

**Tech Stack:** Python 3.9+ standard library, POSIX `dir_fd`/`O_DIRECTORY`/`O_NOFOLLOW`, `unittest`, existing de-starter CLI and external run artifacts.

## Global Constraints

- Canonical approved specification: `docs/superpowers/specs/2026-07-22-empty-directory-residue-design.md`.
- No dependency additions and no global empty-directory cleanup.
- Keep the existing file-finding metric comparable; directory findings and cleanup totals are separate fields/sections.
- `cleanup_empty_dirs` is optional and defaults to `[]`, preserving old decisions and runs.
- Never infer parent cleanup from a child delete or rename.
- Never clean project root, ignored, secret, legal/protected, symlinked, file, unaudited, destination, or ambiguously overlapping paths.
- Preview and apply must use the same operation order: text edits, renames/deletes, emptiness proof, directory cleanup.
- Apply must not use an unchecked path-based `rmdir`; successful cleanup is an atomic descriptor-relative move into the external backup.
- A race or foreign child must fail closed and preserve the foreign entry.
- Every implementation task follows RED → confirm the intended failure → GREEN → focused tests → commit.
- Do not generate or apply the real Starter cleanup preview until the generic suite and compatibility checks pass.
- The real follow-up apply requires a newly generated exact token and a separate user confirmation.

---

## Task 1: Add Safe Directory Inventory and Directory Findings

**Files:**

- Modify: `skills/de-starter/scripts/destarter_lib/models.py`
- Modify: `skills/de-starter/scripts/destarter_lib/files.py`
- Modify: `skills/de-starter/scripts/destarter_lib/scanner.py`
- Modify: `skills/de-starter/scripts/destarter_lib/report.py`
- Modify: `skills/de-starter/scripts/destarter.py` (minimal schema compatibility)
- Test: `tests/test_files.py`
- Test: `tests/test_scanner_report.py`
- Test: `tests/test_cli_e2e.py` (existing lifecycle remains green)

- [ ] **Step 1: Write failing inventory tests**

Add tests proving that `iter_project_directories(root)`:

- returns real safe directories in deterministic path order;
- includes empty and non-empty source-named directories;
- excludes project root, ignored/secret directories, and symlink directories;
- records project-relative path, permission mode, deterministic `state_sha256`, and `is_empty`;
- changes `state_sha256` when direct/descendant directory state changes.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_files
```

Expected RED: missing `DirectoryRecord`/`iter_project_directories`.

- [ ] **Step 2: Implement the directory record and descriptor-safe inventory**

Add this immutable model:

```python
@dataclass(frozen=True)
class DirectoryRecord:
    relpath: str
    mode: int
    state_sha256: str
    is_empty: bool
```

Add `directories: List[DirectoryRecord]` to `DiscoveryResult` and `AuditResult`. Implement `iter_project_directories(root)` using `os.walk(..., followlinks=False)`, `lstat`/no-follow checks, existing ignore and secret rules, and a canonical state payload. `is_empty` must reflect actual children, including excluded children, so a directory containing ignored/secret data is never misreported as empty.

- [ ] **Step 3: Write failing scanner/report tests**

Add tests proving:

- `public/starter/` produces one exact `directory-name` finding even when empty;
- a non-empty `starter-assets/` directory is found independently of its child file findings;
- ordinary parents such as `public/` are inventoried but receive no directory finding;
- directory findings are not included in the existing file-finding count/array;
- `audit.json` exposes a separate `directories` and `directory_findings` contract and `audit.md` has a separate “Directory residue” section.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_scanner_report
```

Expected RED: scanner/report have no directory contract.

- [ ] **Step 4: Implement exact source-term directory findings**

Create stable finding IDs from directory path, occurrence offset, and matched term. Use `line = 0`, the directory state hash in `sha256`, and category `directory-name`. Keep `AuditResult.findings` as the legacy file finding list and add `directory_findings` separately so the published 523 → 227 comparison does not change.

- [ ] **Step 5: Run focused tests and commit**

Before committing, update the CLI's strict audit loader and discovery serialization for the new required `directories` and `directory_findings` fields. This belongs with Task 1 because the audit data contract must not leave existing CLI lifecycle tests broken between tasks. Task 6 retains ownership of the broader tamper matrix and complete empty-directory lifecycle.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_files tests.test_scanner_report tests.test_cli_e2e
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
git diff --check
git add skills/de-starter/scripts/destarter.py skills/de-starter/scripts/destarter_lib/models.py skills/de-starter/scripts/destarter_lib/files.py skills/de-starter/scripts/destarter_lib/scanner.py skills/de-starter/scripts/destarter_lib/report.py tests/test_files.py tests/test_scanner_report.py tests/test_cli_e2e.py
git commit -m "feat: audit source-named directories"
```

---

## Task 2: Add Strict `cleanup_empty_dirs` Decisions

**Files:**

- Modify: `skills/de-starter/scripts/destarter_lib/models.py`
- Modify: `skills/de-starter/scripts/destarter_lib/decisions.py`
- Test: `tests/test_decisions.py`

- [ ] **Step 1: Write failing acceptance and compatibility tests**

Cover:

- absent `cleanup_empty_dirs` becomes `[]`;
- exact audited empty source-named directory is accepted;
- exact audited non-empty source-named parent is accepted only as a candidate for preview-time becomes-empty proof;
- duplicate, normalized duplicate, root, absolute/escaping, ordinary, ignored, secret, legal/protected, symlink, file, and unknown paths are rejected;
- a cleanup path cannot equal or sit inside a delete/rename source, cannot overlap another cleanup root, and cannot overlap any rename destination;
- a cleanup parent may contain approved delete/rename sources because this is the required becomes-empty shape;
- protected P0/P1 descendant findings reject cleanup authorization.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_decisions
```

Expected RED: unknown decision key or missing model field.

- [ ] **Step 2: Implement strict parsing and validation**

Extend the decision model:

```python
@dataclass
class DecisionSet:
    ...
    cleanup_empty_dirs: List[str] = field(default_factory=list)
```

Add `cleanup_empty_dirs` to `_TOP_LEVEL_KEYS`. Validate with `_project_path`, exact `AuditResult.directories` membership, an exact `directory-name` finding on the same path, current real-directory/no-symlink checks when `project_root` is available, invariant/protected checks, and explicit overlap rules. Do not reuse `_validate_audited_paths(..., "delete")`, because cleanup has a narrower independent authority.

- [ ] **Step 3: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_decisions
git diff --check
git add skills/de-starter/scripts/destarter_lib/models.py skills/de-starter/scripts/destarter_lib/decisions.py tests/test_decisions.py
git commit -m "feat: validate empty directory cleanup decisions"
```

---

## Task 3: Make Preview Prove Emptiness and Bind Cleanup to the Token

**Files:**

- Modify: `skills/de-starter/scripts/destarter_lib/models.py`
- Modify: `skills/de-starter/scripts/destarter_lib/preview.py`
- Modify: `skills/de-starter/scripts/destarter_lib/apply.py` (minimal schema compatibility and pre-mutation refusal only)
- Test: `tests/test_preview_apply.py`

- [ ] **Step 1: Write failing preview tests**

Add synthetic tests for:

- already-empty approved directory disappears only in `run/preview`;
- a source-named parent becomes empty after an approved descendant delete;
- a source-named parent becomes empty after an approved descendant rename to a destination outside the cleanup root;
- one unowned child, ignored child, secret child, symlink replacement, or wrong object kind rejects preview and leaves source untouched;
- changing only `cleanup_empty_dirs`, directory mode, or directory state changes the manifest/token;
- parent directory outside the approved cleanup list remains;
- `preview.diff`, `binary-changes.json`, `preview.md`, and `manifest.json` identify cleanup separately from deletion.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
```

Expected RED: cleanup is neither rendered nor token-bound.

- [ ] **Step 2: Extend the manifest contract**

Add fields such as:

```python
cleanup_empty_dirs: List[str]
cleanup_dir_states: Dict[str, Dict[str, object]]
```

Each state entry binds the audited source mode, source state hash, and source-time emptiness. Include both fields in `decision_hash`, manifest core, brand result hash where operation results are bound, and the final approval token.

- [ ] **Step 3: Implement ordered preview cleanup**

After all text/delete/rename operations:

1. Resolve the approved preview path through `_safe_relpath`.
2. Reject missing, symlinked, or non-directory objects.
3. Enumerate without following links and require zero remaining entries.
4. Remove only that exact empty preview directory.
5. Recompute `preview_state_hash` after cleanup.

Add a `cleanup-empty-dir` operation record containing the project-relative path, mode, and source state hash. Add a human-readable line to `preview.diff` and a separate count in `preview.md`.

- [ ] **Step 4: Run focused tests and commit**

Because `manifest.json` has an exact consumer schema, update the Apply loader in the same task to parse and token-bind the new cleanup fields for backward compatibility. Until Tasks 4–5 add complete preflight and transaction support, any manifest with non-empty `cleanup_empty_dirs` must fail explicitly before backup creation or project mutation. Add a focused assertion for that refusal. Existing no-cleanup apply lifecycles must remain green.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
git diff --check
git add skills/de-starter/scripts/destarter_lib/models.py skills/de-starter/scripts/destarter_lib/preview.py skills/de-starter/scripts/destarter_lib/apply.py tests/test_preview_apply.py
git commit -m "feat: bind empty directory cleanup previews"
```

---

## Task 4: Load and Revalidate the Cleanup Manifest Fail-Closed

**Files:**

- Modify: `skills/de-starter/scripts/destarter_lib/apply.py`
- Test: `tests/test_preview_apply.py`

- [ ] **Step 1: Write failing manifest/preflight tests**

Cover malformed types, unknown/missing cleanup keys, duplicate paths, state/path mismatches, token tampering, post-preview directory mode changes, child insertion, symlink replacement, inode replacement, and a cleanup path changed into a file. Every case must fail before a project mutation or backup object remains.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
```

Expected RED: apply loader does not recognize or verify cleanup metadata.

- [ ] **Step 2: Implement strict manifest loading and operation-shape rules**

Extend `_MANIFEST_KEYS`, `_load_manifest`, `_validate_operation_shapes`, and `_verify_approval` so:

- cleanup paths exactly match cleanup state keys;
- cleanup roots are unique/non-overlapping;
- cleanup roots may contain ordinary source delete/rename roots but may not equal or sit below one;
- no rename destination overlaps cleanup;
- root source/preview state hashes and exact cleanup metadata are revalidated before backup creation.

- [ ] **Step 3: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
git diff --check
git add skills/de-starter/scripts/destarter_lib/apply.py tests/test_preview_apply.py
git commit -m "feat: verify empty directory cleanup approvals"
```

---

## Task 5: Implement Transactional Backup, Cleanup, and Rollback

**Files:**

- Modify: `skills/de-starter/scripts/destarter_lib/models.py`
- Modify: `skills/de-starter/scripts/destarter_lib/apply.py`
- Test: `tests/test_preview_apply.py`

- [ ] **Step 1: Write failing success and restoration tests**

Prove:

- apply removes only an approved already-empty directory and leaves its parent;
- child delete/rename sources move first, then the now-empty cleanup directory moves into backup;
- `restore.json` records cleanup path, original mode/state, empty backup object, and parent-first restoration order;
- a disposable reconstruction restores the pre-apply tree and directory mode;
- `ApplyResult` reports `cleaned_empty_dirs` independently.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
```

Expected RED: no cleanup transaction exists.

- [ ] **Step 2: Add a separate cleanup transaction record**

Use a dedicated record rather than pretending cleanup is `delete_paths`:

```python
@dataclass
class CleanupDirectory:
    relpath: str
    parent_fd: int
    name: str
    initial: ObjectState
    mode: int
    backup_name: str
    moved_empty: Optional[ObjectState] = None
```

Pin these records in `_prepare_transaction` but keep them out of ordinary `_affected_paths`, avoiding overlapping parent/child originals.

- [ ] **Step 3: Implement ordered atomic mutation**

Update the final-entry sequence to:

```text
verify all pinned source and preview state
create approved output parents
move ordinary originals into backup
verify ordinary backups
create approved outputs
for each cleanup directory:
  verify same inode/mode and zero current children through pinned descriptors
  rename the empty directory into backup with dir_fd
verify all backups and final preview_state_hash
```

The directory move is the successful removal. Do not call path-based `rmdir` for approved cleanup.

- [ ] **Step 4: Write failing race and rollback tests**

Inject failures/concurrency at each boundary:

- foreign file insertion after child moves;
- symlink or inode replacement before cleanup move;
- permission/rename failure during cleanup;
- failure after one of multiple cleanup moves;
- restore-name collision and foreign content during rollback;
- failure while writing `restore.json` or `reverse.diff` after cleanup.

Assert no foreign content is deleted or overwritten, complete rollback restores source state where safe, incomplete rollback is reported accurately, and external backup remains available.

- [ ] **Step 5: Implement parent-first rollback and evidence**

Restore moved cleanup directories before normal originals. Use no-replace descriptor-relative restore semantics and verify identities/states at every boundary. Extend `_verify_backups`, `_verify_success`, `_rollback`, `_reverse_diff`, `_restore_payload`, and `ApplyResult` with independent cleanup evidence.

- [ ] **Step 6: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_preview_apply.PreviewApplyTests
git diff --check
git add skills/de-starter/scripts/destarter_lib/models.py skills/de-starter/scripts/destarter_lib/apply.py tests/test_preview_apply.py
git commit -m "feat: transact and restore empty directory cleanup"
```

---

## Task 6: Update CLI Schemas, Skill Contract, and Pressure Test

**Files:**

- Modify: `skills/de-starter/scripts/destarter.py`
- Modify: `skills/de-starter/SKILL.md`
- Modify: `skills/de-starter/references/input-files.md`
- Modify: `skills/de-starter/references/risk-rules.md`
- Modify: `skills/de-starter/references/report-contract.md`
- Modify: `tests/test_cli_e2e.py`
- Modify: `tests/skill/scenarios.json`
- Modify: `tests/skill/rubric.md`
- Add: `tests/skill/forward/empty-directory-residue.md`

- [ ] **Step 1: Write failing CLI lifecycle test**

Exercise discover → audit → preview → rejected wrong token → apply → verify with an empty source-named directory. Assert:

- discovery/audit serialize and reload directory records strictly;
- stale/tampered directory audit is rejected;
- wrong token leaves the directory and produces no backup;
- exact token removes only the approved directory;
- verification reports zero directory residue independently from file findings.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e
```

- [ ] **Step 2: Extend strict CLI audit loading**

Update discover output, `_load_audit`, fresh-scan equality, apply-result serialization, and verify output. Reject unknown/missing directory schema fields, duplicate directory paths/IDs, invalid mode/hash/boolean values, and directory findings not backed by directory records.

- [ ] **Step 3: Run the empty-directory pressure scenario before changing the Skill**

Run the new scenario first against the current Skill guidance and record the exact baseline behavior. The RED condition is that the agent misses the empty source-named parent, folds it into file findings, deletes it without a new token, or proposes an ad hoc `rmdir`. If the no-guidance control does not exhibit a relevant failure, do not add speculative prose; retain the executable contract and record why the documentation change is unnecessary.

- [ ] **Step 4: Update public Skill instructions to address the observed failure**

Document:

- directory residue as a separate audit dimension;
- the exact `cleanup_empty_dirs` input;
- mandatory explicit approval and new-token gate;
- already-empty and becomes-empty rules;
- transactional backup/rollback semantics;
- prohibition on global cleanup and ad hoc `rmdir`;
- report language that does not merge directory cleanup with file-finding counts.

- [ ] **Step 5: Re-run and evaluate the pressure scenario with the updated Skill**

Scenario: all files/subtrees have moved out, leaving a source-named parent. Passing behavior must report the directory residue, request exact cleanup approval, produce a new preview/token, stop at Gate 2, and never silently delete it.

- [ ] **Step 6: Run focused tests and commit**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e
python3 scripts/evaluate_skill.py
git diff --check
git add skills/de-starter/scripts/destarter.py skills/de-starter/SKILL.md skills/de-starter/references tests/test_cli_e2e.py tests/skill
git commit -m "docs: define approved empty directory cleanup"
```

If the repository uses a different Skill evaluator command, inspect the existing test harness and substitute its documented command; do not invent a passing result.

---

## Task 7: Full Regression and Independent Review

**Files:**

- Modify only if a test or review identifies a real defect.
- Update: `tasks/todo.md`
- Update: `.superpowers/sdd/protected-semantic-edits-progress.md`

- [ ] **Step 1: Run the complete validation matrix**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONPYCACHEPREFIX=/private/tmp/de-starter-pyc python3 -m compileall -q skills/de-starter/scripts
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
git diff --check
git status --short
```

Expected: all existing and new tests pass, compilation succeeds, Skill validation succeeds, and only intended files are changed.

- [ ] **Step 2: Perform security-focused review**

Review specifically for:

- check/use races around emptiness and rename;
- parent/child overlap and restoration order;
- symlink following;
- backup ownership/identity verification;
- foreign-content preservation;
- token/artifact coverage;
- backward compatibility and honest metrics.

- [ ] **Step 3: Fix findings with new RED tests, rerun full validation, and commit**

```bash
git add skills/de-starter tests docs tasks .superpowers/sdd/protected-semantic-edits-progress.md
git commit -m "test: verify empty directory cleanup safety"
```

---

## Task 8: Generate the Real Follow-up Preview and Stop at Gate 2

**Files:**

- Create in a new private external run directory: source config, audit, decisions, preview artifacts.
- Update privately: experiment/effect audit notes.
- Do not modify `$TARGET_PROJECT` in this task.

- [ ] **Step 1: Re-audit the current real Starter with the generic CLI**

Confirm independently:

- `public/starter/` is a source-named directory finding and is currently empty;
- `public/` is not a cleanup decision and remains protected by omission;
- no new file edit/delete/rename is included;
- the existing 523 → 227 file-finding experiment remains unchanged;
- cleanup scope is exactly one directory.

- [ ] **Step 2: Write the exact private decisions file**

The only new operation must be:

```json
{
  "cleanup_empty_dirs": ["public/starter"]
}
```

Retain required neutral brand fields/actions as no-op lifecycle inputs, but do not authorize any additional project mutation.

- [ ] **Step 3: Generate and inspect the new external preview**

Verify preview artifacts, source/preview state hashes, directory cleanup record, backup plan, and exact token. Compare the real source with preview and prove the sole project-state difference is absence of `public/starter/`.

- [ ] **Step 4: Present the exact preview/diff and token to the user, then stop**

Report:

- cleanup directories: 1;
- file changes/deletes/renames: 0;
- retained parent: `public/`;
- restoration evidence to be created;
- exact new approval token.

Do not call `apply` until the user explicitly approves that token.

---

## Task 9: Apply the Approved Real Cleanup and Refresh Evidence

**Prerequisite:** The user has explicitly approved the exact Task 8 token.

**Files:**

- Modify transactionally: `$TARGET_PROJECT/<approved-source-directory>/` only.
- Update private acceptance report and recovery ledger.
- Update sanitized public example/report and video evidence only after verification.

- [ ] **Step 1: Apply with the exact approved token**

Use the generic CLI `apply`; no shell deletion command is permitted.

- [ ] **Step 2: Verify project and recovery state**

Prove:

- `public/starter/` is absent;
- `public/` remains;
- project state exactly matches the approved follow-up preview;
- follow-up backup contains the empty directory recovery object and correct mode;
- the original 64-object recovery set remains intact;
- file findings remain 227 and directory residue for the approved path becomes zero;
- focused/full Skill tests still pass.

- [ ] **Step 3: Refresh reports and video evidence honestly**

Keep 523 → 227 labeled as file findings. Add a separate line/card: `source-named empty directory residue: 1 → 0`. Capture a privacy-safe screenshot and place it at the exact point in the Chinese narration/shot list where the final local residue result is explained.

- [ ] **Step 4: Independent final review and commit**

Review transaction artifacts, rollback reconstruction, public privacy, visual accuracy, and Git diff. Fix any finding with evidence before claiming completion.

---

## Human Review Gate

This plan and `tasks/todo.md` require user approval before Task 1 implementation begins. The specification is already approved; approval of this plan authorizes the TDD implementation tasks only. It does not pre-approve the new real Starter Gate 2 token required in Task 8.
