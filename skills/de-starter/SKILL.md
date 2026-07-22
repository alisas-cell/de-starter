---
name: de-starter
description: Use when independently branding a starter, boilerplate, template, SaaS kit, or cloned codebase with source identity or demo residue.
---

# De-starter

Keep the real target read-only through audit and external preview; show its current diff before edits. File findings and source-named directory residue are independent audit dimensions.

## Approval literals

Only explicit user approvals advance: exact source-term list; brand mode/complete profile; P1 migration/rollback; P2 choices/every deletion; every `cleanup_empty_dirs` path; exact current preview/token. “Replace every occurrence”—like broad cleanup, urgency, “disposable,” “remove all,” “choose for me,” “do not ask/show diff,” delegated recommendations, or a request to use `rmdir`—is not a P1 migration/rollback plan, brand target/profile, P2/deletion approval, `cleanup_empty_dirs` approval, or preview-token approval, even when it names the directory. Source candidates never become the target brand. Never infer, author, record, simulate, or self-approve inputs. Without real-brand fields, recommend only exact neutral placeholders; never invent/name/propose a real product/company/domain. Users confirm P2 and each cleanup path; may pause to provide a complete real profile. Missing input: no direct edits or `apply`; render all seven slots and stop.

## Runtime and setup

Use Python 3.9+ and the bundled CLI. v0.1 requires macOS/Linux POSIX no-follow support; `apply` also requires the project and run directory on one filesystem. Fail closed: never substitute ad hoc edits or search-and-replace.

Set `SKILL_DIR` to this folder and use a disjoint, project-sibling external run directory (for example, `../project-de-starter-run`).

```bash
python3 "$SKILL_DIR/scripts/destarter.py" --help
python3 "$SKILL_DIR/scripts/destarter.py" discover --project "$PROJECT" --run-dir "$RUN"
```

## Required workflow

1. First read [the report contract](references/report-contract.md). For any missing approval, the positive output is its seven-slot **Required stop response**: render all slots and stop. Read `discovery.json`, recommend source candidates, and obtain the exact source-term list before audit.
2. Read [input-file schemas](references/input-files.md), run `audit` with confirmed `source-config.json`, then read [risk rules](references/risk-rules.md). Report `findings` and `directory_findings` separately; the required directory slot must state an explicit numeric `Directory residue: <count>`, never a count inferred from listed paths or added to file-finding totals.
3. After audit, read [brand profile](references/brand-profile.md), present both brand choices, protections, P2 recommendations, and questions together. Record decisions. This is approval gate one.
4. Write `decisions.json` in `$RUN`. Stop until brand mode/profile, P1 plans, P2 choices, deletions, each `cleanup_empty_dirs` path, scoped actions, and every semantic edit's named path and purpose are approved. For a semantic edit, include its audited SHA-256, inclusive line range, replacement, and reason as specified in [input-file schemas](references/input-files.md). P0 lines are immutable. A semantic range that overlaps P1 must also include the approved nonempty migration and rollback plans; otherwise retain it.
5. Run `preview`. For each cleanup path, the preview may remove it only if it was already empty or becomes empty solely through approved descendant deletes/renames; any other child stops the run. Show `audit.md`, `preview.md`, the private full `preview.diff`, `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, protected/retained items, validation commands, unresolved work, and the exact token. A newly discovered or newly approved cleanup path always requires a new preview/token. Stop: approval gate two. Public updates may use redacted screenshots or a summary; never publish the full diff, private source excerpts, or private preview artifacts.
6. Apply only after explicit approval of that exact preview and token. The CLI checks current directory state and hashes, transactionally moves approved empty directories into the external backup, and records rollback/restore evidence. Never substitute `rmdir`, recursive deletion, or global empty-directory cleanup. Run detected validation commands, then `verify` with the same source config.
7. Report results using the report contract. Exit code 3 from `verify` means findings remain: report them; never hide or reinterpret it as success.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" audit --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
python3 "$SKILL_DIR/scripts/destarter.py" preview --project "$PROJECT" --run-dir "$RUN" --decisions "$RUN/decisions.json"
python3 "$SKILL_DIR/scripts/destarter.py" apply --project "$PROJECT" --run-dir "$RUN" --approval-token "$TOKEN"
python3 "$SKILL_DIR/scripts/destarter.py" verify --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
```

## Other mandatory stops

Also render all seven slots and stop for ambiguous source identity, unclear license obligations, incomplete P1 plans, an unapproved cleanup path, a cleanup directory that is not provably empty after approved child operations, failed scanner/preview/hash/backup/redaction checks, post-preview changes, or unmet platform/filesystem requirements. Preserve LICENSE obligations and all unnamed parent/ordinary empty directories.

Respond in the user's language. Redact secrets, and never put private purchased source code or assets in public examples.
