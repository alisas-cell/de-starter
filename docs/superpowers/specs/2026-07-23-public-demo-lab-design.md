# Public Demo Lab Design

Date: 2026-07-23
Status: approved by the user on 2026-07-23

## Purpose

Add a small, fully synthetic project that lets a beginner reproduce the de-starter safety workflow without seeing or receiving any purchased Starter source. The demo must prove both positive behavior and refusal behavior: approved residue changes, protected content remains, wrong or stale approval cannot edit, and every applied byte has external recovery evidence.

The demo is evidence for the existing Skill, not a second implementation of de-starter and not a replacement for the real Starter experiment report.

## Considered approaches

### A. Public demo lab inside this repository — selected

Commit a synthetic seed project, a small Python helper for creating/resetting a disposable working copy, guided documentation, and automated acceptance tests.

Advantages:

- one GitHub repository and one clone command;
- reuses the published CLI rather than imitating it;
- supports repeatable screenshots and video recording;
- keeps the purchased Starter completely outside the public repository;
- can run in CI on the same Python matrix as the Skill.

Trade-off: the repository gains a small amount of example-only code and documentation.

### B. Use the existing unit-test fixture directly

This would add almost no files, but the fixture is optimized for tests rather than learning. It does not explain approval decisions, distinguish expected remaining findings, or provide a safe beginner workflow.

### C. Publish a second demo repository

This gives the demo an independent URL but doubles versioning, CI, issue tracking, and release maintenance. It is unnecessary for the first public version.

## Repository layout

Add these public, synthetic resources outside `skills/de-starter`:

```text
examples/public-demo/
├── README.md
├── demo.py
├── decisions.example.json
└── seed/
    ├── LICENSE
    ├── app/demo/page.tsx
    ├── app/page.tsx
    ├── messages/en.json
    ├── package.json
    └── public/starter-logo.svg
```

The helper creates an untracked disposable project and external run directory under a caller-selected temporary parent. It also creates the intentionally empty source-named directory at runtime because Git cannot commit empty directories. A sentinel identifies helper-owned demo workspaces. The helper must refuse repository roots, filesystem roots, missing sentinels for destructive reset, and nonempty destinations it did not create.

The demo remains framework-light: fixture files resemble a small Next.js project, but the walkthrough depends only on Python 3.9+ and the standard-library CLI. It does not install Node packages or contact the network.

## Synthetic evidence model

Use the fictional seller identity `Northstar Labs` and source terms that cannot be mistaken for the user's real purchased Starter.

The seed covers:

| Level | Synthetic example | Demo decision |
| --- | --- | --- |
| P0 | seller copyright in `LICENSE` | protected and unchanged |
| P1 | persisted billing key such as `starter_monthly` | explicitly retained; no fake migration plan |
| P2 | demonstration route and local sample asset | explicitly deleted or renamed after review |
| P3 | display brand, support address, repository metadata | replaced with exact neutral placeholders |
| Directory residue | empty `public/starter/` created at prepare time | independently approved and transactionally backed up |

The fixture must also retain at least one ordinary empty directory so the demo can prove global empty-directory cleanup did not occur.

## User workflow and approval gates

The beginner path is intentionally staged:

1. `demo.py prepare` creates a disposable project and a disjoint external run directory.
2. The user invokes the real CLI `discover` and `audit` commands.
3. The guide explains the audit and asks the user to inspect a copied decisions template. It does not say that the helper or Agent has approved anything.
4. The user invokes `preview`, reads the rendered preview and private diff locally, and copies the exact current token.
5. An optional refusal exercise submits a wrong token and confirms that the project hash inventory did not change.
6. The user explicitly invokes `apply` with the exact token.
7. The user runs `verify`. Exit code 3 is expected because P0, retained P1, and other intentionally retained findings remain.
8. The guide inspects external backup, `restore.json`, and `reverse.diff`; it describes these as recovery evidence. It does not claim that v0.1.1 has a one-command user restore operation.
9. `demo.py reset` removes only helper-owned disposable demo paths after sentinel and boundary validation.

No quick-start command may discover, decide, preview, extract a token, and apply in a single unattended pipeline. That would teach users to bypass the Skill's safety contract.

## Safety refusal exercises

Two repeatable exercises are required:

1. **Wrong token:** apply must fail before any project write, and a before/after inventory must match.
2. **Stale preview:** after preview, a helper-owned demo file is deliberately changed; apply with the previously valid token must fail before partial edits. Reset recreates the disposable project.

The helper may stage the deliberate stale change only inside a sentinel-marked demo workspace. It may not accept arbitrary project paths for this operation.

The demo also checks these invariants after a successful apply:

- `LICENSE` bytes match the prepared baseline;
- the retained P1 billing key is unchanged;
- approved P3 values use the exact neutral placeholders;
- only approved P2 paths changed or disappeared;
- the approved source-named empty directory is absent;
- the ordinary unnamed empty directory remains;
- backup and restore artifacts exist outside the project;
- verification reports remaining findings honestly.

## Automated tests

Follow test-first development. Add public-demo tests before the helper implementation and observe the expected failures.

Test categories:

1. preparation creates the expected synthetic tree, sentinel, empty directories, and disjoint run directory;
2. preparation refuses unsafe or preexisting destinations;
3. reset refuses any directory without the exact sentinel and removes only helper-owned paths;
4. the documented audit/preview/apply/verify lifecycle succeeds with the expected exit codes and artifacts;
5. wrong-token and stale-preview exercises leave no partial approved edits;
6. post-apply invariants prove P0/P1 preservation and scoped P2/P3/directory changes;
7. repository privacy scan rejects known private-path, token, credential, and purchased-source patterns in all new demo files.

The existing 195-test suite must remain green. The demo tests join the normal `unittest discover` run and GitHub Actions matrix.

## Documentation and media updates

Update the repository README with:

- a five-minute public demo entry point;
- a prominent safety boundary: low risk is not zero risk;
- prerequisites: use Git or a verified backup, review both gates, keep the external run directory, validate after apply;
- an explicit statement that v0.1.1 is macOS/Linux only and that the demo never touches the purchased Starter.

Update the Chinese self-media package, production log, and shot list with a continuous demo sequence. Capture only the synthetic project. Screens must redact the approval token and any absolute machine path. The video should distinguish:

- transaction rollback on failed apply;
- external byte backup and restore evidence;
- a future optional restore command, which does not exist in v0.1.1.

## Success criteria

The feature is complete only when:

- a fresh clone can prepare and run the synthetic demo without network access;
- a beginner can follow the README without editing the purchased Starter;
- wrong-token and stale-preview safety exercises demonstrably perform zero partial approved edits;
- the success path changes only the approved scope and emits recovery evidence;
- full tests, Skill validation, compile checks, links, privacy scan, and Git diff checks pass;
- updated public screenshots contain no private source, absolute machine path, or usable token;
- GitHub CI passes before the demo is described as released.

## Non-goals

- Do not publish or reconstruct the purchased Starter.
- Do not add a second cleanup engine.
- Do not automate user approval or token extraction.
- Do not add Windows support in this increment.
- Do not add a user-facing restore command in this increment.
- Do not claim zero risk, perfect safety, or universal compatibility.
