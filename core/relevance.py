"""
LLM-based relevance scorer.

Scores how directly each paper addresses the searched molecule and (optionally)
the selected therapeutic area. Returns a 0-100 score that feeds into the
composite score alongside SJR and citation count.
"""
from __future__ import annotations

from anthropic import Anthropic

from config.prompts import RELEVANCE_PROMPT, SYSTEM_EXTRACTOR
from core.llm_client import safe_json_call
from core.models import Paper


_FALLBACK = {
    "relevance": 50.0,    # neutral midpoint when LLM call fails
    "rationale": "Relevance call failed; defaulted to 50",
}


def score_relevance(
    client: Anthropic,
    paper: Paper,
    molecule: str,
    therapeutic_areas: list[str] | None = None,
) -> dict:
    """
    Return a relevance dict {relevance: 0-100, rationale: str} for a paper.
    Mutates `paper.relevance` and `paper.relevance_rationale` in place.
    """
    if not paper.abstract:
        return dict(_FALLBACK)

    if therapeutic_areas:
        ta_block = (
            "Therapeutic area(s) to weigh: "
            + ", ".join(therapeutic_areas)
        )
    else:
        ta_block = "No specific therapeutic area selected — assess centrality to the molecule alone."

    prompt = RELEVANCE_PROMPT.format(
        molecule=molecule,
        therapeutic_area_block=ta_block,
        title=paper.title[:300],
        abstract=paper.abstract[:1500],
    )
    result = safe_json_call(
        client,
        system=SYSTEM_EXTRACTOR,
        user=prompt,
        fallback=dict(_FALLBACK),
        max_tokens=200,
    )

    try:
        rel = float(result.get("relevance") or 0)
    except (TypeError, ValueError):
        rel = 0.0
    rel = max(0.0, min(100.0, rel))

    paper.relevance = rel
    paper.relevance_rationale = str(result.get("rationale") or "")[:200]
    return {"relevance": rel, "rationale": paper.relevance_rationale}


def score_relevance_batch(
    client: Anthropic,
    papers: list[Paper],
    molecule: str,
    therapeutic_areas: list[str] | None = None,
    progress_cb=None,
) -> None:
    """Populate relevance for every paper in the list."""
    total = len(papers)
    for i, p in enumerate(papers):
        score_relevance(client, p, molecule, therapeutic_areas)
        if progress_cb:
            progress_cb(i + 1, total)
