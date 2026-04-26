"""
End-to-end pipeline orchestration.

Two public entry points:
    - preview_search(): cheap, just resolves and counts PubMed hits
    - run_full_pipeline(): full search, classify, enrich, score, aggregate

Stages (run_full_pipeline):
    1. Resolve user input → canonical generic name
    2. Build PubMed query (with optional MeSH filters from therapeutic areas)
    3. Search + fetch papers
    4. Classify each paper into one of the 4 categories
    5. Extract structured metadata (geo, trial, safety) per category
    6. Score relevance via LLM
    7. Look up SJR and citation counts
    8. Compute composite score
    9. Cap and sort each category
   10. Build dashboard aggregates
   11. Return MoleculeReport
"""
from __future__ import annotations

import time
from typing import Callable

from anthropic import Anthropic

from config import filters, scoring
from config.categories import CATEGORIES
from config.mock_market_data import get_market_data
from config.molecules import get_molecule
from config.therapeutic_areas import get_mesh_terms

from core import (
    aggregator,
    citations as citations_module,
    classifier,
    drug_resolver,
    geo_extractor,
    journal_metrics,
    metadata_extractors,
    pubmed_client,
    relevance as relevance_module,
)
from core.models import MoleculeReport, Paper


ProgressCb = Callable[[str, int, int], None] | None


# ════════════════════════════════════════════════════════════════════════════
#  PREVIEW
# ════════════════════════════════════════════════════════════════════════════

def preview_search(
    user_input: str,
    date_from,
    date_to,
    therapeutic_areas: list[str] | None = None,
) -> dict:
    """
    Resolve user input and count PubMed hits without fetching anything.
    `therapeutic_areas` is a list of leaf labels from config/therapeutic_areas.py.
    """
    resolved = drug_resolver.resolve(user_input)
    if not resolved.resolved:
        return {
            "resolved": False,
            "input": user_input,
            "generic": None,
            "hit_count": 0,
            "message": f"Could not resolve '{user_input}' to a tracked molecule.",
        }

    mesh = get_mesh_terms(therapeutic_areas) if therapeutic_areas else None
    query = pubmed_client.build_query(
        resolved.generic, date_from, date_to, mesh_terms=mesh,
    )
    count = pubmed_client.count_matches(query)

    return {
        "resolved": True,
        "input": user_input,
        "generic": resolved.generic,
        "matched_term": resolved.matched_term,
        "match_type": resolved.match_type,
        "match_confidence": resolved.confidence,
        "therapeutic_areas": therapeutic_areas or [],
        "mesh_terms": mesh or [],
        "hit_count": count,
        "will_fetch": min(count, filters.MAX_PAPERS_PER_SEARCH),
        "query": query,
    }


