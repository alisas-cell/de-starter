# Sanitized real-run acceptance summary

This case study records a real acceptance run against a purchased, production-oriented Next.js Starter. Product identity, private paths, source excerpts, assets, approval tokens, and credentials are intentionally omitted.

## Outcome

The run removed the approved seller identity and presentation residue while retaining authentication, billing, credits, AI generation, administration, localization, legal obligations, and working demo capabilities.

| Measure | Before | After | Interpretation |
| --- | ---: | ---: | --- |
| Audited findings | 523 | 227 | 296 findings resolved; 56.6% reduction |
| P0 protected evidence | 132 | 132 | Legal and possible-secret evidence remained immutable |
| P1 compatibility-sensitive identifiers | 52 | 35 | Only explicitly migrated identifiers changed |
| P2 user-decides samples and paths | 52 | 21 | Approved samples were removed or renamed; useful demos were retained |
| P3 display and metadata text | 287 | 39 | Seller-facing identity was neutralized; approved billing vocabulary remained |
| Source-named directory residue | 1 | 0 | One separately approved empty directory was transactionally moved into external backup |

The 227 remaining findings are not reported as “missed residue.” They were classified as:

- 132 P0 protected findings, including legal/copyright evidence and possible-secret-shaped code or configuration names;
- 35 P1 billing, storage, and persisted identifiers retained for compatibility;
- 21 P2 working demo routes and local sample assets the user chose to keep;
- 39 P3 billing-plan vocabulary plus one explicitly retained generic package keyword.

## Approved operation set

- 72 changed output paths
- 4 approved deletions
- 2 approved directory renames
- 122 hash-bound semantic edits across 51 paths
- 14 P1 edits with explicit migration and rollback plans
- 0 P0 or LICENSE mutations
- 1 independently approved `cleanup_empty_dirs` operation

The original bytes were moved into external backup before each transaction completed. The first transaction's 64 objects and the later empty-directory object passed descriptor-based identity and content-state verification; both runs produced restore manifests and reverse diffs.

## Validation

| Check | Result |
| --- | --- |
| Lint | Passed |
| Tests | 63 of 65 passed; the same two inherited documentation-link tests failed before and after |
| New test failures | 0 |
| Production build | Passed; 71 pages generated |
| Final file-residue verification | 227 findings, all classified as protected or intentionally retained |
| Final directory-residue verification | 0 source-named directory findings |
| Applied tree | Exact match to the token-bound preview after temporary build outputs were removed |

The build emitted the expected isolated-environment warning for a missing authentication secret. No real secret was supplied for acceptance testing.

## What this proves

The useful claim is not “all occurrences of the word starter disappeared.” A safe de-starter run must distinguish seller residue from legal evidence, secrets, database or billing identifiers, and working samples. This run demonstrates the full two-gate lifecycle: read-only audit, separate file/directory findings, named scope approval, exact diff approval, transactional apply, external backup, validation, and classified residue verification.

## Privacy boundary

This public summary contains only aggregate results and generic descriptions. The detailed audit, exact diff, target paths, source terms, token, backup map, reverse diff, and private screenshots remain outside the Git repository.
