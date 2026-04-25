"""
Extract geographic origin of a study from its affiliations and abstract.

Used by the RWE tab to build the world map with country/state drill-down.
Calls the LLM (via config/prompts.py EXTRACT_GEOGRAPHY_PROMPT) and returns
a structured dict with country, ISO code, region/state, city, cohort size.
"""
from __future__ import annotations

from anthropic import Anthropic

from config.prompts import EXTRACT_GEOGRAPHY_PROMPT, SYSTEM_EXTRACTOR
from core.llm_client import safe_json_call
from core.models import Paper


# Minimal fallback when the LLM call fails
_FALLBACK = {
    "country": None,
    "country_iso2": None,
    "region": None,
    "city": None,
    "cohort_size": None,
    "is_multicentric": False,
}


def extract_geography(client: Anthropic, paper: Paper) -> dict:
    """Return a geography dict for the given paper (see _FALLBACK for schema)."""
    if not paper.abstract and not paper.affiliations:
        return dict(_FALLBACK)

    affiliations_text = "; ".join(paper.affiliations[:5]) if paper.affiliations else "None"
    prompt = EXTRACT_GEOGRAPHY_PROMPT.format(
        title=paper.title[:300],
        abstract=paper.abstract[:1500],
        affiliations=affiliations_text[:1000],
    )
    result = safe_json_call(
        client,
        system=SYSTEM_EXTRACTOR,
        user=prompt,
        fallback=dict(_FALLBACK),
        max_tokens=250,
    )
    # Normalise the ISO code to uppercase if present
    if result.get("country_iso2"):
        result["country_iso2"] = str(result["country_iso2"]).upper()[:2]
    return result


def extract_geography_batch(client: Anthropic, papers: list[Paper]) -> None:
    """Populate paper.geography in-place for each paper in the list."""
    for p in papers:
        p.geography = extract_geography(client, p)

