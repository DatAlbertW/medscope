"""
Typed data structures used across the engine.

Using dataclasses (not pydantic) to keep deps light. These define the
shape of everything that flows through the pipeline and into the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# ════════════════════════════════════════════════════════════════════════════
#  PAPER
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Paper:
    """A single PubMed paper with classification and enrichment metadata."""

    # Core PubMed fields
    pmid: str
    title: str
    abstract: str
    journal: str
    pub_date: str               # ISO-ish: "2024-03-15" or "2024" if month unknown
    pub_year: int | None
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    doi: str | None = None

    # Derived
    pubmed_url: str = ""

    # Classification (from LLM)
    decision: str = "PENDING"               # INCLUDE | EXCLUDE | PENDING
    category: str | None = None             # one of the 4 category IDs
    classification_confidence: float = 0.0
    study_type: str = "Other"
    key_finding: str = ""
    reasoning: str = ""

    # Scoring
    sjr: float | None = None
    citations: int | None = None
    score: float = 0.0                      # composite 0-100

    # Optional extracted metadata (populated only if classified into relevant category)
    trial_metadata: dict | None = None      # for Trial Results
    safety_metadata: dict | None = None     # for Safety & Efficacy
    geography: dict | None = None           # for RWE

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════════════════════
#  MOLECULE REPORT (the single source of truth for the UI)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class MoleculeReport:
    """Everything the UI needs to render the dashboard + 4 category tabs."""

    # Identity
    molecule: str                           # canonical generic name
    drug_class: str = ""
    indication_hint: str = ""

    # Search context
    search_params: dict = field(default_factory=dict)   # date range, filters used
    total_pubmed_hits: int = 0                          # how many PubMed returned
    total_fetched: int = 0                              # how many we actually fetched
    total_classified: int = 0                           # after exclusions

    # Classified papers, keyed by category ID
    papers: dict[str, list[Paper]] = field(default_factory=dict)

    # Aggregates for dashboard rendering
    counts: dict[str, int] = field(default_factory=dict)
    aggregates: dict[str, Any] = field(default_factory=dict)

    # Market context (from config/mock_market_data.py)
    market_context: dict | None = None

    # Timing / debug info
    elapsed_seconds: float = 0.0
    pipeline_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert nested Paper lists
        d["papers"] = {
            cat: [p if isinstance(p, dict) else p.to_dict() for p in plist]
            for cat, plist in self.papers.items()
        }
        return d
