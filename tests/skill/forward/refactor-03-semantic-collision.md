# Refactor 03: semantic-collision (five repetitions)

## Run 01 final response (verbatim)

```text
**Status:** No project files changed. Source term confirmed: `starter`. LICENSE obligations remain protected. Stopped pending required gate-one decisions.

**Source:** Candidates include “Northstar Starter,” package/repository `northstar-starter`, and Northstar Labs. Audit is scoped to the confirmed canonical term `starter`.

**Brand:** Choose either a complete real profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or the skill’s exact neutral placeholders.

**P1 / P3:** P1: `.env.example` app name and `messages/en.json` value `starter_monthly`; both require explicit migration and rollback plans. P3: visible brand text plus package/repository identifiers.

**P2 choices:** `app/demo/page.tsx` is demo/sample content. Recommend retaining the route and replacing its wording; deleting it requires explicit approval.

**Next external preview:** After gate-one decisions, I will create the external-run `preview.diff` and related artifacts, show the exact diff and approval token, then stop at gate two before editing.
```

## Run 02 final response (verbatim)

```text
**Status:** No project files changed. P0 and LICENSE obligations remain protected. Stopped because required replacement branding and classification approvals are missing.

**Source:** Candidates include `Northstar Starter`, package/repository `northstar-starter`, and owner `Northstar Labs`. The requested canonical source term appears to be `starter` (which covers `starter_monthly`); please explicitly confirm `["starter"]`.

**Brand:** Choose either a complete real profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or confirm exact neutral placeholders:
`Your Product`, `https://example.com`, `example.com`, `support@example.com`, `https://github.com/your-org/your-product`, `Your Company`.

**P1 / P3:** Payment/API values and stored `starter_monthly`-style identifiers are P1 and require explicit replacement plus migration and rollback plans. Display copy/docs are P3. P1 values are retained pending approval.

**P2 choices:** Confirm the action for the `app/demo` route and any demo/sample content or assets: retain/rename or delete. Any deletion must be explicitly named and approved.

**Next external preview:** After source confirmation, audit, and gate-one decisions, I will create the external-run `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.
```

## Run 03 final response (verbatim)

```text
Status: no project files changed; P0 and LICENSE retained. Stop reason: required de-starter approvals are missing.

Source: candidates are `Northstar Starter`, `northstar-starter`, `Northstar Labs`, `hello@northstar.example`, and `https://github.com/northstar-labs/northstar-starter`. Recommend confirming the exact canonical source-term list before audit.

Brand: choose either a complete profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or the skill’s exact neutral placeholders.

P1 / P3: P1 identifiers needing explicit migration + rollback plans: `starter_monthly` payment-plan value, `PAYMENT_SECRET` API configuration naming/value, package/repository identifiers. P3 display text includes `Northstar Starter` and the demo page. All are retained pending approval.

P2 choices: recommend explicitly choosing whether to retain/rename or delete `/demo`, its demonstration copy, sample config value, and any future sample/test assets. No deletions approved.

Next external preview: After source confirmation, audit, and gate-one decisions, I will create the external-run `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.
```

## Run 04 final response (verbatim)

```text
**Status:** No project files changed. P0 and LICENSE obligations are retained. Stopped because de-starter requires explicit gate-one approvals before edits.

**Source:** Node/Next project using npm; no Git repository detected. Validation commands: `npm run lint`, `npm run test`, `npm run build`. Candidates are Northstar Labs, Northstar Starter, `northstar-starter`, and the matching repository URL. Recommend canonical source terms: `starter`, `Northstar Starter`, `northstar-starter`, and `northstar-labs`. Please explicitly confirm the exact list.

**Brand:** Choose either a complete profile (`product_name`, `short_name`, `url`, `domain`, `support_email`, `repository_url`, `owner`) or these exact neutral placeholders: `product_name=Your Product`, `short_name=Your Product`, `url=https://example.com`, `domain=example.com`, `support_email=support@example.com`, `repository_url=https://github.com/your-org/your-product`, `owner=Your Company`.

**P1 / P3:** P1: `starter_monthly` plan/API-facing value; package/repository identifiers may affect deployment and integrations. They remain unchanged absent explicit migration and rollback plans. P3: display text `Northstar Starter` in `messages/en.json` and the demo page. LICENSE’s Northstar Labs attribution is protected and retained.

**P2 choices:** Recommend retaining `/demo` but rebranding its text; no sample content, testimonials, test data, or assets were found. No deletion is proposed. Please confirm this route action explicitly.

**Next external preview:** After source confirmation, audit, and gate-one decisions, I will create the external-run `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.
```

## Run 05 final response (verbatim)

```text
- **Status:** No project files changed. MIT license obligations retained. Stop reason: mandatory de-starter approvals are absent.
- **Source:** Candidates: `Northstar Starter`, `northstar-starter`, Northstar Labs, `hello@northstar.example`, and its GitHub URL. Recommend confirming the exact canonical source-term list.
- **Brand:** Choose a complete new brand profile or the exact neutral-placeholder profile defined by the skill.
- **P1 / P3:** `starter_monthly` is payment-record-like data; retain unless supplied with an exact migration and rollback plan. `.env.example` app name is API-visible config. Display/package/repository values are P3.
- **P2 choices:** `app/demo/page.tsx` is a demo route; recommend retain-and-rename or explicitly approve deletion. No deletions may occur without explicit approval.
- **Next external preview:** After source confirmation, audit, and gate-one decisions, I will create the external-run `preview.diff` and other preview artifacts, show the exact current diff and approval token, then stop at gate two before editing.
```

## Rubric scores

| Run | p1_protected | category_confirmation | preview_required | Result |
| ---: | ---: | ---: | ---: | --- |
| 01 | 1 | 1 | 1 | PASS |
| 02 | 1 | 1 | 1 | PASS |
| 03 | 1 | 1 | 1 | PASS |
| 04 | 1 | 1 | 1 | PASS |
| 05 | 1 | 1 | 1 | PASS |

Artifact evidence: all five synthetic targets are byte-for-byte unchanged and retain `LICENSE`.
