"""
PubMed E-utilities client.

Uses NCBI's public E-utilities (free, no key required, but higher rate
limits with a key). Rate limit without key: 3 requests/second.

Endpoints used:
    - esearch.fcgi: find PMIDs matching a query
    - esummary.fcgi: get lightweight metadata
    - efetch.fcgi:   get full MEDLINE records (including abstracts)

Reference: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Iterable

import requests

from core.models import Paper
from config import filters


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT = 30
USER_AGENT = "MedScope-POC/0.1 (research; contact: medscope@contentedmed.local)"

# NCBI requests no more than 3 req/sec without API key
_MIN_INTERVAL = 0.34
_last_call_at = 0.0


def _throttle() -> None:
    """Simple client-side rate limiter."""
    global _last_call_at
    now = time.time()
    wait = _MIN_INTERVAL - (now - _last_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.time()


def _get(endpoint: str, params: dict) -> requests.Response:
    _throttle()
    url = f"{EUTILS_BASE}/{endpoint}"
    return requests.get(
        url,
        params=params,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )


# ════════════════════════════════════════════════════════════════════════════
#  QUERY BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_query(
    molecule: str,
    date_from: str | int | None = None,
    date_to: str | int | None = None,
    language: list[str] | None = None,
    mesh_terms: list[str] | None = None,
) -> str:
    """
    Build a PubMed query string using field tags.
    Always searches by the canonical generic name.

    `date_from` / `date_to` accept either a year int (e.g. 2024) or a
    'YYYY/MM' string (e.g. '2024/03').

    `mesh_terms` (optional): MeSH terms to add as additional filters,
    e.g. ['Breast Neoplasms', 'Carcinoma, Non-Small-Cell Lung'].
    Multiple MeSH terms are joined with OR (any match is sufficient).

    Animal-only papers are excluded via a NOT filter at the end.
    """
    parts = [f'"{molecule}"[Title/Abstract]']

    # MeSH term filter (therapeutic area)
    if mesh_terms:
        mesh_clauses = [f'"{m}"[MeSH Terms]' for m in mesh_terms if m]
        if mesh_clauses:
            joined = " OR ".join(mesh_clauses)
            parts.append(f"({joined})")

    # Language filter
    if language:
        lang_clause = " OR ".join(f'"{l}"[Language]' for l in language)
        parts.append(f"({lang_clause})")
    elif filters.LANGUAGE_FILTER:
        lang_clause = " OR ".join(f'"{l}"[Language]' for l in filters.LANGUAGE_FILTER)
        parts.append(f"({lang_clause})")

    # Date range — accept either year ints or 'YYYY/MM' strings
    def _fmt(d, default):
        if d is None:
            return default
        s = str(d)
        return s if "/" in s else f"{s}/01"

    if date_from or date_to:
        df = _fmt(date_from, "2000/01")
        dt = _fmt(date_to, "3000/12")
        parts.append(f'("{df}"[PDAT] : "{dt}"[PDAT])')

    animal_filter = '("animals"[MeSH Terms] NOT "humans"[MeSH Terms])'
    base = " AND ".join(parts)
    return f"{base} NOT {animal_filter}"


# ════════════════════════════════════════════════════════════════════════════
#  PREVIEW COUNT (cheap call for the "347 papers match" preview)
# ════════════════════════════════════════════════════════════════════════════

def count_matches(query: str) -> int:
    """Return how many papers a query matches without fetching them."""
    resp = _get("esearch.fcgi", {
        "db": "pubmed",
        "term": query,
        "rettype": "count",
        "retmode": "json",
    })
    if resp.status_code != 200:
        return 0
    data = resp.json()
    return int(data.get("esearchresult", {}).get("count", 0))


# ════════════════════════════════════════════════════════════════════════════
#  FIND PMIDS
# ════════════════════════════════════════════════════════════════════════════

def search_pmids(query: str, retmax: int = 150) -> list[str]:
    """Return up to `retmax` PMIDs matching the query, sorted by relevance."""
    resp = _get("esearch.fcgi", {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance",
    })
    if resp.status_code != 200:
        return []
    return resp.json().get("esearchresult", {}).get("idlist", [])


# ════════════════════════════════════════════════════════════════════════════
#  FETCH FULL RECORDS
# ════════════════════════════════════════════════════════════════════════════

def fetch_papers(pmids: Iterable[str]) -> list[Paper]:
    """
    Fetch full paper records (title, abstract, journal, authors, affiliations)
    for a list of PMIDs. Returns Paper objects with classification pending.
    """
    pmid_list = list(pmids)
    if not pmid_list:
        return []

    # EFetch in batches (NCBI recommends up to 200 per call for efetch)
    papers: list[Paper] = []
    BATCH = 100
    for i in range(0, len(pmid_list), BATCH):
        chunk = pmid_list[i:i + BATCH]
        resp = _get("efetch.fcgi", {
            "db": "pubmed",
            "id": ",".join(chunk),
            "rettype": "abstract",
            "retmode": "xml",
        })
        if resp.status_code != 200:
            continue
        papers.extend(_parse_pubmed_xml(resp.text))

    return papers


def _parse_pubmed_xml(xml_text: str) -> list[Paper]:
    """Parse a PubMed efetch XML response into Paper objects."""
    papers: list[Paper] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return papers

    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""
        if not pmid:
            continue

        # Title
        title_el = article.find(".//Article/ArticleTitle")
        title = _text_or_empty(title_el)

        # Abstract (may have multiple sections)
        abstract_parts = []
        for ab in article.findall(".//Abstract/AbstractText"):
            label = ab.attrib.get("Label")
            txt = _text_or_empty(ab)
            if label:
                abstract_parts.append(f"{label}: {txt}")
            else:
                abstract_parts.append(txt)
        abstract = " ".join(p for p in abstract_parts if p)

        # Journal
        journal_el = article.find(".//Journal/Title")
        journal = _text_or_empty(journal_el)

        # Publication date
        pub_year = _parse_year(article)
        pub_date = _parse_pub_date(article)

        # Authors
        authors = []
        for author in article.findall(".//Author"):
            last = _text_or_empty(author.find("LastName"))
            initials = _text_or_empty(author.find("Initials"))
            if last:
                authors.append(f"{last} {initials}".strip())

        # Affiliations
        affiliations = []
        for aff in article.findall(".//AffiliationInfo/Affiliation"):
            aff_text = _text_or_empty(aff)
            if aff_text and aff_text not in affiliations:
                affiliations.append(aff_text)

        # DOI
        doi = None
        for eid in article.findall(".//ArticleId"):
            if eid.attrib.get("IdType") == "doi":
                doi = _text_or_empty(eid)
                break

        papers.append(Paper(
            pmid=pmid,
            title=title,
            abstract=abstract,
            journal=journal,
            pub_date=pub_date,
            pub_year=pub_year,
            authors=authors[:10],              # cap to prevent bloat
            affiliations=affiliations[:5],
            doi=doi,
            pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        ))

    return papers


# ── helpers ─────────────────────────────────────────────────────────────────

def _text_or_empty(el: ET.Element | None) -> str:
    if el is None:
        return ""
    # Collapse inline tags (e.g. <i>, <sub>) into plain text
    return "".join(el.itertext()).strip()


def _parse_year(article: ET.Element) -> int | None:
    for path in (".//Journal/JournalIssue/PubDate/Year",
                 ".//Article/ArticleDate/Year",
                 ".//PubMedPubDate/Year"):
        el = article.find(path)
        if el is not None and el.text and el.text.strip().isdigit():
            return int(el.text)
    # Last resort: parse MedlineDate like "2024 Jan-Feb"
    md = article.find(".//Journal/JournalIssue/PubDate/MedlineDate")
    if md is not None and md.text:
        for token in md.text.split():
            if token.isdigit() and 1900 < int(token) < 2100:
                return int(token)
    return None


def _parse_pub_date(article: ET.Element) -> str:
    year = _parse_year(article)
    if year is None:
        return ""
    month_el = article.find(".//Journal/JournalIssue/PubDate/Month")
    month = _text_or_empty(month_el)
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    mm = month_map.get(month.lower()[:3], "")
    return f"{year}-{mm}-01" if mm else str(year)
