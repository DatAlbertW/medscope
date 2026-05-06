"""
Default filter values and hard limits for PubMed searches.

Tune these to change how much the app fetches and how it presents results.
"""

# ── Search limits ───────────────────────────────────────────────────────────

# Absolute maximum papers to fetch per molecule per category.
# Keeping this low preserves Groq tokens and keeps demo latency snappy.
MAX_PAPERS_PER_CATEGORY = 50

# Maximum total papers to classify per search before hitting the category cap.
# The pipeline fetches this many from PubMed, then classifies and distributes
# into the 4 categories, capping each at MAX_PAPERS_PER_CATEGORY.
MAX_PAPERS_PER_SEARCH = 30


# ── Default date range ──────────────────────────────────────────────────────

# On first load, the date range filter defaults to papers from the last N years.
DEFAULT_LOOKBACK_YEARS = 3

# Earliest allowed search year (PubMed contains data going back to ~1946)
MIN_SEARCH_YEAR = 2000


# ── Language filter ─────────────────────────────────────────────────────────

# PubMed language filter. English-only for POC.
LANGUAGE_FILTER = ["english"]


# ── Publication type allow-list ─────────────────────────────────────────────
# PubMed "Publication Type" filter. Empty list = no filter.
# Useful types: "Clinical Trial", "Randomized Controlled Trial", "Review",
# "Meta-Analysis", "Observational Study", "Case Reports".
PUBLICATION_TYPES_ALLOW: list[str] = []


# ── RWE region drill-down ───────────────────────────────────────────────────

# For the Real-World Evidence tab, these are the regions/countries highlighted
# on the world map with state-level drill-down available.
RWE_DRILLDOWN_COUNTRIES = {
    "ES": "Spain",          # Catalonia, Madrid, Andalusia, etc.
    "DE": "Germany",        # Bavaria, Baden-Württemberg, NRW, etc.
    "FR": "France",         # Île-de-France, Auvergne-Rhône-Alpes, etc.
    "IT": "Italy",          # Lombardy, Lazio, Veneto, etc.
    "GB": "United Kingdom",
    "US": "United States",  # 50 states
    "CH": "Switzerland",    # Zurich, Geneva, Basel-Stadt, etc.
    "NL": "Netherlands",
    "SE": "Sweden",
    "DK": "Denmark",
}


# ── Result display ──────────────────────────────────────────────────────────

# How many rows to show per table by default
TABLE_PAGE_SIZE = 25

# Minimum composite score to display. Set to 0 to show all.
MIN_DISPLAY_SCORE = 0
