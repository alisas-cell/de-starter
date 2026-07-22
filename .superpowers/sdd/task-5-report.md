# Task 5 Report: Transactional Empty-Directory Cleanup

## Scope

Implemented a separate `CleanupDirectory` transaction path for approved,
token-bound empty-directory cleanup. The implementation does not add cleanup
paths to ordinary `_affected_paths` and does not call `rmdir` to perform an
approved cleanup. A successful cleanup is an atomic descriptor-relative,
no-replace move into the external backup.

No real Starter project or private preview was touched.

## TDD Evidence

### RED A: success and recovery contract

The first three tests were added before transaction support:

- already-empty cleanup produces independent apply/backup/restore evidence;
- child originals move first and the cleanup parent is listed first for
  restoration;
- restore metadata can reconstruct the approved path and mode in a disposable
  tree.

Observed result: `3` errors, each at the intended Task 4 refusal:

```text
ApplyError: empty-directory cleanup transaction is not implemented;
approval preflight completed without creating a backup
Ran 3 tests ... FAILED (errors=3)
```

After the first implementation pass, the same tests were `3/3` green.

### RED B: explicit recovery evidence

The race/rollback implementation and five initial adversarial tests were
developed as the next pass. Those adversarial tests passed on their first
execution against that implementation. This is recorded honestly rather than
presented as a fabricated RED result.

An additional evidence-contract assertion was then added before its production
fields. It required explicit `source_device`, `source_inode`,
`source_was_empty`, and `backup_empty` entries. The intended RED was observed:

```text
KeyError: 'source_device'
Ran 1 test ... FAILED (errors=1)
```

After adding the minimal fields, the Task 5 tests were green. The final matrix
contains `15` new transaction tests, including `12` race/rollback and recovery
scenarios.

## Operation Order Implemented

1. Revalidate the token-bound source and preview state through pinned
   descriptors.
2. Create only approved output parents.
3. Move ordinary originals to the external backup.
4. Verify ordinary backups.
5. Create approved outputs.
6. Re-resolve every cleanup path from the pinned root and compare parent,
   terminal identity, mode, and current path binding.
7. Enumerate the pinned terminal descriptor and require zero children.
8. Atomically move the empty directory, with no-replace semantics, into the
   external backup.
9. Verify cleanup backups and the final preview state hash.
10. Write independent restore and reverse-diff evidence.

Rollback removes only owned outputs/artifacts, restores cleanup parents with
no-replace descriptor-relative semantics, then restores ordinary child
originals. Any foreign target, symlink, ancestor replacement, changed backup,
or identity mismatch is preserved and reported as an incomplete rollback.

## Coverage Added

- already-empty cleanup keeps the unapproved parent;
- delete child before parent cleanup;
- rename child before parent cleanup;
- parent-first restoration after a late failure;
- path and mode reconstruction from `restore.json`;
- foreign child inserted after ordinary moves;
- final terminal new-inode replacement;
- final terminal symlink replacement;
- final ancestor replacement;
- second cleanup move fails after the first succeeds;
- atomic move permission/rename failure;
- rollback target collision with foreign content;
- foreign content inserted into the cleanup backup;
- `restore.json` write failure;
- `reverse.diff` write failure after `restore.json` was published.

Each failure-path assertion checks that foreign content is not removed or
overwritten. Safe rollback restores the source tree; unsafe rollback reports
failure and retains the external backup.

## Evidence Contract

`ApplyResult.cleaned_empty_dirs` is independent from file deletes.
`restore.json` now contains:

- `cleanup_directories`, separate from ordinary `operations`;
- cleanup path and external backup object;
- original mode and audit directory-state hash;
- source device/inode and source-time emptiness;
- verified empty-backup indicator;
- explicit statement that reconstruction does not guarantee the original
  inode;
- a `restoration_order` with cleanup parents before ordinary originals.

`reverse.diff` includes a separate cleanup restoration instruction.

## Verification

```text
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning \
  -m unittest tests.test_preview_apply.PreviewApplyTests
Ran 100 tests in 3.889s — OK

PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning \
  -m unittest discover -s tests
Ran 184 tests in 7.578s — OK

PYTHONPYCACHEPREFIX=/private/tmp/de-starter-pyc \
  python3 -m compileall -q skills/de-starter/scripts
OK

git diff --check
OK
```

## Self-Review

- Cleanup authority remains independent from delete/rename authority.
- Cleanup objects are pinned separately and excluded from ordinary original
  overlap.
- Approved cleanup never uses path-based deletion.
- The implementation reuses the already-reviewed platform-specific atomic
  no-replace primitive from preview rather than introducing a second ctypes
  implementation.
- Raw descriptors are added to transaction ownership or closed in local
  `finally` blocks; strict `ResourceWarning` runs are clean.
- Existing no-cleanup behavior remains green across the full suite.

Known limitation: the v0.1 safety contract depends on the existing macOS/Linux
atomic no-replace primitive. An unsupported platform fails closed rather than
falling back to an overwriting rename.

## Independent Review Fixes

The first independent review requested three changes: one Critical atomic
phase-accounting fix, one Important artifact-ownership fix, and one Minor
evidence-label clarification.

### RED

Three deterministic fault-injection tests were added before the fixes:

1. The first backup-state read after a successful forward cleanup rename
   failed. The old code incorrectly reported `before mutation`, left the
   source path absent, and did not enter rollback.
2. The first source-state read after a successful reverse cleanup rename
   failed. The old code incorrectly said the backup was preserved even though
   the rename had consumed its backup name.
3. The first state read after publishing `restore.json` failed. The old code
   left the published restore file behind because artifact ownership had not
   yet been registered.

The evidence-label assertion also failed on the former ambiguous
`new-inode-not-guaranteed` value.

### GREEN

- `CleanupDirectory.move_committed` is now set immediately after the forward
  atomic syscall returns, with the already-proved empty state captured before
  any fallible post-move read.
- `CleanupDirectory.restore_committed` is now set immediately after the
  reverse atomic syscall returns. A subsequent verification failure reports
  that the restored entry is preserved and the backup name was consumed; it
  no longer claims the backup remains.
- A successful artifact link is added to `transaction.artifacts` before its
  first post-publish state read. Rollback removes it only when it still matches
  the precomputed inode/state and preserves a replacement.
- The recovery label is now `original-inode-not-guaranteed`.

Post-review verification:

```text
PreviewApplyTests: 103/103 — OK (`-W error::ResourceWarning`)
Full suite: 187/187 — OK (`-W error::ResourceWarning`)
compileall: OK
git diff --check: OK
```
