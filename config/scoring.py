"""
Composite paper score configuration.

Each paper gets a 0-100 score combining three signals:

    - Relevance  (LLM): how directly the paper addresses the molecule and
                        the selected therapeutic area
    - SJR:       journal prestige from SCImago Journal Rank
    - Citations: scholarly impact from OpenAlex citation count

Default weights are 40/30/30. Relevance leads because it captures
"is this paper actually about what I asked?" — a question SJR and
citations can't answer.

To rebalance, edit WEIGHTS below. They must sum to 1.0.
The anchor lists below define how raw SJR values and citation counts
are normalised onto a 0-100 scale (with diminishing returns).
"""

# ── Weights (must sum to 1.0) ───────────────────────────────────────────────
WEIGHTS = {
    "relevance": 0.40,
    "sjr":       0.30,
    "citations": 0.30,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, \
    f"scoring.WEIGHTS must sum to 1.0, got {sum(WEIGHTS.values())}"


# ── SJR normalization ───────────────────────────────────────────────────────
# Anchor list maps raw SJR → 0-100 score, with diminishing returns.
# Reference: NEJM ~25, JAMA ~13, mid-tier specialty 2-8, niche <1.
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
# Citation counts grow over time, so we apply a soft log-style curve.
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
    """Linear-interpolate `value` between anchor points (sorted high→low)."""
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


def normalize_relevance(relevance: float | None) -> float:
    """
    Relevance comes from the LLM already on a 0-100 scale, so we just
    clamp to [0, 100]. Returns 0 if missing.
    """
    if relevance is None:
        return 0.0
    return max(0.0, min(100.0, float(relevance)))


def composite_score(sjr: float | None,
                    citations: int | None,
                    relevance: float | None = None) -> float:
    """Compute the composite 0-100 score given raw metrics."""
    rel_score = normalize_relevance(relevance)
    sjr_score = normalize_sjr(sjr)
    cit_score = normalize_citations(citations)

    score = (
        WEIGHTS["relevance"] * rel_score +
        WEIGHTS["sjr"]       * sjr_score +
        WEIGHTS["citations"] * cit_score
    )
    return round(score, 1)


def score_breakdown(sjr: float | None,
                    citations: int | None,
                    relevance: float | None = None) -> dict:
    """
    Return both raw and normalized values for the tooltip display.
    Used by the UI to render hover tooltips like:
        Relevance 92.0 · SJR 65.4 (raw 7.2) · Citations 70.0 (raw 145) → 75.6
    """
    rel = normalize_relevance(relevance)
    sjr_norm = normalize_sjr(sjr)
    cit_norm = normalize_citations(citations)
    composite = round(
        WEIGHTS["relevance"] * rel +
        WEIGHTS["sjr"]       * sjr_norm +
        WEIGHTS["citations"] * cit_norm,
        1,
    )
    return {
        "relevance":      round(rel, 1),
        "sjr_norm":       round(sjr_norm, 1),
        "sjr_raw":        round(float(sjr), 2) if sjr is not None else None,
        "citations_norm": round(cit_norm, 1),
        "citations_raw":  int(citations) if citations is not None else None,
        "composite":      composite,
        "weights":        dict(WEIGHTS),
    }
