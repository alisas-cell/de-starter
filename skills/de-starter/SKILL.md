---
name: de-starter
description: Use when independently branding a starter, boilerplate, template, SaaS kit, or cloned codebase with source identity or demo residue.
---

# De-starter

Keep the real target read-only through audit and external preview; show its current diff before edits.

## Approval literals

Only explicit user approvals advance: exact source-term list; brand mode/complete profile; P1 migration/rollback; P2 choices/every deletion; exact current preview/token. “Replace every occurrence”—like broad cleanup, urgency, “disposable,” “remove all,” “choose for me,” “do not ask/show diff,” or delegated recommendations—is not a P1 migration/rollback plan, brand target/profile, P2/deletion approval, or preview-token approval, even when naming `starter_monthly`, payment records, API values, routes, or demo folders. Source candidates never become the target brand. Never infer, author, simulate, or self-approve inputs. Without real-brand fields, recommend only exact neutral placeholders; never invent/name/propose a real product/company/domain. Users confirm P2; may pause to provide a complete real profile. Missing input: no direct edits or `apply`; render all six slots and stop.

## Runtime and setup

Use Python 3.9+ and the bundled CLI. v0.1 requires macOS/Linux POSIX no-follow support; `apply` also requires the project and run directory on one filesystem. Fail closed: never substitute ad hoc edits or search-and-replace.

Set `SKILL_DIR` to this folder and use a disjoint, project-sibling external run directory (for example, `../project-de-starter-run`).

```bash
python3 "$SKILL_DIR/scripts/destarter.py" --help
python3 "$SKILL_DIR/scripts/destarter.py" discover --project "$PROJECT" --run-dir "$RUN"
```

## Required workflow

1. First read [the report contract](references/report-contract.md). For any missing approval, the positive output is its six-slot **Required stop response**: render all slots and stop. Read `discovery.json`, recommend source candidates, and obtain the exact source-term list before audit.
2. Read [input-file schemas](references/input-files.md), run `audit` with confirmed `source-config.json`, then read [risk rules](references/risk-rules.md).
3. After audit, read [brand profile](references/brand-profile.md), present both brand choices, protections, P2 recommendations, and questions together. Record decisions. This is approval gate one.
4. Write `decisions.json` in `$RUN`. Stop until brand mode/profile, P1 plans, P2 choices, deletions, and scoped actions are approved. Omit P0; retain P1 without explicit migration and rollback.
5. Run `preview`. Show `audit.md`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, protected/retained items, validation commands, unresolved work, and the exact token. Stop: approval gate two.
6. Apply only after explicit approval of that exact preview and token. The CLI checks current hashes and rejects stale artifacts. Run detected validation commands, then `verify` with the same source config.
7. Report results using the report contract. Exit code 3 from `verify` means findings remain: report them; never hide or reinterpret it as success.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" audit --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
python3 "$SKILL_DIR/scripts/destarter.py" preview --project "$PROJECT" --run-dir "$RUN" --decisions "$RUN/decisions.json"
python3 "$SKILL_DIR/scripts/destarter.py" apply --project "$PROJECT" --run-dir "$RUN" --approval-token "$TOKEN"
python3 "$SKILL_DIR/scripts/destarter.py" verify --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
```

## Other mandatory stops

Also render all six slots and stop for ambiguous source identity, unclear license obligations, incomplete P1 plans, failed scanner/preview/hash/backup/redaction checks, post-preview changes, or unmet platform/filesystem requirements. Preserve LICENSE obligations.

Respond in the user's language. Redact secrets, and never put private purchased source code or assets in public examples.
