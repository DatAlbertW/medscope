"""
Groq / LLaMA client with strict JSON enforcement and recovery.

All LLM prompts live in config/prompts.py. This module only handles
the mechanics of calling Groq, enforcing JSON output, and recovering
from malformed responses.
"""
from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq


# ── Model choice ────────────────────────────────────────────────────────────
# llama-3.3-70b-versatile is Groq's current flagship free-tier model.
# Adjust here if a newer model becomes available.
DEFAULT_MODEL = "llama-3.3-70b-versatile"


# ════════════════════════════════════════════════════════════════════════════
#  CLIENT FACTORY
# ════════════════════════════════════════════════════════════════════════════

def get_client(api_key: str) -> Groq:
    """Instantiate a Groq client. Raises on missing or empty key."""
    if not api_key or not api_key.startswith("gsk_"):
        raise ValueError(
            "Invalid Groq API key. Get a free key at https://console.groq.com"
        )
    return Groq(api_key=api_key)


# ════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL CALL
# ════════════════════════════════════════════════════════════════════════════

def complete_json(
    client: Groq,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.1,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Send a prompt to Groq expecting a JSON response.
    Returns a parsed dict, or raises ValueError with the raw response if parsing fails.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = response.choices[0].message.content.strip()
    return parse_json(raw)


def complete_text(
    client: Groq,
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.3,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Send a prompt to Groq and return the raw text response.
    Used by the chatbot where structured output is not required.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def stream_text(
    client: Groq,
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.3,
    model: str = DEFAULT_MODEL,
):
    """
    Streaming version for the chatbot. Yields content deltas as they arrive
    so the UI can render live token-by-token.
    """
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ════════════════════════════════════════════════════════════════════════════
#  JSON PARSING WITH RECOVERY
# ════════════════════════════════════════════════════════════════════════════

def parse_json(raw: str) -> dict:
    """
    Attempt to parse `raw` as JSON, with recovery for:
        - Markdown code fences (```json ... ```)
        - Surrounding prose text
        - Truncated responses (closes unclosed brackets)
    """
    # Strip code fences
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()

    # Extract outermost JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    # First attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Repair: trim trailing comma / incomplete final key, close brackets
    repaired = cleaned.rstrip().rstrip(",")
    repaired = re.sub(r',\s*"[^"]*$', "", repaired)
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse LLM response as JSON. Raw: {raw[:300]}")


# ════════════════════════════════════════════════════════════════════════════
#  SAFE WRAPPER (never crashes — returns a fallback dict on failure)
# ════════════════════════════════════════════════════════════════════════════

def safe_json_call(
    client: Groq,
    system: str,
    user: str,
    fallback: dict,
    max_tokens: int = 500,
) -> dict:
    """
    Wrap complete_json so that callers never have to handle exceptions.
    Returns `fallback` (with an `_error` key added) on any failure.
    """
    try:
        return complete_json(client, system, user, max_tokens=max_tokens)
    except Exception as e:
        return {**fallback, "_error": str(e)[:120]}
