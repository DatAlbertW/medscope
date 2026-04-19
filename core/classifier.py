"""
Paper classifier.

For each paper, calls the LLM to decide:
    - Is this paper relevant (INCLUDE) or should it be dropped (EXCLUDE)?
    - If INCLUDE, which of the 4 categories does it belong to?

Also extracts the study type, key finding, and confidence score.
Uses config/prompts.CLASSIFY_PROMPT and config/categories.CATEGORIES.
"""
from __future__ import annotations

from groq import Groq

from config.categories import CATEGORIES, GLOBAL_EXCLUSIONS
from config.prompts import CLASSIFY_PROMPT, SYSTEM_CLASSIFIER
from core.llm_client import safe_json_call
from core.models import Paper


_FALLBACK = {
    "decision": "EXCLUDE",
    "category": None,
    "confidence": 0.0,
    "study_type": "Other",
    "key_finding": "",
    "reasoning": "Classification failed, excluded by default",
}


def _build_categories_block() -> str:
    """Render the category list for insertion into the prompt."""
    lines = []
    for cid, cdef in CATEGORIES.items():
        lines.append(f"- {cid}: {cdef['description']}")
    return "\n".join(lines)


_CATEGORIES_BLOCK = _build_categories_block()


# ════════════════════════════════════════════════════════════════════════════
#  PRE-LLM FAST EXCLUSIONS
# ════════════════════════════════════════════════════════════════════════════

def _fast_exclude(paper: Paper) -> bool:
    """
    Return True if the paper can be excluded without calling the LLM,
    based on simple keyword markers for animal-only / in-vitro-only work.
    Saves tokens on obviously-out-of-scope papers.
    """
    text = f"{paper.title}\n{paper.abstract}".lower()

    for marker in GLOBAL_EXCLUSIONS["animal_only_markers"]:
        if marker.lower() in text and "patient" not in text and "human" not in text:
            return True

    for marker in GLOBAL_EXCLUSIONS["in_vitro_only_markers"]:
        if marker.lower() in text and "clinical" not in text and "patient" not in text:
            return True

    # No abstract at all — we can't classify; drop
    if not paper.abstract or len(paper.abstract) < 50:
        return True

    return False


# ════════════════════════════════════════════════════════════════════════════
#  CLASSIFIER
# ════════════════════════════════════════════════════════════════════════════

def classify(client: Groq, paper: Paper, molecule: str) -> Paper:
    """
    Classify a single paper. Mutates and returns the Paper object.
    """
    # Fast path
    if _fast_exclude(paper):
        paper.decision = "EXCLUDE"
        paper.category = None
        paper.reasoning = "Fast-excluded (animal-only, in-vitro-only, or no abstract)"
        return paper

    prompt = CLASSIFY_PROMPT.format(
        molecule=molecule,
        title=paper.title[:300],
        abstract=paper.abstract[:1500],
        categories_block=_CATEGORIES_BLOCK,
    )
    result = safe_json_call(
        client,
        system=SYSTEM_CLASSIFIER,
        user=prompt,
        fallback=dict(_FALLBACK),
        max_tokens=300,
    )

    decision = str(result.get("decision", "EXCLUDE")).upper()
    paper.decision = "INCLUDE" if decision == "INCLUDE" else "EXCLUDE"
    paper.category = result.get("category") if paper.decision == "INCLUDE" else None
    paper.classification_confidence = float(result.get("confidence") or 0.0)
    paper.study_type = str(result.get("study_type") or "Other")
    paper.key_finding = str(result.get("key_finding") or "")[:200]
    paper.reasoning = str(result.get("reasoning") or "")[:200]

    # Belt-and-braces: validate category ID if present
    if paper.category and paper.category not in CATEGORIES:
        paper.decision = "EXCLUDE"
        paper.category = None
        paper.reasoning = f"LLM returned unknown category: {paper.category}"

    return paper


def classify_batch(client: Groq, papers: list[Paper], molecule: str,
                   progress_cb=None) -> list[Paper]:
    """Classify a list of papers. Calls progress_cb(i, total) after each paper."""
    total = len(papers)
    # Debug counters
    stats = {"INCLUDE": 0, "EXCLUDE_fast": 0, "EXCLUDE_llm": 0,
             "by_category": {}, "sample_reasons": []}
    for i, p in enumerate(papers):
        classify(client, p, molecule)
        if p.decision == "INCLUDE":
            stats["INCLUDE"] += 1
            cat = p.category or "none"
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        else:
            if "Fast-excluded" in (p.reasoning or ""):
                stats["EXCLUDE_fast"] += 1
            else:
                stats["EXCLUDE_llm"] += 1
                if len(stats["sample_reasons"]) < 10:
                    stats["sample_reasons"].append(
                        f"[{p.pmid}] {p.title[:60]}... → {p.reasoning[:100]}"
                    )
        if progress_cb:
            progress_cb(i + 1, total)
    # Attach stats to the first paper so they surface in warnings
    if papers:
        papers[0]._classify_stats = stats  # type: ignore
    return papers
