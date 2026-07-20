# Task 7 Report: Isolated Preview Generation

## RED

Created `tests/test_preview_apply.py` before the preview implementation.

```text
python3 -m unittest tests.test_preview_apply.PreviewApplyTests.test_preview_changes_copy_but_not_source -v
ModuleNotFoundError: No module named 'destarter_lib.preview'
```

Added an additional manifest-binding regression after the first implementation
pass. It failed with `KeyError: 'brand_mode'` until the artifact format bound
brand mode and a redacted brand-result hash into the approval token.

## GREEN

Implemented `destarter_lib.preview.create_preview`. It copies only permitted
source files into an external preview root, applies line/column-verified
replacements in reverse order, and performs deletes and renames only in that
copy. It emits `preview.md`, `preview.diff`, `binary-changes.json`,
`placeholders.json`, and `manifest.json` with a deterministic 64-character
approval token.

Safety boundaries added beyond the baseline sketch:

- resolves and requires project/run roots to be disjoint, with the run outside
  the project;
- rejects source symlinks, secret files, ignored metadata, and protected roots;
- rejects delete/rename scopes that contain secret or ignored content even when
  a caller constructs a `DecisionSet` outside the normal validator;
- cleans a prior preview only when its project ownership marker matches, leaving
  other run-directory content untouched;
- binds source and preview hashes, delete/rename tree hashes, brand mode, and a
  non-sensitive brand result hash into the manifest token;
- inventories binary and text filesystem operations without writing profile or
  secret-like replacement values into report artifacts.

## Verification

```text
python3 -m unittest tests.test_preview_apply -v
7 tests passed

python3 -m unittest discover -s tests -v
45 tests passed

python3 -m compileall -q skills/de-starter/scripts tests
passed

git diff --check
passed
```

## Final Important follow-up

### RED

Added regressions for a Git worktree/submodule-style root `.git` file and for
placeholder inventory output. The former failed stale-audit because preview's
safe inventory did not exclude ignored files; the latter lacked neutral values,
aggregated identifiers, explicit status, and location counts.

### GREEN

Safe inventory now excludes ignored-name files as well as directories and
secret paths, matching scanning and copying. Placeholder output is grouped by
actual value and lists the safe neutral literal, all associated identifiers,
`present`/`absent` status, deterministic locations, and occurrence count. A
custom placeholder profile value remains redacted as `<custom placeholder>` so
real-brand data cannot enter the artifact.

```text
python3 -m unittest tests.test_preview_apply -v
14 tests passed

python3 -m unittest discover -s tests -v
52 tests passed

python3 -m compileall -q skills/de-starter/scripts tests
passed

git diff --check
passed
```

## Final review remediation

### RED

Added focused regressions for a secret on the same line as a permitted brand
replacement, an added safe source file after audit, a nested `.env` directory
inside a delete scope, and a `node_modules` symlink. The initial focused run
showed the diff-context secret leak, accepted stale inventories and hidden
secret directories, and rejected the ignored pnpm-style symlink.

### GREEN

Preview reports now reuse the scanner/report assignment redactor before any
diff is written, then redact secret-like user supplied values. The source safe
inventory must exactly equal the audit inventory before any preview cleanup or
copy. Operation roots reject secret directories as well as secret files and
case-insensitive ignored directories; symlink inspection prunes those excluded
trees first.

The approval payload now also binds a canonical decision hash, complete safe
source/preview tree snapshots, and hashes of the three review artifacts. These
additive fields are persisted in `manifest.json`; profile values themselves are
only hashed. Placeholder output now uses a neutral marker, identifier, and
deduplicated locations. A deterministic rerun and explicit `keep`-decision
regression confirms approval tokens are stable for identical input and change
when explicit approval changes.

```text
python3 -m unittest tests.test_preview_apply -v
12 tests passed

python3 -m unittest discover -s tests -v
50 tests passed

python3 -m compileall -q skills/de-starter/scripts tests
passed

git diff --check
passed
```
