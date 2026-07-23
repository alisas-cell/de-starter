# Five-minute public demo

This walkthrough uses a tiny fictional project owned by `Northstar Labs`. It contains deliberately planted P0, P1, P2, P3, source-named asset, and empty-directory evidence. It contains no purchased Starter code or proprietary asset.

Risk is reduced, not zero. Use de-starter on a real project only with Git or a verified backup, review both approval gates, keep the external run directory, and validate after apply. A wrong decision that the user explicitly approves can still produce an unwanted change.

Requirements: Python 3.9+, macOS or Linux, and a clone of this repository. The demo does not install packages or use the network.

## 1. Prepare an isolated synthetic project

Run these commands from the repository root:

```bash
DEMO=/tmp/de-starter-public-demo
PROJECT="$DEMO/project"
RUN="$DEMO/run"

python3 examples/public-demo/demo.py prepare --workspace "$DEMO"
python3 examples/public-demo/demo.py inventory --workspace "$DEMO"
```

The helper refuses a nonempty unowned destination. It creates `project` and the external `run` directory as siblings under the disposable workspace. It also creates two empty directories:

- `public/starter`, which is eligible only after separate `cleanup_empty_dirs` approval;
- `public/uploads`, an ordinary empty directory that must remain untouched.

## 2. Discover and confirm the fictional source identity

```bash
python3 skills/de-starter/scripts/destarter.py discover \
  --project "$PROJECT" \
  --run-dir "$RUN"

sed -n '1,160p' examples/public-demo/source-config.example.json
```

The example contains only the fictional identity planted in the seed. Reviewing it is the demo's source-confirmation step. Copy it only after the list matches what you just inspected:

```bash
cp examples/public-demo/source-config.example.json "$RUN/source-config.json"

python3 skills/de-starter/scripts/destarter.py audit \
  --project "$PROJECT" \
  --run-dir "$RUN" \
  --source-config "$RUN/source-config.json"

sed -n '1,260p' "$RUN/audit.md"
```

Expected audit: P0 copyright, P1 environment/billing identifiers, P2 demo material, P3 display/metadata residue, and one source-named empty directory. The correct goal is not zero findings: P0 and retained P1 evidence should remain.

## 3. Review gate one decisions

```bash
sed -n '1,260p' examples/public-demo/decisions.example.json
```

The fixed decision file contains only IDs from this exact synthetic seed. It deliberately:

- leaves P0/LICENSE and P1 `starter_monthly` untouched;
- replaces selected P3 display and repository values with neutral placeholders;
- deletes the explicitly approved P2 `app/demo` path;
- renames the explicitly approved local sample asset;
- separately approves only `public/starter` for empty-directory cleanup.

It is not a decision template for another project. After reviewing every entry, copy it into the external run directory:

```bash
cp examples/public-demo/decisions.example.json "$RUN/decisions.json"
```

## 4. Create and review gate two preview

```bash
python3 skills/de-starter/scripts/destarter.py preview \
  --project "$PROJECT" \
  --run-dir "$RUN" \
  --decisions "$RUN/decisions.json"

sed -n '1,260p' "$RUN/preview.md"
```

Before applying, review the private `preview.diff` locally as well as `binary-changes.json`, `placeholders.json`, `semantic-edits.json`, protected items, retained items, validation commands, and unresolved findings. Do not post the private diff or token online.

The preview command prints the current approval token on its final line. Do not extract it with command substitution or pipe it directly into `apply`.

## 5. Optional refusal exercise: wrong token

Record the project inventory, submit an intentionally wrong value, and compare the inventory again:

```bash
python3 examples/public-demo/demo.py inventory --workspace "$DEMO"

python3 skills/de-starter/scripts/destarter.py apply \
  --project "$PROJECT" \
  --run-dir "$RUN" \
  --approval-token intentionally-wrong-demo-token

python3 examples/public-demo/demo.py inventory --workspace "$DEMO"
```

Expected: `approval failed`, no backup directory, no `apply-result.json`, and identical project inventories.

## 6. Apply only the reviewed current preview

Now paste the exact token yourself. The visible placeholder below is intentionally not usable:

```bash
TOKEN='PASTE_THE_CURRENT_PREVIEW_TOKEN_HERE'

python3 skills/de-starter/scripts/destarter.py apply \
  --project "$PROJECT" \
  --run-dir "$RUN" \
  --approval-token "$TOKEN"
```

If any audited project state changed after preview, the old token is rejected before approved edits begin.

## 7. Verify expected retained findings

```bash
python3 skills/de-starter/scripts/destarter.py verify \
  --project "$PROJECT" \
  --run-dir "$RUN" \
  --source-config "$RUN/source-config.json"

python3 examples/public-demo/demo.py check --workspace "$DEMO"
```

For this demo, exit code 3 is expected from `verify`: legal evidence, the retained P1 billing key, and deliberately retained evidence still exist. The `check` command independently confirms the approved scope, including:

- LICENSE bytes unchanged;
- `starter_monthly` unchanged;
- approved P2 path removed;
- selected P3 values neutralized;
- `public/starter` removed;
- ordinary `public/uploads` retained;
- backup, `restore.json`, `reverse.diff`, and `apply-result.json` present outside the project.

These are recovery artifacts and transaction evidence. v0.1.1 has no one-command restore operation; do not describe it as one. Preserve the run directory and use Git or the verified byte backup if restoration is required.

## 8. Optional refusal exercise: stale preview

Use a fresh disposable workspace and repeat through preview. Then run:

```bash
python3 examples/public-demo/demo.py tamper --workspace "$DEMO"
```

Submitting the previously printed token must return `approval failed`. The helper can alter only the fixed synthetic `messages/en.json` inside a valid demo sentinel; it refuses arbitrary projects. Reset and prepare again before the success path.

## 9. Remove only the disposable lab

```bash
python3 examples/public-demo/demo.py reset --workspace "$DEMO"
```

Reset requires the exact sentinel and refuses unowned directories, filesystem roots, the home directory, and this repository root.
