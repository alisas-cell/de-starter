# Contributing

Thank you for helping improve `de-starter`.

## Before opening a change

- Use synthetic fixtures only.
- Never commit purchased Starter code, private audit output, exact approval tokens, credentials, machine-specific paths, or proprietary assets.
- Keep P0 immutable and preserve the two approval gates.
- Treat file findings and source-named directory residue as separate dimensions.
- Add a failing regression before changing safety-sensitive behavior.

## Local checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/de-starter-pyc python3 -m compileall -q skills/de-starter/scripts tests
python3 skills/de-starter/scripts/destarter.py --help
git diff --check
```

## Pull requests

Describe:

1. the failure or missing behavior;
2. the RED evidence;
3. the smallest implementation change;
4. regression and compatibility results;
5. privacy review performed;
6. any change to approval, backup, rollback, or platform guarantees.

Security-sensitive changes should include deterministic failure injection or race coverage. Do not weaken fail-closed behavior to make a fixture pass.

## Feedback without a code change

Use the [Feedback Issue Form](https://github.com/alisas-cell/de-starter/issues/new/choose). Describe the project category and stage, but replace all real identities, paths, source excerpts, tokens, credentials, and backup mappings with synthetic values.
