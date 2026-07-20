---
name: de-starter
description: Use when independently branding a starter, boilerplate, template, SaaS kit, or cloned codebase with source identity or demo residue.
---

# De-starter

Safely convert a template-derived repository. Keep the real target read-only through audit and external preview; show the current diff before edits.

## Runtime and setup

Use Python 3.9+ and the bundled CLI. v0.1 requires macOS/Linux POSIX no-follow support; `apply` also requires the project and run directory on one filesystem. Fail closed: never substitute ad hoc edits or search-and-replace.

Set `SKILL_DIR` to this folder. Use a project-sibling external run directory (for example, `../project-de-starter-run`), disjoint from the project.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" --help
python3 "$SKILL_DIR/scripts/destarter.py" discover --project "$PROJECT" --run-dir "$RUN"
```

## Required workflow

1. Read `discovery.json`; recommend high-confidence source candidates and obtain explicit confirmation of the exact canonical source-term list before audit. Stop without it.
2. Read [input-file schemas](references/input-files.md), run `audit` with confirmed `source-config.json`, then read [risk rules](references/risk-rules.md).
3. After audit, read [brand profile](references/brand-profile.md), present both brand choices, protections, P2 recommendations, and questions together. Record decisions. This is approval gate one.
4. Write `decisions.json` in `$RUN`. Stop until brand mode/profile, P1 plans, P2 choices, deletions, and scoped actions are approved. Omit P0; retain P1 without explicit migration and rollback.
5. Run `preview`. Show `audit.md`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, protected/retained items, validation commands, unresolved work, and the exact token. Stop: approval gate two.
6. Apply only after explicit approval of that exact preview and token. The CLI checks current hashes and rejects stale artifacts. Run detected validation commands, then `verify` with the same source config.
7. Report results using [the report contract](references/report-contract.md). Exit code 3 from `verify` means findings remain: report them; never hide or reinterpret it as success.

```bash
python3 "$SKILL_DIR/scripts/destarter.py" audit --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
python3 "$SKILL_DIR/scripts/destarter.py" preview --project "$PROJECT" --run-dir "$RUN" --decisions "$RUN/decisions.json"
python3 "$SKILL_DIR/scripts/destarter.py" apply --project "$PROJECT" --run-dir "$RUN" --approval-token "$TOKEN"
python3 "$SKILL_DIR/scripts/destarter.py" verify --project "$PROJECT" --run-dir "$RUN" --source-config "$RUN/source-config.json"
```

## Mandatory stops and response

Stop without editing when source identity is ambiguous or unconfirmed, brand mode is unselected, license obligations are unclear, a P1 plan is incomplete, a scanner/preview/hash/backup/redaction check fails, files change after preview, or platform/filesystem requirements are unmet. Preserve LICENSE obligations; never continue with direct edits.

At every stop, give this short positive status report before asking for input: state no project files changed and P0/LICENSE retained; give source candidates, evidence, recommendation, and request the exact source-term confirmation (before audit); offer both brand choices—complete real profile or the exact neutral placeholders; separate P1 identifiers (e.g. keys, payment/API names) from P3 display text and request migration plus rollback for any P1 change; recommend a choice for each P2 category (demo routes, sample content, testimonials, test data, assets) and require explicit deletion confirmation. Promise that, after gate-one decisions, you will produce an external-run `preview.diff` with preview artifacts, show its exact approval token, and stop for gate two before edits.

Respond in the user's language. Redact secrets, and never put private purchased source code or assets in public examples.
