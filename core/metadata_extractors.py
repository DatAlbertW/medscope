"""
Structured metadata extractors.

Two LLM-backed extractors:
    - extract_trial_metadata: pulls NCT id, phase, primary endpoint/result
      for papers classified as Trial Results.
    - extract_safety_metadata: pulls top adverse events, serious AEs flag,
      discontinuation rate, efficacy signal for papers classified as
      Safety & Efficacy.

These are called selectively from the pipeline (only for papers that land
in the relevant category) to avoid wasting LLM tokens.
"""
from __future__ import annotations

from anthropic import Anthropic

from config.prompts import (
    EXTRACT_TRIAL_METADATA_PROMPT,
    EXTRACT_SAFETY_PROMPT,
    SYSTEM_EXTRACTOR,
)
from core.llm_client import safe_json_call
from core.models import Paper


_TRIAL_FALLBACK = {
    "phase": "Not specified",
    "nct_id": None,
    "primary_endpoint": None,
    "primary_result": None,
    "n_enrolled": None,
    "comparator": None,
}

_SAFETY_FALLBACK = {
    "most_common_aes": [],
    "serious_aes_mentioned": False,
    "discontinuation_rate": None,
    "efficacy_signal": None,
}


# ════════════════════════════════════════════════════════════════════════════
#  TRIAL METADATA
# ════════════════════════════════════════════════════════════════════════════

def extract_trial_metadata(client: Anthropic, paper: Paper) -> dict:
    if not paper.abstract:
        return dict(_TRIAL_FALLBACK)

    prompt = EXTRACT_TRIAL_METADATA_PROMPT.format(
        title=paper.title[:300],
        abstract=paper.abstract[:1500],
    )
    return safe_json_call(
        client,
        system=SYSTEM_EXTRACTOR,
        user=prompt,
        fallback=dict(_TRIAL_FALLBACK),
        max_tokens=250,
    )


# ════════════════════════════════════════════════════════════════════════════
#  SAFETY METADATA
# ════════════════════════════════════════════════════════════════════════════

def extract_safety_metadata(client: Anthropic, paper: Paper) -> dict:
    if not paper.abstract:
        return dict(_SAFETY_FALLBACK)

    prompt = EXTRACT_SAFETY_PROMPT.format(
        title=paper.title[:300],
        abstract=paper.abstract[:1500],
    )
    return safe_json_call(
        client,
        system=SYSTEM_EXTRACTOR,
        user=prompt,
        fallback=dict(_SAFETY_FALLBACK),
        max_tokens=250,
    )
