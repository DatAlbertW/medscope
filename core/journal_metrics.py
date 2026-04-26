"""
Journal prestige lookup (SCImago Journal Rank).

SCImago publishes free annual CSV dumps of all journals with SJR score,
H-index, quartile, etc. This module:

    1. Looks for a cached SJR file in /data/sjr_scores.csv
    2. Downloads the latest SCImago dump on first run if missing
    3. Normalizes journal names to match PubMed's journal strings
    4. Returns SJR score for a given journal name (best-effort)

Since the free SCImago CSV is ~50 MB and updates yearly, we download
once and cache. Lookups are by normalised journal title.
"""
from __future__ import annotations

import csv
import os
import re
import threading

import requests
from rapidfuzz import fuzz, process


# Latest known SCImago CSV URL template (update year annually)
SCIMAGO_YEAR = 2024
SCIMAGO_CSV_URL = f"https://www.scimagojr.com/journalrank.php?out=xls&year={SCIMAGO_YEAR}"

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "scimagojr_2025.csv",
)


# In-memory cache: normalized_journal_name -> (sjr, quartile)
_cache: dict[str, tuple[float, str]] = {}
_cache_loaded = False
_cache_lock = threading.Lock()


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════════════════

def get_sjr(journal_name: str) -> tuple[float | None, str | None]:
    """
    Return (SJR score, quartile) for a journal name.
    Both values can be None if the journal is not found.
    """
    if not journal_name:
        return None, None

    _ensure_cache_loaded()
    if not _cache:
        return None, None

    key = _normalize(journal_name)

    # Exact normalised match first
    if key in _cache:
        return _cache[key]

    # Fuzzy fallback against cache keys
    candidates = list(_cache.keys())
    best = process.extractOne(key, candidates, scorer=fuzz.WRatio, score_cutoff=90)
    if best is not None:
        match_key, _, _ = best
        return _cache[match_key]

    return None, None


# ════════════════════════════════════════════════════════════════════════════
#  CACHE LOADING
# ════════════════════════════════════════════════════════════════════════════

def _ensure_cache_loaded() -> None:
    """Load cache from disk. The CSV is bundled with the repo at data/scimagojr_2025.csv."""
    global _cache_loaded
    with _cache_lock:
        if _cache_loaded:
            return
        _load_from_disk()
        _cache_loaded = True


def _download_scimago() -> None:
    """Download the SCImago CSV dump to DATA_PATH. Silently fails on error."""
    try:
        resp = requests.get(SCIMAGO_CSV_URL, timeout=60)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
            with open(DATA_PATH, "wb") as f:
                f.write(resp.content)
    except Exception:
        # Silent failure is acceptable — the app will just run without SJR scores
        pass


def _load_from_disk() -> None:
    """Parse the SCImago CSV into the in-memory cache."""
    if not os.path.exists(DATA_PATH):
        return

    # SCImago CSV uses semicolons as separators and comma as decimal mark
    try:
        with open(DATA_PATH, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                title = row.get("Title") or row.get("title") or ""
                sjr_raw = row.get("SJR") or row.get("sjr") or ""
                quartile = row.get("SJR Best Quartile") or row.get("Q") or ""
                if not title or not sjr_raw:
                    continue
                try:
                    sjr = float(sjr_raw.replace(",", "."))
                except ValueError:
                    continue
                _cache[_normalize(title)] = (sjr, quartile.strip() or "Unranked")
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  NORMALIZATION
# ════════════════════════════════════════════════════════════════════════════

def _normalize(name: str) -> str:
    """
    Normalize a journal name for matching:
        - lowercase
        - strip punctuation except letters/digits/spaces
        - collapse whitespace
        - drop common prefixes/suffixes like "The", "Journal of"
    """
    s = name.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Remove leading "the"
    if s.startswith("the "):
        s = s[4:]
    return s
  
