# Report Contract

## Required stop response

Fill every slot before any mandatory stop:

- **Status:** no project files changed; P0 and LICENSE obligations retained; stop reason.
- **Source:** candidates, evidence, recommendation, and request for the exact canonical source-term confirmation before audit.
- **Brand:** ask the user to choose either a complete real profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or exact neutral placeholders: `product_name=Your Product`, `short_name=Your Product`, `url=https://example.com`, `domain=example.com`, `support_email=support@example.com`, `repository_url=https://github.com/your-org/your-product`, `owner=Your Company`.
- **P1 / P3:** name already-visible P1 keys, payment/API identifiers, or routes separately from P3 display text. State each P1 is retained, or request its migration and rollback plans.
- **P2 choices:** recommend and request confirmation for demo routes, sample content, testimonials, test data, and assets. Name every proposed deletion and request explicit approval. For every semantic edit, name its project-relative path and approved purpose; record its hash, inclusive range, replacement, and reason in `decisions.json` only after approval.
- **Next external preview:** “After source confirmation, audit, and gate-one decisions, I will create the external-run private `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.”

Present artifacts and decisions in this order:

1. Project kind, package manager, Git state, and validation commands.
2. Source-identity candidates, supporting evidence, recommendations, and confirmed source terms.
3. Findings grouped as P0, P1, P2, and P3.
4. Chosen P2 actions for demo routes, sample content, testimonials, test data, and assets; call out every confirmed deletion.
5. Protected, retained, ambiguous, and unresolved items, including license obligations and P1 migration/rollback plans.
6. Before approval: `audit.md`, `preview.md`, private `preview.diff`, `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, and the exact current approval token. Public reporting may show redacted screenshots or a summary, never the full private diff or source excerpts.
7. Validation commands and restore strategy before apply.
8. After apply: actual changes, command results, verification findings, backup location, `reverse.diff`, `restore.json`, and `apply-result.json`.

`verify` exit code 3 means remaining findings, which must be reported explicitly. Never include secret values, private source excerpts beyond minimum evidence, or purchased code/assets in public examples. Respond in the user's language.
