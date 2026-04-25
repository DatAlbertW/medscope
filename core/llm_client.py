"""
Anthropic Claude client with strict JSON enforcement and recovery.

All LLM prompts live in config/prompts.py. This module only handles
the mechanics of calling Anthropic's API, enforcing JSON output, and
recovering from malformed responses.

Why Claude Haiku for this app:
  - Fast: typical classification call returns in 1-2 seconds
  - Cheap: roughly $0.001 per paper classified
  - Strong JSON adherence
  - Higher rate limits than Groq's free tier
"""
from __future__ import annotations

import json
import re
import time as _time
from typing import Iterator

from anthropic import Anthropic


# ── Model choice ────────────────────────────────────────────────────────────
# Claude Haiku 3.5 is the cost/speed sweet spot for structured extraction.
DEFAULT_MODEL = "claude-haiku-4-5"


# ════════════════════════════════════════════════════════════════════════════
#  CLIENT FACTORY
# ════════════════════════════════════════════════════════════════════════════

def get_client(api_key: str) -> Anthropic:
    """Instantiate an Anthropic client. Raises on missing or invalid key."""
    if not api_key or not api_key.startswith("sk-ant-"):
        raise ValueError(
            "Invalid Anthropic API key. Get a key at console.anthropic.com "
            "(it should start with 'sk-ant-')."
        )
    return Anthropic(api_key=api_key)


# ════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL CALL
# ════════════════════════════════════════════════════════════════════════════

def complete_json(
    client: Anthropic,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.1,
    model: str = DEFAULT_MODEL,
    max_retries: int = 4,
) -> dict:
    """
    Send a prompt to Anthropic expecting a JSON response.
    Retries on rate limits with exponential backoff.
    Returns a parsed dict, or raises ValueError on persistent failure.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw += block.text
            return parse_json(raw.strip())
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "overloaded" in err_str:
                wait = (2 ** attempt) + 1
                _time.sleep(wait)
                continue
            raise
    raise last_err if last_err else RuntimeError("complete_json failed")


def complete_text(
    client: Anthropic,
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.3,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Send a prompt to Anthropic and return the raw text response.
    Used by the chatbot where structured output is not required.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    out = ""
    for block in response.content:
        if hasattr(block, "text"):
            out += block.text
    return out.strip()


def stream_text(
    client: Anthropic,
    system: str,
    user: str,
    max_tokens: int = 800,
    temperature: float = 0.3,
    model: str = DEFAULT_MODEL,
) -> Iterator[str]:
    """
    Streaming version for the chatbot. Yields content deltas as they arrive
    so the UI can render live token-by-token.
    """
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for delta in stream.text_stream:
            if delta:
                yield delta


# ════════════════════════════════════════════════════════════════════════════
#  JSON PARSING WITH RECOVERY
# ════════════════════════════════════════════════════════════════════════════

def parse_json(raw: str) -> dict:
    """Parse `raw` as JSON, with recovery for code fences, prose, and truncation."""
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

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
    client: Anthropic,
    system: str,
    user: str,
    fallback: dict,
    max_tokens: int = 500,
) -> dict:
    """Wrap complete_json so callers never have to handle exceptions."""
    try:
        return complete_json(client, system, user, max_tokens=max_tokens)
    except Exception as e:
        return {**fallback, "_error": f"{type(e).__name__}: {str(e)[:300]}"}
