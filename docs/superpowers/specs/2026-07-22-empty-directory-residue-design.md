# Spec: Source-Named Empty Directory Residue

## Objective

Extend the generic `de-starter` Skill so it can audit source-named directories and safely clean an explicitly approved directory that is already empty or becomes empty only because approved child deletes/renames are applied.

The immediate acceptance case is `public/starter/`: it originally contained approved sample deletes and a renamed Demo subtree, then remained as an empty local directory after the exact Gate 2 transaction. The feature must remove that directory only after explicit approval, keep `public/`, and preserve a complete rollback record.

Success is not “delete every empty directory.” Only a directory whose own path has an audited source-term/path finding and whose exact cleanup path was approved may be removed.

## Assumptions

1. Empty directories are filesystem evidence even though Git does not track them.
2. Ordinary empty directories without a confirmed source-term/path finding are out of scope.
3. A directory that is non-empty at audit time may be approved for cleanup only when every remaining child is already owned by an approved delete or rename operation and the token-bound preview proves the directory becomes empty.
4. Cleanup approval is represented separately as `cleanup_empty_dirs`; it does not widen `delete_paths` or permit overlapping delete/rename shortcuts.
5. Directory restoration preserves path and mode from the byte/descriptor backup. A restored directory receives a new inode; inode equality is not claimed.
6. Existing file-finding counts remain comparable. Directory-path findings and cleanup counts are reported separately instead of silently rewriting the published 523 → 227 file-finding experiment.

## Tech Stack

- Python 3.9+ standard library
- Existing `destarter_lib` discovery, decisions, preview, apply, and verify runtime
- `unittest`
- POSIX descriptor operations (`dir_fd`, `O_DIRECTORY`, `O_NOFOLLOW`) on the supported macOS/Linux v0.1 platform

