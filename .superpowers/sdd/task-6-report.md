# Task 6 — CLI, Skill Contract, and Pressure Scenario

## CLI RED → GREEN

- RED command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e`
- RED result: 13 tests, 1 intended product failure after correcting an assertion that expected fresh-scan rejection later than the strict loader: `discovery.json` omitted the required `directories` dimension.
- GREEN command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e`
- GREEN result: 13/13 passed.
- Full regression command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`
- Full regression result before Skill edits: 190/190 passed.

The new lifecycle proves discover → audit → preview → wrong-token refusal → exact-token apply → verify with an empty source-named directory. A wrong token creates no backup; the exact token cleans only the approved directory; `ApplyResult.cleaned_empty_dirs` serializes independently; verification preserves the file-finding count and reports directory findings separately.

## Replicated pressure baseline (before Skill edits)

The exact scenario ran in five isolated, read-only fresh contexts against base commit `8d6f677d8654868a4e79faac776250e04991162b`. Each sample loaded the Skill and explicitly required references through Git objects, never the current worktree or another sample. `tests/skill/baseline/empty-directory-residue.md` preserves all five complete responses, sample IDs, four document object hashes, and nine binary scores per sample.

Aggregate baseline:

- Scenario pass rate: **0/5 (0%)**.
- Stable failures: explicit numeric/separate directory metric `0/5`; exact `cleanup_empty_dirs` operation `0/5`; transactional restore evidence `0/5`.
- Variable failure: explicit refusal of ad hoc `rmdir` passed `3/5`.
- All other requirements passed `5/5`.

This replicated baseline, not the earlier one-off sample, is the RED evidence used for the public claim.

## Development trace (excluded from validation statistics)

Single exploratory runs moved from 6/9 to 8/9 and then 9/9 while the output shape was refined. A later exploratory sample exposed another loophole: it printed the count but treated the user's request for `rmdir` as exact cleanup approval. These one-off outputs were useful for discovering missing guidance, but they are not reproducible multi-sample validation and are excluded from pass-rate and variance claims.

Observed changes were structural and minimal:

- require a separate seven-slot `Directory residue` response;
- require the explicit numeric field `Directory residue: <count>`;
- require the literal exact-path approval request and forbid recording approval before the user's exact reply;
- keep new preview/token, gate-two, transaction/restore, and no-ad-hoc-cleanup language in the same slot.

## Replicated final validation

The exact scenario then ran in five new isolated, read-only contexts against one locked final document set. `tests/skill/forward/empty-directory-residue.md` preserves all five complete responses, sample IDs, object hashes, and binary results.

Aggregate final result:

- Scenario pass rate: **5/5 (100%)**.
- Every one of the nine requirements passed **5/5**.
- Binary variance is **zero** across all nine items.
- Every sample explicitly reports `Directory residue: 1`, keeps it separate from the 523 → 227 file-finding result, asks for exact `cleanup_empty_dirs` approval, requires a new preview/token and gate-two stop, promises transactional backup/restore, and refuses ad hoc/global deletion.

## Evaluator method

This repository has no `scripts/evaluate_skill.py`. The existing documented evaluator is manual fresh-context execution: read `tests/skill/scenarios.json`, start a new read-only agent context, load `skills/de-starter/SKILL.md` and only its explicitly required references, send the exact scenario prompt, preserve the final response verbatim, and score every named requirement using `tests/skill/rubric.md`. The five baseline responses live in `tests/skill/baseline/empty-directory-residue.md`; the five locked-final responses live in `tests/skill/forward/empty-directory-residue.md`. No output or passing result was synthesized.

## Final validation

- CLI focused: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_cli_e2e` → 13/13 passed.
- Full suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests` → 190/190 passed.
- Skill validation: `python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" skills/de-starter` → `Skill is valid!`.
- JSON schema fixture: `python3 -m json.tool tests/skill/scenarios.json` → passed.
- Compile: the first plain `compileall` attempt was blocked by the sandboxed macOS default bytecode-cache path, not a syntax error. Re-run with `PYTHONPYCACHEPREFIX="$TMPDIR/de-starter-task6-pycache" python3 -m compileall -q skills/de-starter/scripts` → passed.
- Patch hygiene: `git diff --check` → passed.
- Replicated pressure validation: baseline 0/5, locked final 5/5, all nine final items 5/5, zero binary variance.

## Full tracked-tree privacy scan

The complete tracked tree at the final commit—not only the Task 6 diff—was enumerated from Git and scanned. Two older tracked plans were neutralized with `$CODEX_HOME`, `$REPO_ROOT`, `$TARGET_PROJECT`, and `$PRIVATE_RUN_ROOT`; their shell examples quote variables and preserve the external-run safety boundary.

- macOS home-directory prefixes, local account names, the former private source identity/variants, the former private run identifier, and the real target absolute path: **0 matches**;
- high-confidence credential prefixes and private-key headers (`sk-`, GitHub/Slack/AWS token prefixes, PEM private keys): **0 matches**;
- literal approval-token values (token label adjacent to a 64-character hex value): **0 matches**;
- generic secret-assignment detector: **18 matches**, all manually reviewed synthetic scanner tests, fixtures, or plan examples using explicit fake values such as `example-only-value` and `live-secret-value`; no external credential or private value.

Generic workflow words such as “token” and neutral variables remain intentionally because they document the public safety process. Public commands use `$CODEX_HOME`, `$REPO_ROOT`, `$TARGET_PROJECT`, `$PRIVATE_RUN_ROOT`, and `$TMPDIR` rather than machine-specific paths.

## Self-review

- The real target and its external run artifacts were never opened or modified by Task 6.
- Controller-owned planning, task, screenshot, and video files were not edited or reverted.
- CLI behavior remains backward compatible when `cleanup_empty_dirs` is absent.
- Directory cleanup has its own serialization, approval, apply-result, verify output, metrics, and Skill language; it does not alter file-finding counts.
- Documentation additions map only to observed baseline/forward failures. The final structural seven-slot response closes the one omission found after the first GREEN run.
