# Protected Semantic Edits Design

## Context

The private Starter acceptance run proved that exact source-term replacements and whole-path operations are insufficient for a complete de-starter workflow. Removing a fabricated testimonial component also requires removing its imports and JSX usage. Replacing a source course URL does not by itself turn the surrounding course promotion into neutral product copy.

The real Starter must remain unchanged until the user approves the exact external preview and token. The public Skill must remain generic and must not contain private project names, paths, source excerpts, or assets.

## Decision

Add guarded, line-range semantic edits to `decisions.json`. The Agent may author these edits only after gate-one scope approval. The runtime applies them only to the external preview copy, includes their exact result in the preview diff and approval token, and later applies only the approved preview bytes.

This is preferred over accepting unified diff files because Python standard-library patch parsing would require path, fuzz, rename, and binary semantics that v0.1 does not need. It is preferred over directly editing the preview tree because an explicit decision file remains deterministic, reviewable, and reproducible.

## Input Contract

Add `text_edits` to the allowed top-level `decisions.json` keys:

```json
{
  "text_edits": [
    {
      "path": "app/page.tsx",
      "expected_sha256": "64-lowercase-hex-characters",
      "start_line": 12,
      "end_line": 15,
      "replacement": "",
      "reason": "Remove the approved sample testimonial component usage",
      "migration_plan": "required when the selected range overlaps P1",
      "rollback_plan": "required when the selected range overlaps P1"
    }
  ]
}
```

Line numbers are one-based and inclusive. An empty replacement deletes the selected lines. Insert-only edits, binary edits, fuzzy matching, and patch application are outside v0.1. Multiple edits in one file are allowed only when their original line ranges do not overlap.

`expected_sha256` must equal both the audited file hash and the current project file hash. `reason` must be a nonempty, user-reviewable description. `migration_plan` and `rollback_plan` are optional for ordinary semantic edits and both mandatory when the range overlaps P1. The replacement and plan text remain private inside the external run directory; public artifacts expose only safe aggregate metadata.

## Validation and Protection Rules

The decision loader must reject a semantic edit when any of these conditions holds:

- the path is absolute, escapes the project, is absent from the audit inventory, or resolves through a symlink;
- the path is a directory, binary file, ignored dependency/build path, secret file, LICENSE, NOTICE, COPYING, or another invariant-protected path;
- the expected hash is malformed or differs from the audit;
- the line range is invalid, outside the original file, or overlaps another semantic edit;
- the range overlaps any P0 finding line;
- the range overlaps a P1 finding line without both a nonempty migration plan and a nonempty rollback plan;
- the range overlaps an existing finding-based replacement action;
- the replacement or reason has the wrong JSON type.

P1 changes may use either the existing finding action or a hash-bound semantic edit with explicit migration and rollback plans. Semantic edits cannot bypass that gate and cannot overlap a separately actioned finding. P0 remains immutable.

The Skill must name every semantic-edit path and purpose at gate one. Deletions and renames retain their existing explicit-approval rules. Gate two remains the authority for the exact resulting bytes.

## Preview Data Flow

1. Load the current audit and validate every existing action, path operation, and semantic edit against the original audit inventory.
2. Copy the project into the guarded external preview tree.
3. Apply existing finding replacements using original line and column coordinates.
4. Apply semantic edits from the bottom of each file upward so original line coordinates remain stable.
5. Apply approved renames and deletions.
6. Generate the complete redacted `preview.diff`, preview hashes, protected/retained lists, placeholder report, and a safe `semantic-edits.json` containing only path, original range, reason, before/after hashes, and the boolean `p1_migration_protected` marker. Do not expose replacement or plan text in this safe metadata.
7. Bind semantic-edit intent metadata, including the exact private migration/rollback plans, and the resulting preview file hashes into the approval token.

The original project is not written during this flow. Any source, audit, decision, preview, or manifest change invalidates the current approval token.

## Apply and Recovery

