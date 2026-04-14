---
name: check
description: Run the full local quality gate — ruff lint, ruff format check, mypy strict, pytest unit. Use before every commit and every push. Stops at the first failure.
---

Run in this exact order. Stop at the first failure, diagnose, fix, restart the gate from the top.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy data/ nlp/ api/ db/
uv run pytest -m "not slow and not integration" --tb=short -q
```

## Expected outcomes
- **All four green** — safe to commit/push (still needs pre-push-checklist for workflow/secret validation).
- **Any red** — never bypass. Root-cause it:
  - Ruff lint/format: `uv run ruff check --fix .` then `uv run ruff format .` usually resolves.
  - mypy: real issue — missing annotation, wrong type, or unsafe pattern. Fix the code, not the annotation.
  - pytest: run the specific test locally with `-x --tb=long`. If a fixture is stale, fix it; don't `xfail` without a reason.

## Deeper variants (before a release or a long-running PR)
```bash
uv run pytest --tb=short                    # include slow tests
uv run pytest --cov-report=term-missing     # full coverage table
uv run pytest -m integration --tb=short     # integration tests (mocked externals)
```

## Never
- Commit with any of the four red.
- `--no-verify` to skip the pre-commit hook.
- Disable a test or lower the coverage threshold to make this pass.
