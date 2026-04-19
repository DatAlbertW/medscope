"""
The end-to-end orchestration pipeline.

Given a user's search (molecule + date range), this module produces
a fully populated MoleculeReport ready for the UI to render.

Pipeline stages:
    1. Resolve user input to canonical generic name (drug_resolver)
    2. Build PubMed query and preview count (pubmed_client)
    3. Fetch up to MAX_PAPERS_PER_SEARCH papers (pubmed_client)
    4. Classify each paper into one of the 4 categories (classifier)
    5. Extract structured metadata (geo / trial / safety) for category papers
    6. Enrich with SJR (journal_metrics) and citations (citations)
    7. Compute composite scores (config/scoring)
    8. Cap each category to MAX_PAPERS_PER_CATEGORY
    9. Build aggregates (aggregator)
   10. Attach market context (config/mock_market_data)
   11. Return MoleculeReport

The pipeline accepts progress callbacks so the UI can show live progress.
"""
from __future__ import annotations

import time
from typing import Callable

from groq import Groq

from config import filters, scoring
from config.categories import CATEGORIES
from config.mock_market_data import get_market_data
from config.molecules import get_molecule

from core import (
    aggregator,
    citations as citations_module,
    classifier,
    drug_resolver,
    geo_extractor,
    journal_metrics,
    metadata_extractors,
    pubmed_client,
)
from core.models import MoleculeReport, Paper


ProgressCb = Callable[[str, int, int], None] | None


# ════════════════════════════════════════════════════════════════════════════
#  PREVIEW (cheap — just resolves the molecule and counts PubMed hits)
# ════════════════════════════════════════════════════════════════════════════