The existing apply transaction continues to copy approved bytes from the preview tree. Semantic edits therefore use the same final-entry source rechecks, verified external backups, atomic replacement, rollback, restore manifest, and reverse diff as finding replacements.

No new direct-to-project editing path is introduced. A stale source hash, changed mode, late secret, preview tampering, or backup failure aborts before an unapproved result can be committed.

## Reporting

Private acceptance produces a written before/after effect audit in the external run directory. It records aggregate P0/P1/P2/P3 counts, changed/deleted/renamed paths, validation commands, remaining protected findings, placeholders, backup location, and restore instructions. It may name the private target but must not reproduce purchased source or asset contents.

The public repository produces two sanitized written deliverables:

- `examples/sanitized-real-run-summary.md`: aggregate real-world acceptance evidence with private identities and paths removed;
- `docs/video-kit.zh-CN.md`: a beginner-friendly Chinese self-media package written as an honest first-Skill learning and growth story, not as an expert-only product launch.

The video kit must contain:

- a plain-language glossary for Agent, Skill, Agent Skill, audit, diff, hash, approval token, backup, and rollback;
- a recommended 8–12 minute long-video structure with a complete first-person spoken script;
- a 60–90 second short-video version and an opening hook that does not overpromise;
- a step-by-step screen-demo runbook pairing every screen action with narration, expected output, and a fallback if the command or approval gate differs;
- a product-first story arc: what the Skill is, why an ordinary one-off conversation is not enough, what problems the Skill solves, its concrete capabilities, where it is safer or more convenient, who should use it, and what the before/after audit proves;
- a concise secondary learning thread covering why the Skill was built, what failed during the real Starter test, and how that failure improved the safety design, without turning the video into a development tutorial;
- installation and usage instructions suitable for a first-time GitHub and Codex Skill user;
- at least five title options, cover-text options, a platform description, chapter timestamps, suggested tags, a pinned comment, a GitHub call to action, and a beginner FAQ;
- transparent limitations and disclosures: legal attribution can remain, P1 identifiers may remain, neutral placeholders are not a production brand, the purchased source is not published, and AI assisted the design and implementation.

The tone must be conversational, patient, and concrete. It should share decisions, mistakes, and learning rather than imply effortless automation. Every technical term must be explained before it is used as proof of safety or effectiveness.

The recommended editorial balance is:

- 60%: what the Skill is, why it is needed, problems solved, concrete functions, advantages, and suitable or unsuitable scenarios;
- 25%: the sanitized real-Starter P0–P3 audit, proposed changes, retained protections, and verified before/after effect;
- 10%: installation, invocation, the two approval gates, and how to read the output;
- 5%: the creator's first-Skill learning and growth reflections.

The capability explanation must cover, in beginner language:

- source-identity discovery rather than blind replacement of the word `starter`;
- P0 protection for licenses, copyright, possible secrets, and production data;
- P1 protection for payment, plan, database, authentication, API, route, and environment identifiers unless migration and rollback are explicit;
- P2 user decisions for demo routes, sample assets, testimonials, example content, tests, and other product-dependent material;
- P3 replacement candidates such as visible brand copy, SEO, emails, README, documentation, social links, repository metadata, and package identity;
- complete real-brand mode versus exact neutral-placeholder mode;
- external read-only audit and preview, an exact diff and approval token, stale-source protection, backup, rollback, validation, and post-cleanup verification;
- honest remaining-residue reporting instead of claiming that every literal occurrence can or should be removed.

The video must also add useful material beyond the requested basics: a comparison with a normal chat request, a decision guide for choosing retain/replace/delete, common mistakes, a safety checklist before approval, unsuitable scenarios, and a short roadmap for future versions.

The public Skill, example, and video kit must pass a private-name and live-looking-secret scan before GitHub publication.

After the real GitHub remote is explicitly approved and published, replace repository URL placeholders in the video description, pinned comment, installation commands, and final call to action with the confirmed public URL. Do not guess the user's account, organization, repository name, or visibility.