No new dependency is allowed.

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_decisions tests.test_preview_apply tests.test_cli_e2e
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
PYTHONPYCACHEPREFIX=/private/tmp/de-starter-pyc python3 -m compileall -q skills/de-starter/scripts
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter
git diff --check
```

The real acceptance run uses the existing CLI commands with a new private run/preview and exact approval token. It must not use `rmdir` or another ad hoc write.

## Project Structure

- `skills/de-starter/scripts/destarter_lib/models.py`: directory inventory/finding and decision/manifest data.
- `skills/de-starter/scripts/destarter_lib/files.py`: safe directory discovery/state helpers.
- `skills/de-starter/scripts/destarter_lib/scanner.py`: source-term directory path findings.
- `skills/de-starter/scripts/destarter_lib/decisions.py`: strict `cleanup_empty_dirs` validation.
- `skills/de-starter/scripts/destarter_lib/preview.py`: prove result emptiness, remove approved directories, bind artifacts/token.
- `skills/de-starter/scripts/destarter_lib/apply.py`: descriptor-safe cleanup, backup, restore, and rollback.
- `skills/de-starter/references/*.md` and `SKILL.md`: approval/report contract.
- `tests/`: synthetic RED/GREEN, conflict, race, rollback, CLI, and compatibility coverage.

## Code Style

Use small validation helpers, explicit immutable records, project-relative POSIX paths, and fail-closed exceptions. Never rely on a check-then-path-operation sequence.

```python
def _remove_approved_empty_dir(parent_fd: int, name: str, expected: DirectoryState) -> None:
    current = _lstat_entry(parent_fd, name)
    if current != expected or not current.is_directory:
        raise ApplyError("approved empty directory changed")
    _assert_directory_empty_no_follow(parent_fd, name)
    os.rmdir(name, dir_fd=parent_fd)
```

The real implementation may use existing descriptor abstractions, but must preserve this ordering: bind identity/state, prove empty without following links, then remove relative to a pinned parent.

## Data and Decision Contract

### Directory inventory

Discovery/audit records directory path, mode, deterministic directory-state hash, and whether it is empty. Directory findings use `line = 0`, a directory-specific record type/category, and the same stable finding-ID discipline as file path findings.

Directory inventory must include source-named directories even when they are non-empty. Ignored metadata, secret-named paths, project root, and symlinked directories remain excluded/protected.

### `cleanup_empty_dirs`

Add one strict top-level `decisions.json` key:

```json
{"cleanup_empty_dirs":["public/starter"]}
```

Each path must:

- be project-relative, audited, and have an exact directory path finding;
- be explicitly approved and distinct;
- not be project root, ignored, secret/legal/protected, a symlink, a file, or an operation destination;
- either be empty in the source or become empty in the preview solely because approved descendant operations move/delete every child;
- not overlap another cleanup root ambiguously.

The field is included in the decision hash, manifest, preview summary, artifacts, and approval token.

### Preview and apply

Preview performs approved child operations, proves each cleanup directory is then empty, removes it, and records source/preview directory states. Apply performs the same operation after token/source/ambient revalidation using pinned descriptors and no-follow relative operations.

Backup/restore records directory path and mode. Apply failure restores removed directories in safe parent-first order before restoring children. Rollback never removes or overwrites a replaced path, symlink, foreign content, or identity-mismatched entry.

## Testing Strategy

### RED/GREEN unit tests

- scanner reports a source-named empty directory;
- scanner reports a source-named non-empty directory path without counting ordinary parents;
- decision accepts exact audited cleanup and rejects unknown/ordinary/protected/symlink/file paths;
- preview removes an already-empty approved directory;
- preview removes a parent made empty by approved child delete/rename;
- preview rejects an unowned remaining child;
- manifest/token change when cleanup decisions change;
- apply creates backup/restore evidence and removes only the approved empty directory;
- rollback/restoration recreates path and mode;
- concurrent file insertion, symlink replacement, inode replacement, permission failure, and non-empty races fail closed without deleting foreign content;
- older decisions without `cleanup_empty_dirs` remain compatible and behave as an empty list.

### Integration tests

- CLI discover/audit/preview/apply/verify round trip with an empty source-named directory;
- approved nested rename plus parent cleanup, matching the real acceptance shape;
- restore descriptor can reconstruct the pre-apply state in a disposable copy;
- full existing suite remains green.

### Skill pressure scenario

Add a scenario where all source-named files move out but an empty source-named parent remains. A compliant agent must report it, request exact cleanup approval, generate a new preview/token, and never run ad hoc `rmdir`.

## Boundaries

### Always

- Require exact user approval for every cleanup directory.
- Bind directory state, decision, preview, and token.
- Preserve parent directories not named in `cleanup_empty_dirs`.
- Record directory cleanup and restoration in private/public reports without leaking private paths publicly.
- Re-run exact preview, validation, verify, backup checks, and independent review.

### Ask first

- Cleaning any newly discovered directory not already named by the user.
- Changing an existing cleanup path, target brand, P1 plan, or P2 operation.
- Removing a non-empty directory whose children are not entirely owned by approved operations.

### Never

- Delete all empty directories globally.
- Infer directory deletion from a child rename/delete.
- Follow symlinks or use unchecked recursive deletion.
- Treat Git's inability to track empty directories as proof that local residue does not matter.
- Rewrite the published file-finding baseline without labeling a separate directory metric.

## Success Criteria

1. The generic scanner reports source-named directory residue, including empty directories.
2. `cleanup_empty_dirs` is strict, token-bound, explicitly approved, and independently reported.
3. Synthetic preview/apply/rollback tests prove already-empty and becomes-empty cases.
4. All race/conflict tests preserve foreign content and report failure accurately.
5. Existing behavior and all prior tests remain compatible.
6. A new private preview represents only removal of approved `public/starter/`; `public/` remains.
7. The user approves the new exact preview/token before the follow-up apply.
8. The final local project has no `public/starter/`, matches the approved follow-up preview, and retains the original 64-object recovery set plus a new cleanup recovery record.
9. Public evidence explains the file-finding counts separately from the one directory-residue cleanup.

## Open Questions

None. The user has approved the exact cleanup path and required the generic capability before a new preview. Implementation may proceed only after this specification is reviewed and approved.
