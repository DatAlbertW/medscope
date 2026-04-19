"""
Build aggregated summary data for the dashboard view.

Input:  a list of classified Papers
Output: a dict of aggregates (counts by year, top papers, geography,
        trial phases, top AEs, top journals) that the UI renders
        as charts and summary cards.

All aggregation is pure Python — no LLM calls. This keeps the dashboard
fast to recompute if the user re-filters.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from core.models import Paper


# ════════════════════════════════════════════════════════════════════════════
#  TOP-LEVEL AGGREGATOR
# ════════════════════════════════════════════════════════════════════════════

def build_aggregates(papers_by_category: dict[str, list[Paper]]) -> dict[str, Any]:
    """
    Build the aggregate dict that feeds the dashboard.
    Keys: top_papers, yearly_counts, trial_phases, top_adverse_events,
          geography, top_journals.
    """
    all_papers: list[Paper] = []
    for plist in papers_by_category.values():
        all_papers.extend(plist)

    return {
        "top_papers":         _top_papers(all_papers, n=5),
        "yearly_counts":      _yearly_counts(papers_by_category),
        "trial_phases":       _trial_phases(papers_by_category.get("trial_results", [])),
        "top_adverse_events": _top_aes(papers_by_category.get("safety_efficacy", [])),
        "geography":          _geography(papers_by_category.get("real_world_evidence", [])),
        "top_journals":       _top_journals(all_papers, n=10),
    }


# ════════════════════════════════════════════════════════════════════════════
#  INDIVIDUAL AGGREGATORS
# ════════════════════════════════════════════════════════════════════════════

def _top_papers(papers: list[Paper], n: int = 5) -> list[dict]:
    """Return the top N papers by composite score."""
    ranked = sorted(papers, key=lambda p: p.score, reverse=True)
    return [{
        "pmid":       p.pmid,
        "title":      p.title,
        "journal":    p.journal,
        "year":       p.pub_year,
        "score":      p.score,
        "category":   p.category,
        "url":        p.pubmed_url,
    } for p in ranked[:n]]


def _yearly_counts(papers_by_category: dict[str, list[Paper]]) -> dict[str, dict[int, int]]:
    """
    Return papers-per-year counts, per category.
    Structure: { "clinically_relevant": { 2022: 4, 2023: 7, ... }, ... }
    """
    out: dict[str, dict[int, int]] = {}
    for cat, plist in papers_by_category.items():
        counts: dict[int, int] = defaultdict(int)
        for p in plist:
            if p.pub_year:
                counts[p.pub_year] += 1
        out[cat] = dict(sorted(counts.items()))
    return out


def _trial_phases(trial_papers: list[Paper]) -> dict[str, int]:
    """Count papers by trial phase (from paper.trial_metadata)."""
    counts: Counter = Counter()
    for p in trial_papers:
        meta = p.trial_metadata or {}
        phase = meta.get("phase") or "Not specified"
        counts[phase] += 1
    # Stable ordering: known phases first, then "Not specified" / "Other"
    canonical_order = ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Not specified"]
    ordered = {k: counts.get(k, 0) for k in canonical_order if counts.get(k, 0) > 0}
    for k, v in counts.items():
        if k not in ordered and v > 0:
            ordered[k] = v
    return ordered


def _top_aes(safety_papers: list[Paper]) -> list[tuple[str, int]]:
    """Count most common adverse events across all Safety & Efficacy papers."""
    counts: Counter = Counter()
    for p in safety_papers:
        meta = p.safety_metadata or {}
        for ae in meta.get("most_common_aes") or []:
            if isinstance(ae, str) and ae.strip():
                counts[ae.strip().lower()] += 1
    return counts.most_common(10)


def _geography(rwe_papers: list[Paper]) -> list[dict]:
    """
    Build a list of geographic points for the world map.
    Each entry: { country, iso2, region, city, cohort_size, paper_pmid, title }
    """
    out = []
    for p in rwe_papers:
        g = p.geography or {}
        if not g.get("country"):
            continue
        out.append({
            "country":     g.get("country"),
            "iso2":        g.get("country_iso2"),
            "region":      g.get("region"),
            "city":        g.get("city"),
            "cohort_size": g.get("cohort_size"),
            "paper_pmid":  p.pmid,
            "title":       p.title,
            "url":         p.pubmed_url,
        })
    return out


def _top_journals(papers: list[Paper], n: int = 10) -> list[dict]:
    """Top N journals by paper count, with their average SJR."""
    by_journal: dict[str, list[Paper]] = defaultdict(list)
    for p in papers:
        if p.journal:
            by_journal[p.journal].append(p)

    rows = []
    for journal, plist in by_journal.items():
        sjrs = [p.sjr for p in plist if p.sjr is not None]
        avg_sjr = round(sum(sjrs) / len(sjrs), 2) if sjrs else None
        rows.append({
            "journal":     journal,
            "paper_count": len(plist),
            "avg_sjr":     avg_sjr,
        })
    rows.sort(key=lambda r: (r["paper_count"], r["avg_sjr"] or 0), reverse=True)
    return rows[:n]
