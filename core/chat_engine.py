"""
Chatbot engine for the dashboard.

Tight scope: the user picks ONE predefined question at a time. The LLM
answers using ONLY the loaded MoleculeReport — no outside knowledge.

The answer streams live token-by-token so the UI can render as it arrives
(rather than waiting for a full response).
"""
from __future__ import annotations

import json
from typing import Iterator

from anthropic import Anthropic

from core.llm_client import stream_text
from core.models import MoleculeReport


# ════════════════════════════════════════════════════════════════════════════
#  PREDEFINED QUESTIONS
# ════════════════════════════════════════════════════════════════════════════
# Each question has an ID, a user-facing label, and the exact instruction
# sent to the LLM. Questions reference the loaded report — the LLM must
# answer only from that data.

PREDEFINED_QUESTIONS = [
    {
        "id": "strongest_evidence",
        "label": "What are the strongest pieces of evidence for this molecule?",
        "instruction": (
            "Identify the 3-4 strongest papers in the loaded dataset based on "
            "composite score (SJR + citations), study design, and clinical relevance. "
            "For each, give a one-line summary of why it matters."
        ),
    },
    {
        "id": "safety_summary",
        "label": "What are the key safety signals across the literature?",
        "instruction": (
            "Summarise the safety profile across the Safety & Efficacy papers. "
            "List the most commonly reported adverse events, note whether serious AEs "
            "appeared, and flag any discontinuation patterns."
        ),
    },
    {
        "id": "trial_landscape",
        "label": "What does the trial landscape look like?",
        "instruction": (
            "Describe the clinical trial landscape in the data. "
            "Summarise the phase distribution, primary endpoints seen most often, "
            "and notable comparators. Flag any pivotal trials."
        ),
    },
    {
        "id": "rwe_gaps",
        "label": "Where is real-world evidence strong or missing?",
        "instruction": (
            "Describe the geographic distribution of real-world evidence. "
            "Identify regions with strong RWE coverage and regions where RWE is "
            "sparse or absent. Call out cohort sizes where notable."
        ),
    },
    {
        "id": "evidence_gaps",
        "label": "What evidence gaps exist across all categories?",
        "instruction": (
            "Identify the most important evidence gaps in the loaded dataset. "
            "Look across all four categories and point out areas where "
            "published evidence is thin or missing. Be specific."
        ),
    },
    {
        "id": "publication_trends",
        "label": "How has the publication volume evolved over time?",
        "instruction": (
            "Describe the publication trend over the date range covered. "
            "Note years with peaks or drops, and whether momentum is growing or "
            "slowing for this molecule."
        ),
    },
    {
        "id": "top_journals",
        "label": "Which journals are publishing most on this molecule?",
        "instruction": (
            "List the top journals by paper count in the loaded data, and what "
            "this tells us about the publication strategy and venues used for "
            "this molecule."
        ),
    },
    {
        "id": "manuscript_opportunity",
        "label": "What manuscript opportunities could ContentEd Med propose?",
        "instruction": (
            "Based on the evidence gaps and publication landscape, suggest 2-3 "
            "concrete manuscript opportunities a medical communications agency "
            "could propose to a pharma client. Include manuscript type and "
            "target journal tier for each."
        ),
    },
]


# ════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_CHAT = (
    "You are a medical affairs analyst embedded in a publications intelligence tool. "
    "You answer questions about a specific molecule using ONLY the data provided "
    "in the context. Do NOT use outside knowledge. If the answer is not supported "
    "by the data, say so clearly. Keep responses concise, structured, and factual. "
    "Use bullet points and short paragraphs. No speculation."
)


# ════════════════════════════════════════════════════════════════════════════
#  CONTEXT BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_context(report: MoleculeReport, max_papers_per_cat: int = 10) -> str:
    """
    Serialise the MoleculeReport into a compact text context for the LLM.
    Truncates paper lists to keep token usage manageable.
    """
    lines = [
        f"MOLECULE: {report.molecule}",
        f"DRUG CLASS: {report.drug_class}",
        f"INDICATION HINT: {report.indication_hint}",
        f"SEARCH PARAMS: {json.dumps(report.search_params)}",
        f"TOTAL PAPERS FOUND: {report.total_pubmed_hits}",
        f"TOTAL PAPERS CLASSIFIED: {report.total_classified}",
        "",
        "COUNTS BY CATEGORY:",
    ]
    for cat, n in report.counts.items():
        lines.append(f"  - {cat}: {n}")

    lines.append("")
    lines.append("AGGREGATES:")
    lines.append(json.dumps(report.aggregates, default=str, indent=2)[:3000])

    lines.append("")
    lines.append("TOP PAPERS PER CATEGORY (truncated):")
    for cat, plist in report.papers.items():
        lines.append(f"\n[{cat}]")
        top = sorted(plist, key=lambda p: p.score, reverse=True)[:max_papers_per_cat]
        for p in top:
            lines.append(
                f"  - PMID {p.pmid} | {p.journal} ({p.pub_year}) | "
                f"score {p.score} | {p.study_type}"
            )
            lines.append(f"    Title: {p.title[:180]}")
            if p.key_finding:
                lines.append(f"    Finding: {p.key_finding[:200]}")

    if report.market_context:
        lines.append("")
        lines.append("MARKET CONTEXT (illustrative mock data):")
        lines.append(json.dumps(report.market_context, default=str, indent=2)[:1200])

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
#  ASK
# ════════════════════════════════════════════════════════════════════════════

def ask(
    client: Anthropic,
    report: MoleculeReport,
    question_id: str,
) -> Iterator[str]:
    """
    Stream the answer to a predefined question as content deltas.
    Raises ValueError if the question_id is unknown.
    """
    q = next((q for q in PREDEFINED_QUESTIONS if q["id"] == question_id), None)
    if not q:
        raise ValueError(f"Unknown question id: {question_id}")

    context = build_context(report)
    user_prompt = (
        f"DATA CONTEXT:\n{context}\n\n"
        f"---\n\n"
        f"QUESTION: {q['label']}\n\n"
        f"INSTRUCTION: {q['instruction']}\n\n"
        f"Answer using ONLY the data above."
    )

    yield from stream_text(
        client,
        system=SYSTEM_CHAT,
        user=user_prompt,
        max_tokens=900,
        temperature=0.3,
    )


def get_question_labels() -> list[tuple[str, str]]:
    """Return (id, label) pairs for UI rendering."""
    return [(q["id"], q["label"]) for q in PREDEFINED_QUESTIONS]
