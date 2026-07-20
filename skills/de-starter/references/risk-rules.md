# Risk Rules

Classify by location, surrounding syntax, persistence, and dependencies. A keyword alone never determines risk.

| Risk | Default | Examples |
| --- | --- | --- |
| P0 protected | Report and keep | LICENSE, copyright, notices, secrets, production data |
| P1 high risk | Keep unless migration and rollback are explicit | `starter_monthly`, payment IDs, database enums, auth keys, API routes, environment-variable names |
| P2 user decision | Present by category and recommend an ordinary choice | Demo routes, sample assets, testimonials, example blogs, test data |
| P3 display residue | Eligible for preview | UI brand names, SEO, email signatures, repository links, package descriptions |

Precedence is P0, then P1, then P2, then P3. A payment key inside a Demo file remains P1. A source-author name inside LICENSE remains P0.

P0 never enters actions, and any path containing a P0 finding is retained. Preserve all license obligations; ask when they are unclear. P1 has no action unless the user explicitly confirms both a migration plan and a rollback plan. Never delete a path containing P0 or P1 findings.

Present P2 choices by category, including demo routes, sample content, testimonials, test data, and assets. Make a sensible P2 recommendation when the user delegates a choice, but require explicit confirmation before deletion. Record every selected category action in the decisions file.

Treat generated files as derived: change their source and run the repository generator. P3 changes remain proposals until the user approves the exact current preview.
