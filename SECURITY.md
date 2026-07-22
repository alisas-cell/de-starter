# Security Policy

## Supported version

Security fixes currently target the latest `0.1.x` release.

## Reporting a vulnerability

Do not open a public issue when a report contains an exploit, private source identity, purchased code, credentials, exact approval tokens, or backup paths.

Use GitHub's private vulnerability reporting for this repository. Include a minimal synthetic reproduction, the affected stage (`discover`, `audit`, `preview`, `apply`, or `verify`), platform and filesystem details, and the expected fail-closed behavior.

For non-sensitive correctness bugs, use the public bug-report template and remove all private project details first.

## Security boundaries

- v0.1 automated operations require macOS/Linux POSIX no-follow support.
- Apply requires the target and external run directory to share a filesystem.
- Windows automated Apply is not supported.
- The Skill cannot replace legal review, production secret management, or real payment/data migration exercises.