# ════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def run_full_pipeline(
    client: Anthropic,
    user_input: str,
    date_from,
    date_to,
    therapeutic_areas: list[str] | None = None,
    progress_cb: ProgressCb = None,
) -> MoleculeReport:
    """Run the full pipeline. Returns a populated MoleculeReport."""
    start = time.time()
    warnings: list[str] = []

    def _p(stage: str, done: int, total: int):
        if progress_cb:
            progress_cb(stage, done, total)

    # ── 1. Resolve molecule ──────────────────────────────────────────────────
    _p("Resolving molecule", 0, 1)
    resolved = drug_resolver.resolve(user_input)
    if not resolved.resolved:
        raise ValueError(f"Could not resolve '{user_input}' to a tracked molecule")
    molecule = resolved.generic
    mol_entry = resolved.molecule_entry or get_molecule(molecule) or {}
    _p("Resolving molecule", 1, 1)

    # ── 2. Build query ───────────────────────────────────────────────────────
    mesh = get_mesh_terms(therapeutic_areas) if therapeutic_areas else None
    query = pubmed_client.build_query(molecule, date_from, date_to, mesh_terms=mesh)
    total_hits = pubmed_client.count_matches(query)

    # ── 3. Search + fetch ────────────────────────────────────────────────────
    _p("Searching PubMed", 0, 1)
    pmids = pubmed_client.search_pmids(query, retmax=filters.MAX_PAPERS_PER_SEARCH)
    _p("Searching PubMed", 1, 1)

    if not pmids:
        return _empty_report(molecule, mol_entry, query, total_hits,
                             date_from, date_to, therapeutic_areas,
                             warnings, start)

    _p("Fetching paper details", 0, len(pmids))
    papers = pubmed_client.fetch_papers(pmids)
    _p("Fetching paper details", len(papers), len(pmids))

    # ── 4. Classify ──────────────────────────────────────────────────────────
    classifier.classify_batch(
        client, papers, molecule,
        progress_cb=lambda d, t: _p("Classifying papers", d, t),
    )

    included = [p for p in papers if p.decision == "INCLUDE" and p.category]

    by_category: dict[str, list[Paper]] = {cid: [] for cid in CATEGORIES}
    for p in included:
        if p.category in by_category:
            by_category[p.category].append(p)

    for cid, plist in by_category.items():
        if len(plist) > filters.MAX_PAPERS_PER_CATEGORY:
            by_category[cid] = plist[:filters.MAX_PAPERS_PER_CATEGORY]
            warnings.append(
                f"Category '{cid}' truncated to {filters.MAX_PAPERS_PER_CATEGORY} papers"
            )

    kept = [p for plist in by_category.values() for p in plist]

    # ── 5. Extract structured metadata per category ─────────────────────────
    if by_category.get("trial_results"):
        trial_papers = by_category["trial_results"]
        for i, p in enumerate(trial_papers):
            p.trial_metadata = metadata_extractors.extract_trial_metadata(client, p)
            _p("Extracting trial metadata", i + 1, len(trial_papers))

    if by_category.get("safety_efficacy"):
        safety_papers = by_category["safety_efficacy"]
        for i, p in enumerate(safety_papers):
            p.safety_metadata = metadata_extractors.extract_safety_metadata(client, p)
            _p("Extracting safety signals", i + 1, len(safety_papers))

    if by_category.get("real_world_evidence"):
        rwe_papers = by_category["real_world_evidence"]
        for i, p in enumerate(rwe_papers):
            p.geography = geo_extractor.extract_geography(client, p)
            _p("Extracting geography", i + 1, len(rwe_papers))

    # ── 6. Score relevance via LLM ──────────────────────────────────────────
    relevance_module.score_relevance_batch(
        client, kept, molecule, therapeutic_areas,
        progress_cb=lambda d, t: _p("Scoring relevance", d, t),
    )

    # ── 7. Enrich with SJR + citations ──────────────────────────────────────
    for i, p in enumerate(kept):
        sjr, _ = journal_metrics.get_sjr(p.journal)
        p.sjr = sjr
        _p("Looking up journal rankings", i + 1, len(kept))

    for i, p in enumerate(kept):
        p.citations = citations_module.get_citations(doi=p.doi, pmid=p.pmid)
        _p("Fetching citation counts", i + 1, len(kept))

    # ── 8. Composite score + breakdown ──────────────────────────────────────
    for p in kept:
        p.score = scoring.composite_score(p.sjr, p.citations, p.relevance)
        p.score_breakdown = scoring.score_breakdown(p.sjr, p.citations, p.relevance)

    # Re-sort by score
    for cid in by_category:
        by_category[cid].sort(key=lambda p: p.score, reverse=True)

    # ── 9. Aggregates ───────────────────────────────────────────────────────
    _p("Building dashboard aggregates", 0, 1)
    aggregates = aggregator.build_aggregates(by_category)
    _p("Building dashboard aggregates", 1, 1)

    # ── 10. Assemble report ─────────────────────────────────────────────────
    counts = {cid: len(plist) for cid, plist in by_category.items()}
    return MoleculeReport(
        molecule=molecule,
        drug_class=mol_entry.get("drug_class", ""),
        indication_hint=mol_entry.get("indication_hint", ""),
        search_params={
            "user_input":         user_input,
            "matched_term":       resolved.matched_term,
            "match_type":         resolved.match_type,
            "date_from":          date_from,
            "date_to":            date_to,
            "therapeutic_areas":  therapeutic_areas or [],
            "mesh_terms":         mesh or [],
            "query":              query,
        },
        total_pubmed_hits=total_hits,
        total_fetched=len(papers),
        total_classified=sum(counts.values()),
        papers=by_category,
        counts=counts,
        aggregates=aggregates,
        market_context=get_market_data(molecule),
        elapsed_seconds=round(time.time() - start, 1),
        pipeline_warnings=warnings,
    )


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _empty_report(
    molecule: str,
    mol_entry: dict,
    query: str,
    total_hits: int,
    date_from,
    date_to,
    therapeutic_areas: list[str] | None,
    warnings: list[str],
    start: float,
) -> MoleculeReport:
    """Build an empty MoleculeReport when no papers are found."""
    empty_by_cat = {cid: [] for cid in CATEGORIES}
    return MoleculeReport(
        molecule=molecule,
        drug_class=mol_entry.get("drug_class", ""),
        indication_hint=mol_entry.get("indication_hint", ""),
        search_params={
            "date_from": date_from,
            "date_to": date_to,
            "therapeutic_areas": therapeutic_areas or [],
            "query": query,
        },
        total_pubmed_hits=total_hits,
        total_fetched=0,
        total_classified=0,
        papers=empty_by_cat,
        counts={cid: 0 for cid in CATEGORIES},
        aggregates=aggregator.build_aggregates(empty_by_cat),
        market_context=get_market_data(molecule),
        elapsed_seconds=round(time.time() - start, 1),
        pipeline_warnings=warnings + ["No papers matched the search"],
    )
