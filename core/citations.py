"""
Citation counts via OpenAlex.

OpenAlex is a free, open replacement for Web of Science / Scopus
with no API key required (polite rate limit: 100k requests/day).

We look up by DOI when available, fall back to PMID, and return the
`cited_by_count` field. Results are cached in-memory for the app lifetime.

Reference: https://docs.openalex.org/
"""
from __future__ import annotations

import threading
import time

import requests


OPENALEX_BASE = "https://api.openalex.org/works"
TIMEOUT = 20
HEADERS = {
    "User-Agent": "MedScope-POC/0.1 (mailto:medscope@contentedmed.local)",
}

# Simple in-memory cache (DOI or PMID → citation count)
_cache: dict[str, int] = {}
_cache_lock = threading.Lock()

# Politeness throttle — one request at a time to stay well under rate limits
_MIN_INTERVAL = 0.1
_last_call_at = 0.0
_throttle_lock = threading.Lock()


def _throttle() -> None:
    global _last_call_at
    with _throttle_lock:
        wait = _MIN_INTERVAL - (time.time() - _last_call_at)
        if wait > 0:
            time.sleep(wait)
        _last_call_at = time.time()


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════════════════

def get_citations(doi: str | None = None, pmid: str | None = None) -> int | None:
    """
    Return citation count for a paper. Looks up by DOI first, PMID fallback.
    Returns None if not found or on any API error.
    """
    key = doi or (f"pmid:{pmid}" if pmid else None)
    if not key:
        return None

    with _cache_lock:
        if key in _cache:
            return _cache[key]

    count = _fetch(doi=doi, pmid=pmid)

    with _cache_lock:
        _cache[key] = count if count is not None else -1

    return count


def get_citations_bulk(papers: list[dict]) -> None:
    """
    Populate citation counts in-place for a list of Paper-dict-like inputs.
    Each item must have `doi` and/or `pmid` attributes.
    Writes result to each paper's `.citations` attribute.
    """
    for p in papers:
        doi = getattr(p, "doi", None) or (p.get("doi") if isinstance(p, dict) else None)
        pmid = getattr(p, "pmid", None) or (p.get("pmid") if isinstance(p, dict) else None)
        count = get_citations(doi=doi, pmid=pmid)
        if hasattr(p, "citations"):
            p.citations = count
        elif isinstance(p, dict):
            p["citations"] = count


# ════════════════════════════════════════════════════════════════════════════
#  INTERNALS
# ════════════════════════════════════════════════════════════════════════════

def _fetch(doi: str | None, pmid: str | None) -> int | None:
    """Query OpenAlex for a work and return cited_by_count, or None on failure."""
    url = None
    if doi:
        url = f"{OPENALEX_BASE}/doi:{doi}"
    elif pmid:
        url = f"{OPENALEX_BASE}/pmid:{pmid}"
    if not url:
        return None

    try:
        _throttle()
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return int(data.get("cited_by_count", 0))
    except Exception:
        return None
