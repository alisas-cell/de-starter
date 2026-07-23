# Changelog

## 0.1.2 - 2026-07-23

- Added a fully synthetic public demo lab with sentinel-owned prepare, inventory, stale-preview exercise, post-apply checks, and safe reset commands.
- Added a staged five-minute walkthrough that preserves both human approval gates and never auto-extracts or submits a preview token.
- Added wrong-token and stale-preview refusal tests proving zero partial approved edits, plus protected P0/P1 and ordinary-empty-directory invariants on the success path.
- Added an explicit non-zero-risk safety boundary, a redacted 16:9 evidence card, and updated Chinese self-media materials.
- Expanded the full regression suite from 195 to 214 tests. No production Skill behavior changed from v0.1.1.

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
