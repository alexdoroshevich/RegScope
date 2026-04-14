---
paths:
  - "data/**"
  - "nlp/**"
  - "db/**"
---

# Data Pipeline Rules

## Ingestion (`data/ingest/`)
- All HTTP via `httpx.AsyncClient` with `timeout=httpx.Timeout(30.0)`.
- Rate limit: ~1 req/sec for Federal Register. Respect Regulations.gov limits (1000/hr).
- Retry on 429/5xx: 3 attempts, exponential backoff (`tenacity` if needed — but prefer stdlib).
- Save raw payloads to Parquet, partitioned by year or docket_id.
- Include a `fetched_at` timestamp column on every raw row.

## Processing (`data/process/`)
- Pandera schema BEFORE and AFTER every transform.
- Idempotent: running twice produces the same output.
- Never mutate raw Parquet. Always write to `data/processed/`.

## DuckDB (`db/`)
- Raw SQL in `db/queries.py` — no ORM.
- Parquet is source of truth: DuckDB tables are derived via `CREATE TABLE AS SELECT * FROM read_parquet(...)`.
- Migrations in `db/migrations/NNN_description.sql` — sequential numbering.
- Never commit `.duckdb` files. Regenerate from Parquet.

## Embeddings (`nlp/embed.py`)
- Model: `all-MiniLM-L6-v2` (384 dims, float32).
- Batch size default 256. Resume by skipping `comment_id`s already embedded.
- Store in DuckDB `comments.embedding FLOAT[384]` column.
- Never re-embed a comment that has a non-NULL embedding — this is a bug.

## Clustering (`nlp/cluster.py`)
- HDBSCAN `min_cluster_size=15` by default (tunable via CLI).
- Cluster per-docket, not globally — comments across dockets are unrelated.
- Noise points get `cluster_id = -1`.

## Dedup (`nlp/dedup.py`)
- MinHash 128 permutations, LSH threshold 0.8.
- `campaign_likelihood = group_size / unique_submitters`. Flag `> 5.0` as astroturf.
- Store template text (most common variant) in `duplicate_groups.template_text`.

## LLM calls (`nlp/summarize.py`)
- `litellm` with `gpt-4o-mini`. Max 10 req/s.
- **Every response cached** to Parquet keyed by (prompt_hash, model). No re-calls.
- On content filter: skip + log, don't retry.
- Log `cost_usd` per call. Surface monthly total.
