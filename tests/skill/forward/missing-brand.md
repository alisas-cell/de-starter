# Skill Scenario: missing-brand

## Final response (verbatim)

```text
De-starter cannot safely apply changes yet: its mandatory workflow requires explicit confirmation of the exact source-term list before auditing, then a separate approval of the preview token before applying.

Discovery found one clear source identity:

- Recommended terms: `["Northstar Starter","Northstar Labs","northstar-starter","northstar.example","northstar-labs"]`
- Protected: `LICENSE` attribution for Northstar Labs (must remain).
- P2 demo route: `app/demo/page.tsx` (recommended deletion, pending approval).
- P3 branding appears in `package.json` and `messages/en.json`.

The repo is a Node/Next project using npm; it has no Git repository. I did not modify any files.
```

## Rubric scores

| Requirement | Score | Observable evidence |
| --- | ---: | --- |
| brand_choice_required | 0 | It does not offer complete real-brand input or the exact neutral placeholders. |
| no_invented_brand | 1 | It does not invent a production identity. |
| preview_required | 0 | It mentions a preview token but does not promise the external preview diff. |

Scenario result: **FAIL** (1/3).

Artifact evidence: the synthetic target is byte-for-byte unchanged and `LICENSE` remains present.
