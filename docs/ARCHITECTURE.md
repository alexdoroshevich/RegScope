# RegScope Architecture

## Overview

RegScope is a single-machine analytical platform that ingests federal regulatory comments,
detects coordinated astroturf campaigns, and clusters comments by topic.
All processing fits comfortably on one machine (~30 GB dataset).

## Data Flow

```
Regulations.gov API
        │
        ▼
 data/ingest/          ← httpx async fetch → raw Parquet (partitioned by docket_id)
        │
        ▼
 data/process/         ← Polars text cleaning + schema validation → processed Parquet
        │
        ├──► nlp/dedup.py     ← MinHash/LSH (128 perms, threshold 0.8) → duplicate_groups Parquet
        │
        ├──► nlp/embed.py     ← sentence-transformers all-MiniLM-L6-v2 → embeddings Parquet
        │
        └──► nlp/cluster.py   ← HDBSCAN (min_cluster_size=15) → clusters Parquet
                  │
                  ▼
             nlp/summarize.py  ← litellm gpt-4o-mini (cached) → cluster_labels Parquet
                  │
                  ▼
              db/ (DuckDB)     ← reads Parquet at query time; schema in db/migrations/
                  │
                  ▼
              api/ (FastAPI)   ← serves JSON; Pydantic v2 schemas
                  │
                  ▼
           frontend/ (React)   ← Vite + TypeScript + Tailwind + Recharts
```

## Key Design Decisions

### DuckDB over Postgres / Spark
The dataset is ~30 GB on a single machine. DuckDB reads Parquet files directly,
supports vectorized SQL, and needs zero infrastructure. Spark would add a cluster
management layer with no benefit at this scale. See `DECISIONS.md` for the full ADR.

### Parquet as source of truth
DuckDB tables are derived views over Parquet files. If the `.duckdb` file is
deleted or corrupted, all data can be recovered by re-running the pipeline.
`.duckdb` files are git-ignored.

### Local embeddings (sentence-transformers)
`all-MiniLM-L6-v2` runs on CPU, produces 384-dim vectors, and costs nothing per
call. It is fast enough for ~500 k comments on a modern laptop (~1 k comments/s).

### LLM calls only for cluster labeling
GPT-4o-mini via `litellm` is used only to assign human-readable labels and
summaries to HDBSCAN clusters. Every response is cached to Parquet keyed by
`(prompt_hash, model)` to avoid re-billing on reruns.

### Polars over pandas
Arrow-native memory layout interops directly with DuckDB's zero-copy Parquet
reader. Polars also enforces explicit schema types, catching data quality issues
earlier than pandas.

## Directory Layout

```
RegScope/
├── api/                  FastAPI app
│   ├── models/           Pydantic v2 schemas
│   ├── routes/           one file per resource
│   ├── config.py         settings (env vars)
│   └── main.py           app factory + SPA mount
├── data/
│   ├── ingest/           raw fetch → Parquet
│   └── process/          clean + validate → processed Parquet
├── db/
│   ├── migrations/       sequential .sql files
│   ├── init_db.py        schema apply + Parquet loaders
│   └── queries.py        raw SQL query functions
├── nlp/
│   ├── dedup.py          MinHash/LSH campaign detection
│   ├── embed.py          sentence-transformer embeddings
│   ├── cluster.py        HDBSCAN clustering
│   └── summarize.py      litellm cluster labeling
├── frontend/
│   └── src/
│       ├── api/          typed fetch wrappers
│       ├── components/   shared UI components
│       ├── pages/        one file per route
│       └── types/        TypeScript API types
├── scripts/
│   ├── pipeline.py       end-to-end single-docket CLI
│   └── seed_data.py      synthetic data for local dev
└── tests/
    ├── unit/             fast, no I/O
    └── integration/      TestClient + in-memory DuckDB
```

## MVP Feature Scope

| Feature | Status |
|---|---|
| Astroturf Detector (MinHash/LSH + campaign score) | Done |
| Comment Cluster Analyzer (embeddings → HDBSCAN → GPT labels) | Done |
| Citation Graph | Not started |
| NL Query (RAG) | Not started |

Citation Graph and NL Query are out of scope until both MVP features are
deployed and polished.

## Running Locally

```bash
# Install deps
uv sync --dev

# Seed DuckDB with 500 synthetic comments (no API keys needed)
make seed

# Start API + frontend
make dev            # terminal 1 — FastAPI on :8000
make dev-frontend   # terminal 2 — Vite on :5173

# Run a real docket end-to-end (requires API keys in .env)
uv run python scripts/pipeline.py EPA-HQ-OAR-2021-0317
```
