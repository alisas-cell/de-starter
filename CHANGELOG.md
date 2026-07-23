# Changelog

## 0.1.1 - 2026-07-23

- Made the preview-root identity regression portable to Linux filesystems that may immediately reuse an inode, while continuing to verify identity-bound tokens and explicit keep decisions.
- Updated GitHub Actions to the official Node 24 runtimes and verified the Python 3.9, 3.11, and 3.13 matrix without annotations.
- No production Skill behavior changed from v0.1.0.

## 0.1.0 - 2026-07-23

- Added deterministic source-identity and residue scanning.
- Added P0–P3 contextual risk classification and secret redaction.
- Added mandatory audit-scope and preview-diff approval gates.
- Added project-external preview, hash validation, backups, reverse diff, and restore manifest.
- Added Node/Next.js detection plus safe generic fallback.
- Added baseline and forward evaluation for Skill behavior.
- Added separate source-named directory auditing and explicit `cleanup_empty_dirs` decisions.
- Added token-bound directory state/identity, no-clobber transactional cleanup, and parent-first rollback.
- Added token-free hash-bound preview summaries and restore/apply evidence for empty directories.
- Added repeated fresh-context pressure evaluation, full tracked-tree privacy checks, and sanitized real acceptance evidence.
