# RegScope — Federal Register Regulatory Intelligence

> AI-powered analysis of public comments on federal regulations.
> Detect astroturf campaigns. Cluster comment themes. Visualize citation networks. Query in plain English.

[![PR Gate](https://github.com/alexdoroshevich/RegScope/actions/workflows/pr-gate.yml/badge.svg)](https://github.com/alexdoroshevich/RegScope/actions/workflows/pr-gate.yml)
[![Security](https://github.com/alexdoroshevich/RegScope/actions/workflows/security.yml/badge.svg)](https://github.com/alexdoroshevich/RegScope/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What it does

RegScope ingests public comments from [Regulations.gov](https://regulations.gov) and surfaces four kinds of analysis:

| Feature | What it answers |
|---|---|
| **Astroturf Detector** | Are there coordinated duplicate-comment campaigns in this docket? Which submissions look template-driven? |
| **Comment Clusters** | What are the main themes commenters raise? How many people touch each topic? |
| **Citation Graph** | Which CFR sections and U.S.C. titles do commenters reference most? How are they connected? |
| **Ask a Question** | Plain-English RAG — retrieve the most relevant comments and synthesise an answer with GPT-4o-mini. |

A **Docket Browser** lets you search and navigate all ingested dockets, with one-click deep-links into each analysis page.

---

## Quick Start

### Local (recommended for development)

```bash
# 1. Clone and install
git clone https://github.com/alexdoroshevich/RegScope.git
cd RegScope
make setup           # uv sync + spaCy model + pre-commit hooks + creates .env

# 2. Add your API keys to .env
#    REGULATIONS_GOV_API_KEY  — free from https://api.data.gov/signup/
#    OPENAI_API_KEY           — for GPT-4o-mini cluster labels and RAG answers

# 3. Load sample data
make seed            # seeds ~500 synthetic comments into DuckDB

# 4. Start the API and UI (two terminals)
make dev             # FastAPI at http://localhost:8000/docs
make dev-frontend    # React dev server at http://localhost:5173
```

### Docker

```bash
docker build -t regscope .
docker compose up          # API on :8000, UI served from FastAPI static files
```

---

## Ingesting real data

```bash
# Full single-docket pipeline (ingest → dedup → embed → cluster → label → load)
uv run python -m scripts.pipeline EPA-HQ-OAR-2021-0317

# Or step by step
make ingest-comments   # fetch from Regulations.gov → Parquet
make embed             # sentence-transformers embeddings
make cluster           # HDBSCAN per-docket clustering
make dedup             # MinHash/LSH near-duplicate detection
make citations         # spaCy CFR/USC citation extraction
make summarize         # GPT-4o-mini cluster labels (cached)
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Language | Python 3.13+, TypeScript |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| API | FastAPI 0.115+, Pydantic v2 |
| Database | DuckDB 1.1+ (reads Parquet; no separate DB server needed) |
| Data processing | Polars 1.x (Arrow-native, no pandas) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local, no API cost) |
| Clustering | HDBSCAN |
| Deduplication | datasketch MinHash/LSH |
| NER | spaCy `en_core_web_sm` |
| LLM | GPT-4o-mini via [litellm](https://github.com/BerriAI/litellm) (every response cached) |
| Frontend | React 18, Vite, Tailwind CSS, Recharts, react-force-graph |

---

## Architecture

```
Regulations.gov API
        │
        ▼
data/ingest/  ──→  Parquet (raw)
        │
        ▼
nlp/          ──→  Parquet (embeddings, clusters, dedup, citations)
        │
        ▼
db/           ──→  DuckDB (reads Parquet; rebuilt from scratch on restart)
        │
        ▼
api/          ──→  FastAPI  ──→  frontend/  (React SPA)
```

Parquet files are the **source of truth** — DuckDB is a query layer rebuilt from them on startup. This means data survives DuckDB restarts and the database file is never committed to the repo.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detail.

---

## Development

```bash
make lint        # ruff check + mypy strict
make format      # ruff format + ruff --fix
make test        # unit tests (fast, no network, no GPU)
make test-all    # unit + integration tests
make test-cov    # coverage report → htmlcov/index.html
make check       # lint + test in one shot
```

---

## Design Decisions

See [docs/DECISIONS.md](docs/DECISIONS.md) for why DuckDB over PostgreSQL, Polars over pandas, local embeddings over API calls, and more.

---

## License

MIT