### Screenshot capture and script embedding

Capture visual evidence as each milestone becomes available so the creator does not need to recreate the Skill run or re-record missing screens later.

- Store private full-detail evidence under the external run directory in `screenshots/private/`; never commit it.
- Store public, sanitized 16:9 PNG images under `docs/assets/video/` and commit only images rendered from sanitized text or synthetic fixtures.
- Maintain `docs/video-shot-list.zh-CN.md` with screenshot ID, milestone, source artifact, privacy class, on-screen focus, matching narration, and final filename.
- Embed every public screenshot directly at the relevant position in `docs/video-kit.zh-CN.md`, followed by explicit editing directions such as display duration, crop/focus area, and the sentence spoken over it.
- Capture at minimum: initial audit summary, P0–P3 explanation, safety regression test, exact-preview summary, approval gate, post-cleanup validation, before/after comparison, remaining protected findings, restore artifacts, and the published GitHub repository page.
- Do not publicly screenshot raw purchased code, private absolute paths, source assets, secrets, live-looking product identifiers, approval tokens, or unredacted diffs. Render a sanitized explanatory card or synthetic equivalent instead.
- Record the safe text source used to render each public PNG so a later wording correction does not require repeating the private Starter run.

The video kit is not complete while a referenced screenshot is missing, uses a temporary filename, lacks its matching narration, or has not passed the public privacy scan and visual inspection.

## Private Acceptance Scope

After implementation, rerun the audit against the unchanged Starter. The recommended preview will:

- retain authentication, billing, credits, AI generation, admin, docs, and chat/image/video demo capabilities;
- retain LICENSE and P1 plan/payment/auth/storage identifiers;
- remove fabricated testimonial presentation and obsolete source-course promotion through explicitly approved path deletions and semantic edits;
- replace user-facing brand, repository, social, SEO, email, documentation, and package residue with the confirmed neutral profile;
- retain local demo media while renaming source-branded asset paths and updating references;
- preserve tests, replacing only source-specific fixture values where necessary.

The private effect report must list the real target's findings by P0, P1, P2, and P3 with paths, categories, decisions, and before/after counts. The public case study and video may use category names, aggregate counts, safe filenames, and product-function descriptions, but must omit purchased source excerpts, asset contents, private paths, secrets, and live-looking identifiers.

The Starter is modified only after the user approves the exact current preview diff and token. After apply, run `pnpm lint`, `pnpm test`, `pnpm build`, and the residue verifier. Unexpected P3 residue returns to a new preview cycle.

## Test Strategy

Use test-driven development. Required tests cover:

- valid deletion and replacement of exact text line ranges in the preview copy while the source remains byte-identical;
- stale or malformed hashes, invalid ranges, overlap, traversal, symlinks, binaries, ignored/secret/legal paths, P0 overlap, and P1 overlap without both plans;
- conflicts with finding-based actions and multiple bottom-up edits in one file;
- token changes when semantic intent or result changes;
- tampered preview and changed project rejection during apply;
- backup, rollback, reverse diff, report redaction, and private replacement non-disclosure;
- the complete existing test suite and the private Starter audit/preview lifecycle.

## Success Criteria

- A semantic cleanup can remove a component import/usage or an obsolete copy block without direct project edits.
- P0 findings cannot be changed; P1 findings change only through an explicitly migration-protected action or semantic range.
- The preview is deterministic and the approval token binds the exact result.
- The real Starter remains unchanged until gate two.
- The post-apply Starter validations pass and remaining findings are explicitly documented.
- The GitHub release contains the generic Skill, sanitized evidence, and Chinese video materials without private-source leakage.

## Non-Goals

- No Windows support in v0.1.
- No binary content editing, fuzzy patching, arbitrary shell hooks, or direct preview-tree mutation.
- No automatic LICENSE rewriting or P1 migration.
- No invented production brand or automatic GitHub publication.
