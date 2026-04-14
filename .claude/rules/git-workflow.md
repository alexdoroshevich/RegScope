---
paths:
  - "**/*"
---

# Git Workflow Rules

## Permissions (autonomous vs gated)
- **Autonomous (no ask):** any local shell, file edit, install, web search, test, lint.
- **Gated (always ask user first):** `git commit`, `git push` (any form, any branch).

## Commit format
Conventional Commits. First line ≤72 chars, imperative mood:
```
feat: add MinHash astroturf grouping
fix(ingest): handle 429 with exponential backoff
chore: bump ruff to 0.8.0
docs: add DECISIONS.md entry for DuckDB-vs-Postgres
ci: pin claude-code-action to commit SHA
```
Allowed types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`, `build`, `revert`, `style`.

## Branching
- `main` — protected, production-ready.
- `feature/<short-desc>` — all work lives here. Short-lived, squashed to `main`.
- No `develop`, no release branches (overkill for this project).

## Pre-push checklist (every time)
1. `uv run ruff check .` — clean
2. `uv run ruff format --check .` — clean
3. `uv run mypy data/ nlp/ api/ db/` — clean
4. `uv run pytest -m "not slow and not integration" -q` — pass
5. Workflow YAML changed? Validate with `python -c "import yaml; yaml.safe_load(open('<file>'))"`.
6. Action version changed? Verify the SHA and field names against the action's README on the target tag.

## PR rules
- Title: conventional commits format (`feat: ...`, lowercase subject).
- Body: fill every section of `.github/pull_request_template.md`. No empty/placeholder text.
- Every commit in the PR must match the commit-message validator regex.
- Wait for all CI checks green before requesting merge. If any check fails, diagnose the root cause, fix, push again. Never disable a failing check to make it pass.

## Never
- Force push to `main` / `master`.
- Commit `.env`, API keys, tokens, `.duckdb` files, or `data/raw/`.
- Use `--no-verify` to skip hooks.
- Amend a published commit.
- Delete branches without confirming they've been merged (`git branch --merged`).
