# de-starter

`de-starter` is an Agent Skill, not a standalone Agent. It helps an existing coding Agent audit and safely remove starter, boilerplate, template, and SaaS-kit residue.

The real workspace stays read-only until the user reviews and explicitly approves the current preview diff.

## Install

Requirements: Python 3.9+; runtime scripts use only the standard library. v0.1 automated commands require macOS/Linux POSIX no-follow support; `apply` additionally requires the project and run directory to be on the same filesystem. Windows is not supported in v0.1.

```bash
git clone https://github.com/YOUR_ACCOUNT/de-starter.git
mkdir -p "$HOME/.agents/skills"
cp -R de-starter/skills/de-starter "$HOME/.agents/skills/de-starter"
```

Replace `YOUR_ACCOUNT` with the repository owner after publication.

## Use

```text
$de-starter Audit this repository and show the report and proposed diff before making changes.
```

The Skill discovers source identities, asks for a real brand or neutral placeholders, produces an audit, records Demo/sample decisions and explicitly scoped semantic edits, generates a project-external preview, stops for approval, applies only the approved token, validates the project, and scans again. Semantic edits require an audited file hash, inclusive line range, replacement, and a named purpose at gate one; their safe metadata is written to `semantic-edits.json` for gate two.

## Risk levels

| Risk | Default |
| --- | --- |
| P0 legal/secrets/production data | Report and keep |
| P1 persisted/payment/auth/API identifiers | Keep unless migration and rollback are explicit |
| P2 Demo/sample/testimonial/test data/assets | User category decision |
| P3 display brand/SEO/email/repository metadata | Eligible for preview |

## Artifacts

Each run writes `audit.md`, `audit.json`, `preview.md`, private `preview.diff`, `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, `manifest.json`, backups, `reverse.diff`, and `restore.json` outside the target project. Git is optional; non-Git projects use hashes and verified backups. Use redacted screenshots or summaries for public updates; do not publish the full diff or source excerpts.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skills/de-starter/scripts
```

## Contributing

Use synthetic fixtures. Never commit purchased Starter code, proprietary assets, secrets, production identifiers, or reports containing private source excerpts.

## License

MIT