def preview_search(
    user_input: str,
    date_from,
    date_to,
) -> dict:
    """
    Resolve user input to a generic name and return how many papers PubMed
    has for that search. Does NOT fetch or classify anything.
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

    query = pubmed_client.build_query(resolved.generic, date_from, date_to)
    count = pubmed_client.count_matches(query)

    return {
        "resolved": True,
        "input": user_input,
        "generic": resolved.generic,
        "matched_term": resolved.matched_term,
        "match_type": resolved.match_type,
        "match_confidence": resolved.confidence,
        "hit_count": count,
        "will_fetch": min(count, filters.MAX_PAPERS_PER_SEARCH),
        "query": query,
    }


# ════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def run_full_pipeline(
    client: Groq,
    user_input: str,
    year_from: int,
    year_to: int,
    progress_cb: ProgressCb = None,
) -> MoleculeReport:
    """
    Run the full end-to-end pipeline. Returns a populated MoleculeReport.
    `progress_cb(stage_name, done, total)` is invoked throughout.
    """
    start = time.time()
    warnings: list[str] = []

    def _p(stage: str, done: int, total: int):
        if progress_cb:
            progress_cb(stage, done, total)

    # ── 1. Resolve ───────────────────────────────────────────────────────────
    _p("Resolving molecule", 0, 1)
    resolved = drug_resolver.resolve(user_input)
    if not resolved.resolved:
        raise ValueError(f"Could not resolve '{user_input}' to a tracked molecule")
    molecule = resolved.generic
    mol_entry = resolved.molecule_entry or get_molecule(molecule) or {}
    _p("Resolving molecule", 1, 1)

    # ── 2. Build query + preview count ───────────────────────────────────────
    query = pubmed_client.build_query(molecule, year_from, year_to)
    total_hits = pubmed_client.count_matches(query)

    # ── 3. Fetch papers ──────────────────────────────────────────────────────
    _p("Searching PubMed", 0, 1)
    pmids = pubmed_client.search_pmids(query, retmax=filters.MAX_PAPERS_PER_SEARCH)
    _p("Searching PubMed", 1, 1)

    if not pmids:
        return _empty_report(molecule, mol_entry, query, total_hits,
                             year_from, year_to, warnings, start)

    _p("Fetching paper details", 0, len(pmids))
    papers = pubmed_client.fetch_papers(pmids)
    _p("Fetching paper details", len(papers), len(pmids))

    # ── 4. Classify ──────────────────────────────────────────────────────────
    def _classify_progress(done, total):
        _p("Classifying papers", done, total)

    classifier.classify_batch(client, papers, molecule, progress_cb=_classify_progress)

    included = [p for p in papers if p.decision == "INCLUDE" and p.category]

    # ── 5. Group by category + cap ──────────────────────────────────────────
    by_category: dict[str, list[Paper]] = {cid: [] for cid in CATEGORIES}
    for p in included:
        if p.category in by_category:
            by_category[p.category].append(p)

    # Cap to MAX_PAPERS_PER_CATEGORY (we'll re-sort after scoring)
    for cid, plist in by_category.items():
        if len(plist) > filters.MAX_PAPERS_PER_CATEGORY:
            by_category[cid] = plist[:filters.MAX_PAPERS_PER_CATEGORY]
            warnings.append(
                f"Category '{cid}' truncated to {filters.MAX_PAPERS_PER_CATEGORY} papers"
            )

    # Flatten for enrichment steps
    kept = [p for plist in by_category.values() for p in plist]

    # ── 6. Extract structured metadata for relevant categories ──────────────
    _p("Extracting trial metadata", 0, len(by_category.get("trial_results", [])))
    for i, p in enumerate(by_category.get("trial_results", [])):
        p.trial_metadata = metadata_extractors.extract_trial_metadata(client, p)
        _p("Extracting trial metadata", i + 1, len(by_category["trial_results"]))

    _p("Extracting safety signals", 0, len(by_category.get("safety_efficacy", [])))
    for i, p in enumerate(by_category.get("safety_efficacy", [])):
        p.safety_metadata = metadata_extractors.extract_safety_metadata(client, p)
        _p("Extracting safety signals", i + 1, len(by_category["safety_efficacy"]))

    _p("Extracting geography", 0, len(by_category.get("real_world_evidence", [])))
    for i, p in enumerate(by_category.get("real_world_evidence", [])):
        p.geography = geo_extractor.extract_geography(client, p)
        _p("Extracting geography", i + 1, len(by_category["real_world_evidence"]))

    # ── 7. Enrich with SJR ──────────────────────────────────────────────────
    _p("Looking up journal rankings", 0, len(kept))
    for i, p in enumerate(kept):
        sjr, _ = journal_metrics.get_sjr(p.journal)
        p.sjr = sjr
        _p("Looking up journal rankings", i + 1, len(kept))

    # ── 8. Enrich with citations ────────────────────────────────────────────
    _p("Fetching citation counts", 0, len(kept))
    for i, p in enumerate(kept):
        p.citations = citations_module.get_citations(doi=p.doi, pmid=p.pmid)
        _p("Fetching citation counts", i + 1, len(kept))

    # ── 9. Compute composite scores ─────────────────────────────────────────
    for p in kept:
        p.score = scoring.composite_score(p.sjr, p.citations)

    # Re-sort each category by score descending
    for cid in by_category:
        by_category[cid].sort(key=lambda p: p.score, reverse=True)

    # ── 10. Build aggregates ────────────────────────────────────────────────
    _p("Building dashboard aggregates", 0, 1)
    aggregates = aggregator.build_aggregates(by_category)
    _p("Building dashboard aggregates", 1, 1)

    # ── 11. Assemble report ─────────────────────────────────────────────────
    counts = {cid: len(plist) for cid, plist in by_category.items()}
    report = MoleculeReport(
        molecule=molecule,
        drug_class=mol_entry.get("drug_class", ""),
        indication_hint=mol_entry.get("indication_hint", ""),
        search_params={
            "user_input":   user_input,
            "matched_term": resolved.matched_term,
            "match_type":   resolved.match_type,
            "year_from":    year_from,
            "year_to":      year_to,
            "query":        query,
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
    return report


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _empty_report(
    molecule: str,
    mol_entry: dict,
    query: str,
    total_hits: int,
    year_from: int,
    year_to: int,
    warnings: list[str],
    start: float,
) -> MoleculeReport:
    """Build an empty report when no papers are found."""
    empty_by_cat = {cid: [] for cid in CATEGORIES}
    return MoleculeReport(
        molecule=molecule,
        drug_class=mol_entry.get("drug_class", ""),
        indication_hint=mol_entry.get("indication_hint", ""),
        search_params={
            "year_from": year_from,
            "year_to": year_to,
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
