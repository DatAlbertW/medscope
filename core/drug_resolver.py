"""
Resolve user input (brand name, synonym, misspelling) to the canonical
generic molecule name.

Strategy:
    1. Exact case-insensitive match against generics, brands, synonyms
    2. Fuzzy match (rapidfuzz) with a score threshold
    3. Return resolved generic + confidence + match reason

The user ALWAYS searches PubMed using the generic name. This module is
the single point where "Herceptin" and "trastuzomab" (typo) become
"Trastuzumab" before hitting the API.
"""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from config.molecules import get_all_search_terms, get_molecule


# Minimum fuzzy score (0-100) to accept a fuzzy match
FUZZY_THRESHOLD = 80


@dataclass
class ResolvedMolecule:
    """Result of a search-term resolution attempt."""
    generic: str | None           # canonical generic, or None if not resolved
    matched_term: str | None      # what the user's input was matched against
    match_type: str               # "exact" | "fuzzy" | "not_found"
    confidence: float             # 0-100
    molecule_entry: dict | None   # full entry from config/molecules.py

    @property
    def resolved(self) -> bool:
        return self.generic is not None


# ════════════════════════════════════════════════════════════════════════════
#  RESOLVER
# ════════════════════════════════════════════════════════════════════════════

def resolve(user_input: str) -> ResolvedMolecule:
    """
    Resolve free-text user input to a canonical generic molecule name.
    Returns a ResolvedMolecule even on failure (with generic=None).
    """
    if not user_input or not user_input.strip():
        return ResolvedMolecule(None, None, "not_found", 0.0, None)

    query = user_input.strip()
    pairs = get_all_search_terms()   # list of (display_term, canonical_generic)

    # ── 1. Exact case-insensitive match ─────────────────────────────────────
    for display, generic in pairs:
        if display.lower() == query.lower():
            return ResolvedMolecule(
                generic=generic,
                matched_term=display,
                match_type="exact",
                confidence=100.0,
                molecule_entry=get_molecule(generic),
            )

    # ── 2. Fuzzy match ──────────────────────────────────────────────────────
    # rapidfuzz.process.extractOne needs a list of strings, so we separate then reunite
    display_terms = [d for d, _ in pairs]
    best = process.extractOne(
        query,
        display_terms,
        scorer=fuzz.WRatio,
        score_cutoff=FUZZY_THRESHOLD,
    )
    if best is not None:
        matched_display, score, index = best
        _, generic = pairs[index]
        return ResolvedMolecule(
            generic=generic,
            matched_term=matched_display,
            match_type="fuzzy",
            confidence=float(score),
            molecule_entry=get_molecule(generic),
        )

    # ── 3. Not found ────────────────────────────────────────────────────────
    return ResolvedMolecule(None, None, "not_found", 0.0, None)
