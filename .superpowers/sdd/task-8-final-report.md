# Task 8 Final Report: Descriptor-Owned Apply Transaction

## Outcome

Task 8 no longer uses a copied backup, project-local quarantine, destructive
commit, or ambient-path rollback. Approved changes now run as one fail-closed
POSIX transaction:

1. Require complete `dir_fd`/`O_NOFOLLOW` primitives and a shared filesystem
   before creating a backup or mutating the project.
2. Verify the token-bound source and preview, then pin the project, run,
   preview, every affected project parent, and the external
   `backup/original` hierarchy.
3. Record ambient ancestor device/inode identities and complete
   file/directory states, including modes, bytes, empty directories, layout,
   and forbidden names.
4. Recheck the pinned transaction at the final helper entry.
5. Atomically move every affected original into a unique external backup
   name, verify its identity and complete state, and retain it on success.
6. Create approved outputs exclusively through pinned project parent
   descriptors. Files use `O_CREAT|O_EXCL|O_NOFOLLOW`; directories use
   exclusive `mkdir` plus recursive descriptor-relative copies.
7. Verify output and backup identities/states, the complete visible project
   state, preview state, artifacts, and all ambient ancestors before success.
8. Publish `restore.json` and `reverse.diff` with exclusive atomic links, with
   no later destructive commit phase.

Rollback moves only outputs whose inode and complete state still match the
transaction into external transaction-owned trash before removal. Raced or
replaced outputs are preserved. Backups are restored only to absent original
names and only when their identity and state match. All errors are collected;
the result says `rolled back` only when original source state and ambient
topology are exact. Otherwise it says `rollback failed` and leaves backups or
raced objects for recovery.

The legacy ambient `_rollback`, project quarantine, copy-backup, replacement,
and unsafe deletion helpers were removed.

## RED

The expanded focused suite initially failed with the missing final transaction,
exclusive output, artifact, and filesystem-boundary interfaces. The old
implementation also leaked descriptors under repeated successful applies.

The regressions cover:

- late standalone edits and new-inode replacements at final entry;
- a late rename destination;
- file-parent and directory-parent symlink swaps;
- late `.env` insertion at final entry;
- byte-identical new-inode output replacement;
- ambient topology replacement after mutation;
- failure while publishing the second success artifact;
- unavailable descriptor primitives;
- cross-filesystem refusal;
- duplicate manifest JSON as `ApplyError`; and
- repeated-success descriptor leak detection.

Existing wrong-token, stale source/preview, success, recovery, secret,
inventory, and preview tests remain covered.

## Preview compatibility

`preview._state_hash` now records modes with `stat.S_IMODE`, matching the
transaction's complete mode representation, including special permission
bits. Newly generated approval tokens therefore bind this stronger state.

## Verification

```text
python3 -m unittest tests.test_preview_apply -v
31 tests passed

python3 -m unittest discover -s tests -v
69 tests passed

python3 -m compileall -q skills/de-starter/scripts tests
passed

git diff --check
passed
```
