---
paths:
  - "**/*.py"
  - "db/**"
  - "data/**"
  - "nlp/**"
  - "api/**"
---

# Architecture Rules (non-negotiable)

## Stack invariants
- Python 3.13+, `uv` for packages. Never `pip install` directly.
- **DuckDB** is the analytical store. No PostgreSQL, no SQLite for analytics, no Spark.
- **Polars** for dataframes. No pandas (unless interfacing legacy libs — isolated in adapter).
- **Parquet on disk = source of truth.** DuckDB reads from Parquet; data survives DB restarts.
- `httpx` for HTTP. No `requests`.
- FastAPI + Pydantic v2 for API. No Flask, no Django.
- `litellm` for LLM calls (model: `gpt-4o-mini`). Cache every response.
- `sentence-transformers` (`all-MiniLM-L6-v2`) runs locally — no API cost for embeddings.

## Data flow (never reorder)
1. `data/ingest/` — fetch raw → Parquet
2. `data/process/` — clean + polars-native validate (`data.validation.validate`) → Parquet
3. `db/` — DuckDB reads Parquet
4. `api/` — FastAPI serves DuckDB queries
5. `frontend/` — React consumes API

## Forbidden
- Spark, Airflow, Kafka — overkill for ~30GB, single machine is correct.
- SQLAlchemy — use raw DuckDB SQL via `duckdb-python`.
- Jupyter notebooks checked into repo — this is production code.
- `print()` for logs — use `logging` module.
- String file paths — use `pathlib.Path`.
- `localStorage`/`sessionStorage` in frontend.
- Separate CSS files — Tailwind utility classes only.

## MVP scope
Current phase: **two features only** —
1. Astroturf Detector (MinHash/LSH + campaign score)
2. Comment Cluster Analyzer (embeddings → HDBSCAN → GPT-4o-mini labels)

Do NOT start Citation Graph or NL Query until features 1+2 are done, tested, deployed.

## When tempted to add a dependency
1. Is it already in `pyproject.toml`?
2. If not: state the case to the user. Include: what it does, why stdlib/existing deps won't, bundle-size cost.
3. Never silently add to `pyproject.toml`. Never install without the user's approval.
