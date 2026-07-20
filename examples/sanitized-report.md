# De-starter Audit

- Project kind: `node-next`
- Git present: `false`
- Git dirty: `None`
- Findings: `11`
- Confirmed source terms: `starter_monthly, Northstar`

## Findings

| ID | Risk | Category | Location | Evidence |
| --- | --- | --- | --- | --- |
| F-ee06e91884e7 | P0 | legal-or-copyright | `LICENSE:3:20` | Copyright (c) 2026 Northstar Labs |
| F-637f700c9f21 | P1 | possible-persisted-or-public-identifier | `.env.example:1:23` | NEXT_PUBLIC_APP_NAME="Northstar Starter" |
| F-74bf3f4ae5da | P1 | possible-persisted-or-public-identifier | `messages/en.json:3:12` | "plan": "starter_monthly", |
| F-19153b285379 | P2 | user-decides-sample-content | `app/demo/page.tsx:0:0` | binary-or-path inventory: 94 bytes |
| F-d24808a9413e | P2 | user-decides-sample-content | `app/demo/page.tsx:2:16` | return <main>Northstar Starter demonstration</main>; |
| F-3c2db2686621 | P3 | display-or-metadata | `messages/en.json:2:13` | "brand": "Northstar Starter", |
| F-46c004919141 | P3 | display-or-metadata | `messages/en.json:4:21` | "support": "hello@northstar.example" |
| F-cbed632daf59 | P3 | display-or-metadata | `package.json:2:12` | "name": "northstar-starter", |
| F-b1575ce21656 | P3 | display-or-metadata | `package.json:3:14` | "author": "Northstar Labs", |
| F-683202e16c25 | P3 | display-or-metadata | `package.json:4:37` | "repository": "https://github.com/northstar-labs/northstar-starter", |
| F-52c43b7320a4 | P3 | display-or-metadata | `package.json:4:52` | "repository": "https://github.com/northstar-labs/northstar-starter", |

## Validation Plan

- `npm run lint`
- `npm run test`
- `npm run build`
