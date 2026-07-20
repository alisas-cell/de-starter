---
name: de-starter
description: Use when taking ownership of a starter, boilerplate, template, SaaS kit, or cloned codebase that may still contain source branding, demo content, sample assets, repository links, placeholder metadata, or risky business identifiers.
---

# De-starter

Safely convert a template-derived repository into an independently branded product. The real target is read-only through audit and external preview; show the report and current diff before edits.

## Runtime and setup

Use Python 3.9+ and the bundled CLI. v0.1 automated commands require macOS/Linux POSIX no-follow support; `apply` additionally requires the project and run directory on the same filesystem. Fail closed elsewhere: never substitute ad hoc edits or search-and-replace.

Set `SKILL_DIR` to this Skill folder. Use a real, project-sibling external run directory (for example, `../project-de-starter-run`): it is disjoint from the project while normally sharing its filesystem.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" --help
python3 "$SKILL_DIR/scripts/destarter.py" discover --project "$PROJECT" --run-dir "$RUN"
```

## Required workflow

1. Read `discovery.json`. Recommend high-confidence source-identity candidates; ask only when candidates are ambiguous. The user approves the exact canonical source-term list at approval gate one, which may be combined with the risk/P2 questions.
2. Present both brand choices: pause for a complete real profile, or choose the exact neutral placeholders for later replacement. Read [brand profile](references/brand-profile.md). Never invent a real identity.
3. Read [input-file schemas](references/input-files.md), then run `audit` with the approved `source-config.json`. Read [risk rules](references/risk-rules.md). Present protections and sensible P2 category recommendations, combine ordinary questions, and record every user decision. This is approval gate one.
4. Write `decisions.json` in `$RUN`. Stop until the exact source terms, brand mode, P1 plans, P2 category choices, and every deletion are approved. P0 never enters actions; P1 stays retained unless its action has explicit migration and rollback text.
5. Run `preview`. Show `audit.md`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, protected/retained items, validation commands, unresolved work, and the exact current approval token. Stop: this is approval gate two.
6. Apply only after explicit approval of that exact preview and token. The CLI checks current hashes and rejects stale artifacts. Run detected validation commands, then `verify` with the same source config.
7. Report results using [the report contract](references/report-contract.md). Exit code 3 from `verify` means findings remain: report them; never hide or reinterpret it as success.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" audit --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
python3 "$SKILL_DIR/scripts/destarter.py" preview --project "$PROJECT" --run-dir "$RUN" --decisions "$RUN/decisions.json"
python3 "$SKILL_DIR/scripts/destarter.py" apply --project "$PROJECT" --run-dir "$RUN" --approval-token "$TOKEN"
python3 "$SKILL_DIR/scripts/destarter.py" verify --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
```

## Mandatory stops

Stop without editing when source identity is ambiguous, the user has not selected a brand mode, license obligations are unclear, a P1 plan is incomplete, the scanner/preview/hash/backup/redaction check fails, files change after preview, or the platform/filesystem requirements are unmet. Preserve LICENSE obligations. Do not continue with direct edits.

Respond in the user's language. Redact secrets, and never put private purchased source code or assets in public examples.
