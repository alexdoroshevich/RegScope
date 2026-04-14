## What does this PR do?

<one specific paragraph about THIS change — not a title repeat>

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Docs / config only
- [ ] CI / build
- [ ] Test-only

## Checklist (author)

- [ ] `uv run ruff check .` is clean
- [ ] `uv run ruff format --check .` is clean
- [ ] `uv run mypy data/ nlp/ api/ db/` is clean
- [ ] `uv run pytest -m "not slow and not integration" -q` passes locally
- [ ] New Python files have type hints and at least one smoke test
- [ ] No `print()` — using `logging`
- [ ] No PII / API keys / `.env` content in code or logs
- [ ] No new deps added without prior discussion
- [ ] Conventional commit prefix on every commit (`feat:`, `fix:`, `chore:`, etc.)
- [ ] MVP scope: change is in astroturf-detector or cluster-analyzer flow (or explicitly justified otherwise)

## How to test

<concrete step>
<concrete step>
<what to observe — what proves this works>

## Screenshots (UI change only)

<before / after — or "N/A">

## Related issues / spec sections

<link to issue, or "N/A">
