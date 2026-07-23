# de-starter

`de-starter` is an Agent Skill, not a standalone Agent. It helps an existing coding Agent audit and safely remove starter, boilerplate, template, and SaaS-kit residue.

The real workspace stays read-only until the user reviews and explicitly approves the current preview diff.

## Quick links

- [Install](#install)
- [Five-minute synthetic public demo](examples/public-demo/README.md)
- [Sanitized real Starter experiment report（中文）](docs/real-starter-experiment-report.zh-CN.md)
- [Chinese video director script](docs/video-director-script.zh-CN.md)
- [Open a privacy-safe issue or feedback report](https://github.com/alisas-cell/de-starter/issues/new/choose)
- [Latest release: v0.1.2](https://github.com/alisas-cell/de-starter/releases/tag/v0.1.2)

Risk is reduced, not zero. Review both approval gates, use Git or a verified backup, keep the external run directory, and validate after apply. An explicitly approved wrong decision can still produce an unwanted change.

## Install

Requirements: Python 3.9+; runtime scripts use only the standard library. v0.1 automated commands require macOS/Linux POSIX no-follow support; `apply` additionally requires the project and run directory to be on the same filesystem. Windows is not supported in v0.1.

```bash
git clone https://github.com/alisas-cell/de-starter.git
mkdir -p "$HOME/.agents/skills"
cp -R de-starter/skills/de-starter "$HOME/.agents/skills/de-starter"
```

The public repository is maintained at `alisas-cell/de-starter`.

## Use

```text
$de-starter Audit this repository and show the report and proposed diff before making changes.
```

The Skill discovers source identities, asks for a real brand or neutral placeholders, produces separate file and source-named-directory audits, records Demo/sample decisions and explicitly scoped semantic edits, generates a project-external preview, stops for approval, applies only the approved token, validates the project, and scans again. Semantic edits require an audited file hash, inclusive line range, replacement, and a named purpose at gate one. P0 lines remain immutable; a P1-overlapping range additionally requires approved nonempty migration and rollback plans. Safe metadata records the migration-protection state in `semantic-edits.json` for gate two without exposing replacement or plan text.

## Try the public demo

Follow the [five-minute synthetic walkthrough](examples/public-demo/README.md) to reproduce audit, both approval gates, wrong-token refusal, stale-preview refusal, approved apply, classified verification, and recovery evidence without touching a purchased Starter.

Risk is reduced, not zero. Run de-starter only with Git or a verified backup, review both approval gates, keep the external run directory, and validate after apply. A wrong decision that the user explicitly approves can still produce an unwanted change. The public demo is fictional and contains no purchased Starter source or proprietary asset.

`cleanup_empty_dirs` is a separate permission. The directory must have an exact audit finding and explicit approval, and it must already be empty or become empty only through approved descendant operations. Apply never substitutes `rmdir` or global empty-directory cleanup: it binds directory state and identity to the preview token, then moves the exact directory into external backup with no-clobber transaction and rollback evidence. Ordinary unnamed empty directories remain untouched.

If an approved rename needs new parent directories, `apply` creates them exclusively through no-follow descriptors after the final checks, records them in `restore.json`, and removes only transaction-owned empty parents during rollback.

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

Current public verification: 214/214 full regression tests, including 19 public-demo workspace, lifecycle, refusal, documentation, media, privacy, and reset-boundary checks; 13/13 core CLI lifecycle tests; and a five-sample fresh-context pressure scenario improving from baseline 0/5 to final 5/5.

`v0.1.2` adds the synthetic public lab, refusal evidence, documentation, media, and tests. Production Skill behavior is unchanged from `v0.1.1`.

## Public evidence

- [Sanitized real-run acceptance summary](examples/sanitized-real-run-summary.md)
- [真实 Starter 实验报告（中文）](docs/real-starter-experiment-report.zh-CN.md)
- [中文视频导演稿](docs/video-director-script.zh-CN.md)
- [视频镜头清单（中文）](docs/video-shot-list.zh-CN.md)
- [自媒体发布完整包（中文）](docs/self-media-package.zh-CN.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Use synthetic fixtures. Never commit purchased Starter code, proprietary assets, secrets, production identifiers, exact tokens, or reports containing private source excerpts.

For sensitive reports, follow [SECURITY.md](SECURITY.md) and use private vulnerability reporting.

## License

MIT
