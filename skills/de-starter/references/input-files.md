# Input-file Schemas

Write both JSON files in the external run directory. Use strict JSON: no duplicate or extra keys.

## `source-config.json`

Its complete schema is exactly `{"source_terms":[...]}`. `source_terms` is a nonempty array of nonempty, already-trimmed strings. Case-insensitively deduplicate it, retaining the lexically smallest spelling for duplicates; sort longest-first, then by case-folded spelling, then exact spelling. This is the scanner's canonical order.

```json
{"source_terms":["Northstar AI","northstar.ai","Northstar"]}
```

## `decisions.json`

Only these top-level keys are allowed: `brand_mode`, `brand_profile`, `actions`, `delete_paths`, `rename_paths`. `brand_mode` is `real` or `placeholder`; `brand_profile` follows [Brand Profile](brand-profile.md). `actions` is an array of unique finding decisions:

```json
{
  "brand_mode": "placeholder",
  "brand_profile": {},
  "actions": [
    {"finding_id":"F-example","action":"keep"},
    {"finding_id":"F-p1","action":"replace","replacement":"new_key","migration_plan":"migrate stored values","rollback_plan":"restore prior values"}
  ],
  "delete_paths": ["demo"],
  "rename_paths": {"public/starter-logo.svg":"public/product-logo.svg"}
}
```

An action is `keep` or `replace`; `replace` needs `replacement`. P1 replacements also need nonempty `migration_plan` and `rollback_plan`. Under this Skill, omit P0 findings from `actions` entirely: the runtime accepts `keep`, but the product contract deliberately keeps P0 out of actions. `delete_paths` removes only an audited P2 scope after explicit confirmation. `rename_paths` maps audited P2 or path-finding source paths to distinct, project-relative destinations; it cannot overlap deletes or other rename paths.
