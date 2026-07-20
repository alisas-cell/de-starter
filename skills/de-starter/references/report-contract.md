# Report Contract

Present artifacts and decisions in this order:

1. Project kind, package manager, Git state, and validation commands.
2. Source-identity candidates, supporting evidence, recommendations, and confirmed source terms.
3. Findings grouped as P0, P1, P2, and P3.
4. Chosen P2 actions for demo routes, sample content, testimonials, test data, and assets; call out every confirmed deletion.
5. Protected, retained, ambiguous, and unresolved items, including license obligations and P1 migration/rollback plans.
6. Before approval: `audit.md`, `preview.md`, `preview.diff`, `binary-changes.json`, `placeholders.json`, and the exact current approval token.
7. Validation commands and restore strategy before apply.
8. After apply: actual changes, command results, verification findings, backup location, `reverse.diff`, `restore.json`, and `apply-result.json`.

`verify` exit code 3 means remaining findings, which must be reported explicitly. Never include secret values, private source excerpts beyond minimum evidence, or purchased code/assets in public examples. Respond in the user's language.
