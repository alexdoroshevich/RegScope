---
paths:
  - "**/*.py"
---

# Python Code Quality Rules

## Typing
- Every function has type hints on params AND return type. mypy strict mode.
- `from __future__ import annotations` at the top of every `.py` file.
- Use Pydantic v2 `BaseModel` for API request/response schemas.
- Use polars-native validators at pipeline boundaries (see `data.validation.validate`). Pandera is forbidden — it pulls pandas. See ADR-0001.

## Formatting
- Ruff handles both lint and format. 100 char line length.
- Import sorting is Ruff's `I` rule — don't reorder manually.

## Logging
- `logging.getLogger(__name__)` — never `print()` outside `if __name__ == "__main__"` CLI demos.
- Include context: `logger.info("ingested %d rows in %.2fs", n, elapsed)`.
- Never log API keys, raw user PII, or full response bodies at INFO level.

## Paths & IO
- Always `pathlib.Path`, never string paths.
- Always context managers for file handles.
- Use `httpx.AsyncClient()` with explicit timeout — never `httpx.get()` one-shot in production code.

## Docstrings
- Every module: one-line module docstring.
- Every public function/class: docstring with short purpose. Args/Returns only if non-obvious.
- Internal helpers: docstring optional if name is self-describing.

## Errors
- Never `except Exception: pass`. Log and re-raise, or handle a specific exception class.
- Use `raise ... from err` to preserve chains.

## Testing
- pytest. Coverage gate: `--cov-fail-under=70`.
- Tests mirror source: `tests/unit/test_<module>.py`, `tests/integration/test_<feature>.py`.
- Mark slow tests `@pytest.mark.slow`, integration tests `@pytest.mark.integration`.
- Mock every external API (Federal Register, Regulations.gov, OpenAI). Never hit real APIs in tests.

## Autonomous operation
- No permission needed for: bash commands, file reads/edits, web searches, lint runs, test runs, uv installs.
- Permission required: `git commit` and `git push` only.
