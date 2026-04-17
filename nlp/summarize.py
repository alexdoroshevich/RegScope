"""LLM-powered cluster labeling via litellm (gpt-4o-mini)."""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 500
SAMPLE_SIZE = 5

_SYSTEM_PROMPT = (
    "You are summarizing public regulatory comments. Given 5 representative "
    "comments from the same cluster, produce:\n"
    "1. A 3-5 word topic label.\n"
    "2. A 1-2 sentence theme summary.\n"
    "Do NOT speculate beyond what the comments say. If the cluster is "
    'unclear, say "mixed topic" and label it Unclear.'
)


@dataclass(frozen=True, slots=True)
class ClusterLabel:
    """Result of labeling a single cluster."""

    docket_id: str
    cluster_id: int
    label: str
    summary: str
    prompt_hash: str
    model: str
    cost_usd: float


def _hash_prompt(prompt: str, model: str) -> str:
    """SHA-256 hash of prompt + model for cache keying."""
    return hashlib.sha256(f"{prompt}|{model}".encode()).hexdigest()


def _build_user_prompt(comments: list[str]) -> str:
    """Format representative comments into the user prompt."""
    numbered = "\n".join(f"{i + 1}. {c[:500]}" for i, c in enumerate(comments[:SAMPLE_SIZE]))
    return f"Here are {min(len(comments), SAMPLE_SIZE)} representative comments from a cluster:\n\n{numbered}"


def _parse_response(text: str) -> tuple[str, str]:
    """Extract label and summary from the LLM response."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    label = "Unclear"
    summary = ""

    for line in lines:
        lower = line.lower()
        if lower.startswith("1.") or lower.startswith("label:") or lower.startswith("topic:"):
            label = line.split(":", 1)[-1].strip() if ":" in line else line[2:].strip()
            label = label.strip("*").strip('"').strip("'").strip()
        elif lower.startswith("2.") or lower.startswith("summary:") or lower.startswith("theme:"):
            summary = line.split(":", 1)[-1].strip() if ":" in line else line[2:].strip()
            summary = summary.strip("*").strip('"').strip("'").strip()

    if not summary and len(lines) >= 2:
        summary = lines[-1]
    if not label or label.lower() in ("", "n/a"):
        label = "Unclear"

    return label, summary


def _load_cache(cache_path: Path) -> dict[str, tuple[str, str]]:
    """Load the prompt cache from Parquet. Returns {prompt_hash: (label, summary)}."""
    if not cache_path.exists():
        return {}

    import polars as pl

    df = pl.read_parquet(cache_path)
    result: dict[str, tuple[str, str]] = {}
    for row in df.iter_rows(named=True):
        result[row["prompt_hash"]] = (row["label"], row["summary"])
    return result


def _save_cache(cache_path: Path, entries: list[ClusterLabel]) -> None:
    """Append new entries to the Parquet cache."""
    import polars as pl

    new_df = pl.DataFrame(
        {
            "prompt_hash": [e.prompt_hash for e in entries],
            "model": [e.model for e in entries],
            "label": [e.label for e in entries],
            "summary": [e.summary for e in entries],
            "cost_usd": [e.cost_usd for e in entries],
        }
    )

    if cache_path.exists():
        existing = pl.read_parquet(cache_path)
        combined = pl.concat([existing, new_df])
    else:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        combined = new_df

    combined.write_parquet(cache_path)
    logger.info("saved %d cache entries to %s", len(entries), cache_path)


def _estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Estimate cost in USD for a litellm call."""
    costs: dict[str, tuple[float, float]] = {
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    }
    input_rate, output_rate = costs.get(model, (0.15 / 1_000_000, 0.60 / 1_000_000))
    return prompt_tokens * input_rate + completion_tokens * output_rate


def label_cluster(
    comments: list[str],
    *,
    docket_id: str,
    cluster_id: int,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    cache: dict[str, tuple[str, str]] | None = None,
) -> ClusterLabel:
    """Label a single cluster by calling the LLM (or returning cached result)."""
    import litellm

    user_prompt = _build_user_prompt(comments)
    prompt_hash = _hash_prompt(user_prompt, model)

    if cache and prompt_hash in cache:
        label, summary = cache[prompt_hash]
        logger.debug("cache hit for cluster %d in docket %s", cluster_id, docket_id)
        return ClusterLabel(
            docket_id=docket_id,
            cluster_id=cluster_id,
            label=label,
            summary=summary,
            prompt_hash=prompt_hash,
            model=model,
            cost_usd=0.0,
        )

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception:
        logger.exception("LLM call failed for cluster %d in docket %s", cluster_id, docket_id)
        return ClusterLabel(
            docket_id=docket_id,
            cluster_id=cluster_id,
            label="Unclear",
            summary="LLM call failed",
            prompt_hash=prompt_hash,
            model=model,
            cost_usd=0.0,
        )

    content = response.choices[0].message.content or ""
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost = _estimate_cost(prompt_tokens, completion_tokens, model)

    label, summary = _parse_response(content)

    logger.info(
        "cluster %d/%s: label=%r, cost=$%.6f (%d+%d tokens)",
        cluster_id,
        docket_id,
        label,
        cost,
        prompt_tokens,
        completion_tokens,
    )

    return ClusterLabel(
        docket_id=docket_id,
        cluster_id=cluster_id,
        label=label,
        summary=summary,
        prompt_hash=prompt_hash,
        model=model,
        cost_usd=cost,
    )


def label_clusters_for_docket(
    cluster_comments: dict[int, list[str]],
    *,
    docket_id: str,
    cache_path: Path,
    model: str = DEFAULT_MODEL,
    rate_limit_delay: float = 0.1,
) -> list[ClusterLabel]:
    """Label all clusters for a docket, using and updating the Parquet cache."""
    cache = _load_cache(cache_path)
    results: list[ClusterLabel] = []
    new_entries: list[ClusterLabel] = []

    for cluster_id, comments in sorted(cluster_comments.items()):
        if cluster_id == -1:
            continue

        result = label_cluster(
            comments,
            docket_id=docket_id,
            cluster_id=cluster_id,
            model=model,
            cache=cache,
        )
        results.append(result)

        if result.cost_usd > 0:
            cache[result.prompt_hash] = (result.label, result.summary)
            new_entries.append(result)
            time.sleep(rate_limit_delay)

    if new_entries:
        _save_cache(cache_path, new_entries)

    total_cost = sum(r.cost_usd for r in results)
    logger.info(
        "docket %s: labeled %d clusters, total cost $%.6f",
        docket_id,
        len(results),
        total_cost,
    )

    return results
