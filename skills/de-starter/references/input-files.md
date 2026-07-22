# Input-file Schemas

Write both JSON files in the external run directory. Use strict JSON: no duplicate or extra keys.

## `source-config.json`

Its complete schema is exactly `{"source_terms":[...]}`. `source_terms` is a nonempty array of nonempty, already-trimmed strings. Case-insensitively deduplicate it, retaining the lexically smallest spelling for duplicates; sort longest-first, then by case-folded spelling, then exact spelling. This is the scanner's canonical order.

```json
{"source_terms":["Northstar AI","northstar.ai","Northstar"]}
```

## `decisions.json`

Only these top-level keys are allowed: `brand_mode`, `brand_profile`, `actions`, `delete_paths`, `rename_paths`, `text_edits`. `brand_mode` is `real` or `placeholder`; `brand_profile` follows [Brand Profile](brand-profile.md). `actions` is an array of unique finding decisions:

```json
{
  "brand_mode": "placeholder",
  "brand_profile": {},
  "actions": [
    {"finding_id":"F-example","action":"keep"},
    {"finding_id":"F-p1","action":"replace","replacement":"new_key","migration_plan":"migrate stored values","rollback_plan":"restore prior values"}
  ],
  "delete_paths": ["demo"],
  "rename_paths": {"public/starter-logo.svg":"public/product-logo.svg"},
  "text_edits": [
    {
      "path":"app/page.tsx",
      "expected_sha256":"<the audited lowercase SHA-256 for app/page.tsx>",
      "start_line":1,
      "end_line":4,
      "replacement":"export default function Page() { return <main />; }\\n",
      "reason":"Remove the approved sample component import and usage"
    }
  ]
}
```

An action is `keep` or `replace`; `replace` needs `replacement`. P1 replacements also need nonempty `migration_plan` and `rollback_plan`. Under this Skill, omit P0 findings from `actions` entirely: the runtime accepts `keep`, but the product contract deliberately keeps P0 out of actions. `delete_paths` removes only an audited P2 scope after explicit confirmation. `rename_paths` maps audited P2 or path-finding source paths to distinct, project-relative destinations; an audited directory root is eligible only when the root itself is in that scope and every audited descendant is authorized. Renames cannot overlap deletes or other rename paths.

`text_edits` is an array of scoped semantic edits. Each edit requires `path`, `expected_sha256`, `start_line`, `end_line`, `replacement`, and `reason`; it may also contain `migration_plan` and `rollback_plan`. `path` must name an audited UTF-8 text file inside the project; `expected_sha256` must equal its audited lowercase SHA-256 and current file hash; `start_line` and `end_line` are inclusive positive line numbers; `replacement` is a string; and `reason` states the approved purpose. Ranges cannot overlap P0 lines, separately actioned findings, or other semantic ranges. A range that overlaps any P1 line is accepted only when both plan fields contain the real, explicitly approved migration and rollback steps; boilerplate such as “required for P1” is not an approval. Record the named path, purpose, and any P1 plans at gate one. The preview writes safe `semantic-edits.json` metadata with a `p1_migration_protected` flag, but never the replacement or plan text.
