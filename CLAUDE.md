# RegScope — Claude Code Project Instructions

## Project Overview
RegScope is an open-source AI-powered Federal Register regulatory intelligence platform.
It analyzes public comments on federal regulations to detect astroturf campaigns,
cluster comments by topic, and map cross-rule regulatory impact.

## Tech Stack (DO NOT deviate without explicit approval)
- **Python 3.11+** — all backend code
- **uv** — package manager (NOT pip, NOT poetry, NOT conda)
- **DuckDB 1.1+** — analytical database (NOT PostgreSQL, NOT SQLite for analytics)
- **Polars 1.x** — data processing (NOT pandas unless interfacing with legacy libs)
- **FastAPI 0.115+** — API framework
- **sentence-transformers** — embeddings (all-MiniLM-L6-v2 model)
- **HDBSCAN** — clustering
- **datasketch** — MinHash/LSH for deduplication
- **spaCy** (en_core_web_sm) — NER for citation extraction
- **litellm** — LLM calls (GPT-4o-mini default)
- **React 18 + TypeScript + Vite** — frontend
- **Recharts** — charts
- **react-force-graph** — network visualization
- **Tailwind CSS** — styling

## Architecture Rules

### Data Flow
1. **Ingestion** (data/ingest/) → raw data from APIs → Parquet files on disk
2. **Processing** (nlp/) → embeddings, clusters, dedup, citations
3. **Storage** (db/) → DuckDB reads Parquet files for analytics
4. **API** (api/) → FastAPI serves processed data
5. **Frontend** (frontend/) → React consumes API

### Critical Design Decisions
- **DuckDB, NOT Spark** — dataset is ~30GB, single-machine is correct. Spark is overkill.
  Document this in DECISIONS.md.
- **Polars, NOT pandas** — Arrow interop with DuckDB, better performance.
- **Parquet on disk is source of truth** — DuckDB reads from Parquet.
  This means data survives DuckDB restarts.
- **sentence-transformers runs locally** — no API cost for embeddings.
- **GPT-4o-mini via litellm** — only for cluster labeling and RAG answers.
  Cache all LLM responses to avoid re-running.
- **No Spark anywhere** — if you think Spark is needed, you're wrong. Explain why in DECISIONS.md.

## Code Quality Standards

### Python
- **Ruff** for linting AND formatting (replaces flake8 + black + isort)
- **mypy strict mode** — all functions must have type annotations
- **100 char line length**
- Every module must have docstrings
- Use `from __future__ import annotations` in every file
- Use Pydantic models for all API request/response schemas
- Use Pandera for DataFrame schema validation in data pipelines
- Always use `pathlib.Path`, never string paths
- Use `httpx` for HTTP (not requests) — it supports async

### Testing
- **pytest** with `--cov-fail-under=70`
- Tests go in `tests/unit/` and `tests/integration/`
- Mark slow tests with `@pytest.mark.slow`
- Mark integration tests with `@pytest.mark.integration`
- Use fixtures from `tests/conftest.py` — in-memory DuckDB with sample data
- Mock all external API calls (Federal Register, Regulations.gov, OpenAI)
- Never call real APIs in tests

### Git
- Branch naming: `feature/xyz`, `fix/xyz`, `docs/xyz`
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`)
- Never commit to `main` directly — always PR
- Every PR must pass CI (lint + test)

### Frontend (TypeScript)
- Strict TypeScript — no `any` types
- Functional components only (no class components)
- Custom hooks in `hooks/` directory
- API types auto-generated from FastAPI OpenAPI spec where possible

## File Organization Rules
- `data/ingest/` — downloading and parsing raw data
- `data/process/` — cleaning and transforming
- `nlp/` — all NLP/ML code (embeddings, clustering, dedup, citations, RAG)
- `db/` — DuckDB schema, queries, migrations
- `api/` — FastAPI application
- `api/routes/` — one file per resource (rules.py, comments.py, graph.py, query.py)
- `api/models/` — Pydantic schemas
- `frontend/src/pages/` — one file per page
- `frontend/src/components/` — reusable components
- `tests/` — mirrors source structure
- `scripts/` — one-off utilities, benchmarks
- `docs/` — architecture, decisions, data dictionary

## What NOT to Do
- Do NOT use pandas (use Polars)
- Do NOT use requests (use httpx)
- Do NOT use SQLAlchemy (use raw DuckDB SQL via duckdb-python)
- Do NOT use Jupyter notebooks (this is a production project, not EDA)
- Do NOT add Spark, Airflow, or Kafka (overkill for this scale)
- Do NOT use localStorage/sessionStorage in frontend
- Do NOT install packages with pip (use uv)
- Do NOT write code without tests
- Do NOT commit .env files or API keys
- Do NOT use print() for logging (use Python logging module)
- Do NOT create separate CSS files (use Tailwind utility classes)

## Environment Variables (from .env)
```
REGULATIONS_GOV_API_KEY=xxx          # from api.data.gov
OPENAI_API_KEY=xxx                    # for GPT-4o-mini via litellm
REGSCOPE_DATA_DIR=./data/raw         # where Parquet files live
REGSCOPE_DB_PATH=./data/regscope.db  # DuckDB file
REGSCOPE_LOG_LEVEL=INFO
```

## Common Commands
```bash
uv sync --dev              # Install all dependencies
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy data/ nlp/ api/ db/  # Type check
uv run uvicorn api.main:app --reload  # Start API server
```

## Current Phase
**MVP Phase — Focus on two features only:**
1. Astroturf Detector (comment deduplication + campaign detection)
2. Comment Cluster Analyzer (semantic clustering + LLM labels)

Do NOT start working on Citation Graph or NL Query until features 1 and 2 are complete,
tested, deployed, and polished.

## Data Sources
- **Federal Register API**: https://www.federalregister.gov/developers/documentation/api/v1
  - Free, no API key needed
  - Rate limit: be polite, ~1 req/sec
  - Covers 1994-present
- **Regulations.gov API**: https://open.gsa.gov/api/regulationsgov/
  - Requires API key from api.data.gov (free)
  - GET endpoints for documents, comments, dockets
  - Bulk download at regulations.gov/bulkdownload
- **eCFR Markdown**: https://github.com/AlextheYounga/ecfr
  - 2.5GB of regulations in Markdown (for RAG, Phase 2)
