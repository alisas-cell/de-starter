# Report Contract

## Required stop response

Fill every slot before any mandatory stop:

- **Status:** no project files changed; P0 and LICENSE obligations retained; stop reason.
- **Source:** candidates, evidence, recommendation, and request for the exact canonical source-term confirmation before audit.
- **Brand:** ask the user to choose either a complete real profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or exact neutral placeholders: `product_name=Your Product`, `short_name=Your Product`, `url=https://example.com`, `domain=example.com`, `support_email=support@example.com`, `repository_url=https://github.com/your-org/your-product`, `owner=Your Company`.
- **P1 / P3:** name already-visible P1 keys, payment/API identifiers, or routes separately from P3 display text. State each P1 is retained, or request its migration and rollback plans for the exact finding action or semantic range.
- **P2 choices:** recommend and request confirmation for demo routes, sample content, testimonials, test data, and assets. Name every proposed deletion and request explicit approval. For every semantic edit, name its project-relative path and approved purpose; record its hash, inclusive range, replacement, reason, and any required P1 migration/rollback plans in `decisions.json` only after approval.
- **Directory residue:** begin with the explicit numeric field `Directory residue: <count>` (never infer the number from listed paths or merge it into file findings), then list each exact source-named path and current empty/becomes-empty status. For every unapproved path, include the literal request `Please explicitly approve cleanup_empty_dirs: ["<path>"]`; do not call it approved or record it in decisions until the user replies with that exact cleanup decision. State that approval creates a new preview/token and gate-two stop, and that apply uses external transactional backup plus rollback/restore evidence. Preserve unnamed/ordinary empty directories; never infer cleanup from child operations or treat a request for `rmdir`/global cleanup as approval.
- **Next external preview:** “After source confirmation, audit, and gate-one decisions, I will create the external-run private `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.”

Present artifacts and decisions in this order:

1. Project kind, package manager, Git state, and validation commands.
2. Source-identity candidates, supporting evidence, recommendations, and confirmed source terms.
3. File findings grouped as P0, P1, P2, and P3.
4. Source-named directory residue as a separate table/count, including current emptiness and exact approved `cleanup_empty_dirs` paths. Never merge this count into file findings.
5. Chosen P2 actions for demo routes, sample content, testimonials, test data, and assets; call out every confirmed deletion.
6. Protected, retained, ambiguous, and unresolved items, including license obligations and P1 migration/rollback plans.
7. Before approval: `audit.md`, `preview.md`, private `preview.diff`, `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, and the exact current approval token. A cleanup decision added after an earlier apply gets a new preview/token and another gate-two stop. Public reporting may show redacted screenshots or a summary, never the full private diff or source excerpts.
8. Validation commands and restore strategy before apply, including external transactional backup/rollback for every cleanup directory.
9. After apply: actual file changes and file-finding counts; separately, cleaned empty directories and remaining directory findings; command results; backup location; `reverse.diff`; `restore.json`; and `apply-result.json`.

`verify` exit code 3 means remaining findings, which must be reported explicitly. Never include secret values, private source excerpts beyond minimum evidence, or purchased code/assets in public examples. Respond in the user's language.
