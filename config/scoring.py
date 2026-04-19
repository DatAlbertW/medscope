"""
Composite paper score configuration.

Each paper is assigned a score from 0-100 composed of two signals:
    - Journal prestige (SJR — SCImago Journal Rank)
    - Citation count

Relevance was intentionally excluded from the POC (keeping it simple).
It can be reintroduced by setting RELEVANCE_WEIGHT > 0 and wiring up
an LLM relevance call in the pipeline.

To rebalance the score, adjust the WEIGHTS dict below. All weights must
sum to 1.0. The `_normalize()` functions below define how raw metrics
are converted into a 0-100 scale before weighting.
"""

# ── Weights (must sum to 1.0) ───────────────────────────────────────────────
WEIGHTS = {
    "sjr":       0.55,   # journal prestige
    "citations": 0.45,   # scholarly impact
    "relevance": 0.00,   # disabled for POC; reserved for future LLM relevance
}

# Sanity check — enforce weights sum to 1.0 at import time
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, \
    f"scoring.WEIGHTS must sum to 1.0, got {sum(WEIGHTS.values())}"


# ── SJR normalization (CATEGORY Q ranking) ──────────────────────────────────
# SCImago classifies journals into quartiles (Q1-Q4) by field. We convert
# the SJR raw number into a 0-100 score with diminishing returns.
#
# Rough anchors (based on typical biomedical journal SJR values):
#   SJR 25+  →  100  (NEJM, Lancet, JAMA tier)
#   SJR 10   →   80
#   SJR 5    →   65
#   SJR 2    →   45
#   SJR 1    →   30
#   SJR <0.3 →   10

SJR_ANCHORS = [
    (25.0, 100),
    (10.0,  80),
    ( 5.0,  65),
    ( 2.0,  45),
    ( 1.0,  30),
    ( 0.3,  10),
    ( 0.0,   0),
]


# ── Citation normalization ──────────────────────────────────────────────────
# Citations grow over time, so we apply a simple log-style curve.
# Anchors are (citation_count, normalized_score).

CITATION_ANCHORS = [
    (500, 100),
    (200,  85),
    (100,  70),
    ( 50,  55),
    ( 20,  40),
    ( 10,  25),
    (  5,  15),
    (  0,   0),
]


def _interpolate(value: float, anchors: list[tuple[float, float]]) -> float:
    """
    Linear-interpolate `value` between two adjacent anchor points.
    Anchors must be sorted from highest to lowest `value`.
    """
    if value >= anchors[0][0]:
        return float(anchors[0][1])
    if value <= anchors[-1][0]:
        return float(anchors[-1][1])
    for (hi_v, hi_s), (lo_v, lo_s) in zip(anchors, anchors[1:]):
        if lo_v <= value <= hi_v:
            span = hi_v - lo_v
            pos = (value - lo_v) / span if span else 0
            return lo_s + pos * (hi_s - lo_s)
    return 0.0


def normalize_sjr(sjr: float | None) -> float:
    """Convert a raw SJR value (e.g. 7.2) into a 0-100 score."""
    if sjr is None or sjr < 0:
        return 0.0
    return _interpolate(float(sjr), SJR_ANCHORS)


def normalize_citations(count: int | None) -> float:
    """Convert a citation count into a 0-100 score."""
    if count is None or count < 0:
        return 0.0
    return _interpolate(float(count), CITATION_ANCHORS)


def composite_score(sjr: float | None, citations: int | None,
                    relevance: float | None = None) -> float:
    """
    Compute the composite 0-100 score given raw metrics.
    Relevance is optional and only used if WEIGHTS['relevance'] > 0.
    """
    sjr_score = normalize_sjr(sjr)
    cit_score = normalize_citations(citations)
    rel_score = float(relevance) if relevance is not None else 0.0

    score = (
        WEIGHTS["sjr"]       * sjr_score +
        WEIGHTS["citations"] * cit_score +
        WEIGHTS["relevance"] * rel_score
    )
    return round(score, 1)
