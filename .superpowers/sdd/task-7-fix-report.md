# Task 7 Whole-Feature Review Fix Report

## Scope

Resolved the three release blockers from whole-feature review without touching
the real Starter or generating a real preview:

1. ordinary originals now record committed namespace moves before fallible
   post-move reads;
2. ordinary original backup moves now use the existing atomic no-replace
   primitive;
3. the human-readable preview summary is token-free, hash-bound, and verified
   by Apply.

## RED Evidence

Four focused regressions were written and observed failing before production
changes:

### Ordinary delete-child phase gap

Injected a failure into the first backup-state read after the delete-child
rename syscall had already succeeded. The old result was:

```text
apply refused before mutation but empty backup cleanup failed
```

The source child was absent because `Original.moved` had not been assigned.

### Ordinary rename-child phase gap

Repeated the post-move read failure for a directory renamed out of a cleanup
parent. The old code again reported before-mutation and did not restore the
committed tree move.

### Ordinary backup destination race

Inserted a foreign file into the unique external backup name after the absent
check. The old ordinary `os.rename` path overwrote it and Apply succeeded,
proving the ordinary backup move lacked no-clobber semantics.

### Unbound preview summary

The cleanup preview manifest did not contain a `preview.md` artifact hash, and
the report embedded the approval token. Changing its cleanup count therefore
was not Apply-visible.

All four focused tests failed for the intended reasons (`4/4` RED).

## GREEN Implementation

### Ordinary original phase ledger

`Original` now has `move_committed`. Immediately after the atomic syscall
returns, Apply records:

```text
move_committed = true
moved = the already-pinned expected ObjectState
```

Only then does it perform the fallible backup-state read. Mutation detection,
backup verification, and rollback use the committed phase rather than treating
an absent optional state as proof that no move happened.

The deterministic delete-child and rename-child failures now enter rollback,
restore the source path/tree, retain the verified external original, and never
claim the apply failed before mutation.

### Atomic no-clobber ordinary backup

Every ordinary file/tree original now moves with
`_atomic_rename_no_replace(...)`. The prior absent check remains a useful early
diagnostic, while the atomic primitive closes the check-to-rename race. There
is no overwriting fallback.

The raced foreign backup target keeps its original device/inode and bytes, the
source remains in place, and Apply fails closed while retaining the external
backup for inspection.

### Canonical token-free summary

`preview.md` is now rendered before token calculation and contains counts and
review guidance but no token value. Its SHA-256 is included in
`artifact_hashes`, which is approval-token-bound and checked both before backup
creation and at final descriptor-pinned verification.

The exact token remains available separately in `manifest.json` and the CLI
preview output. This avoids a hash/token cycle while preserving a clear Gate 2
workflow.

Apply accepts the legacy four-artifact set only for the old manifest form that
lacks the cleanup fields. Every new manifest with the cleanup schema—including
an empty cleanup list—requires the five-artifact set containing `preview.md`.
A retokened cleanup manifest cannot downgrade to the legacy artifact set.

## Regression Coverage

- delete child: state-read failure immediately after committed ordinary move;
- rename child tree: same committed-boundary failure;
- foreign file raced into the ordinary backup destination;
- preview summary contains no approval token;
- preview summary hash is present in the manifest;
- changed cleanup count is rejected before backup creation;
- cleanup manifest cannot remove the summary hash and masquerade as legacy;
- genuine legacy manifest fixture removes `preview.md` from its artifact set,
  retokens with the legacy payload shape, and remains accepted;
- existing cleanup-only atomic failure test now targets the cleanup move rather
  than the newly atomic ordinary child move.

## Verification

```text
PreviewApplyTests: 108/108 — OK (`-W error::ResourceWarning`)
Full suite: 195/195 — OK (`-W error::ResourceWarning`)
CLI lifecycle: 13/13 — OK (`-W error::ResourceWarning`)
quick_validate.py: Skill is valid!
compileall: OK
all repository JSON parses: OK
git diff --check: OK
```

## Self-Review

- File and directory originals share the same no-replace primitive already
  reviewed for the cleanup transaction.
- No path-based overwrite fallback was introduced.
- Phase ownership is recorded from the pinned pre-move state, which remains
  valid across same-filesystem rename and includes identity, content digest,
  kind, and forbidden-content state.
- Rollback continues to verify the actual backup against that exact state
  before reconstructing the source.
- A foreign backup target makes the external backup scaffold intentionally
  non-removable; the tool reports this instead of deleting foreign data.
- Token-free summary generation occurs only after all count inputs are known
  and before artifact/token calculation.
- Existing no-cleanup and legacy apply lifecycles remain green.
