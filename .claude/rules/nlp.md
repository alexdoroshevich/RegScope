---
paths:
  - "nlp/**"
---

# NLP / ML Rules

## Stack
- **sentence-transformers** — `all-MiniLM-L6-v2`, 384-dim float32. Runs locally, no API cost.
- **HDBSCAN** — density-based clustering; `min_cluster_size=15` default.
- **datasketch** — MinHash (128 perms) + MinHashLSH, threshold 0.8.
- **spaCy** — `en_core_web_sm` for CFR-citation NER.
- **litellm** — uniform interface to `gpt-4o-mini`. Temperature 0.3, max_tokens 500.

## Invariants
1. **Never re-embed.** Skip comments where the `embedding` column is non-NULL. Re-embedding is a bug — flag in review.
2. **Cluster per-docket, not globally.** Comments across dockets are unrelated; mixing them produces noise.
3. **Every LLM response cached.** Key = `sha256(prompt) + model`. Cache lives in Parquet; load before any call. Never re-call GPT-4o-mini for a key already present.
4. **Cost logged per LLM call.** Token counts + dollar estimate, aggregated monthly.
5. **MinHash pre-normalize.** Lowercase → strip whitespace → remove punctuation — *before* generating the signature. Without this, typos break dedup.

## Campaign-detection math
```
campaign_likelihood = group_size / unique_submitters
```
Flag a duplicate group as astroturf when `campaign_likelihood > 5.0`. Store `template_text` = the longest common substring or medoid of the group.

## Performance targets
- Embedding: ~14k sentences/sec CPU, ~50k GPU.
- HDBSCAN: ~100k points in <60s.
- MinHashLSH query: sub-ms per comment after index is built.

## Cluster-labeling prompt (for GPT-4o-mini)
```
You are summarizing public regulatory comments. Given 5 representative
comments from the same cluster, produce:
1. A 3–5 word topic label.
2. A 1–2 sentence theme summary.
Do NOT speculate beyond what the comments say. If the cluster is
unclear, say "mixed topic" and label it Unclear.
```

## Forbidden
- Swapping to a bigger embedding model without a benchmark showing ≥5% retrieval-quality gain on RegScope data.
- Global (cross-docket) clustering.
- Storing embeddings as JSON strings (use DuckDB `FLOAT[384]`).
- Re-calling an LLM prompt that is already cached.
- Logging raw comment text above DEBUG level.
