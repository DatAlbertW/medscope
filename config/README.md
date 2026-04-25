# Config

Everything in this folder is **meant to be edited**. The files here control how MedScope behaves without touching the engine code in `core/` or the UI in `ui/`. If you want to change which molecules are tracked, how papers are classified, what the LLM is told, or how scores are calculated, this is the right place.

A good rule: if your change is about *what* the app does (which drugs, which categories, which prompts, which thresholds), edit a file here. If it's about *how* the app does it (API calls, parsing logic, rendering), don't touch this folder, that lives elsewhere.

---

## File-by-file guide

### `molecules.py`
The list of tracked molecules. Each entry has a generic name (the canonical identifier that always gets sent to PubMed), a list of brand names, a list of synonyms or research codes, the drug class, and a short indication hint.

When a user types "Herceptin" or makes a typo like "trastuzomab", the resolver matches against this file and converts the input to the generic name before searching. To add a new molecule, copy one of the existing entries and edit it. To rename or correct an entry, edit it directly.

### `categories.py`
The four classification categories that David asked for: clinically relevant articles, safety & efficacy, trial results, and real-world evidence. Each category has a description (what the LLM uses to decide if a paper belongs there), include keywords, and exclude keywords.

This file also holds `GLOBAL_EXCLUSIONS` which are markers that drop a paper entirely before classification, mostly for animal-only or in-vitro-only studies. If you find the classifier is letting through papers it shouldn't, tighten these. If too many real papers are being excluded, loosen them.

### `prompts.py`
Every LLM prompt lives in this file. There are four: one for classifying each paper into a category, one for extracting geographic origin (used by the RWE tab), one for extracting trial metadata like phase and NCT number, and one for extracting safety signals like top adverse events.

This is where to go if the AI is misbehaving — wrong classifications, missing data, hallucinated facts. Adjust the prompt wording, add examples, tighten the JSON schema. The system messages at the top of the file enforce that the LLM only returns JSON.

### `scoring.py`
The composite paper score, currently 55% journal prestige (SJR) plus 45% citation count, with a relevance weight reserved for future use. The score is what ranks papers in each tab.

If you want to weight citations more heavily, change the `WEIGHTS` dict. If you want to enable LLM-based relevance scoring, raise its weight above zero (the engine will then ask the LLM for relevance per paper). The anchor lists below convert raw SJR values and citation counts into a normalised 0-100 score, with a diminishing-returns curve.

### `filters.py`
The numeric thresholds and limits that control search behavior. The most important ones:

- `MAX_PAPERS_PER_SEARCH`: how many papers PubMed returns per search. Lower for faster demos, higher for thorough analysis.
- `MAX_PAPERS_PER_CATEGORY`: cap per category after classification.
- `DEFAULT_LOOKBACK_YEARS`: how far back the date picker defaults to.
- `LANGUAGE_FILTER`: PubMed language filter, currently English only.
- `RWE_DRILLDOWN_COUNTRIES`: countries shown on the RWE world map with state-level drill-down.

Tune these for performance vs. completeness. If a demo is taking too long, lower `MAX_PAPERS_PER_SEARCH`.

### `mock_market_data.py`
Illustrative market data for the Market Intelligence tab — marketing company, estimated annual sales, year-on-year growth, HCP specialty mix, key competitors. The flag `IS_ILLUSTRATIVE = True` causes the UI to show a "mock data" banner.

In production, this whole file would be replaced by a wiring to IQVIA, Evaluate Pharma, or another licensed source. For the POC, edit values here to keep them aligned with the latest publicly known sales figures.

### `__init__.py`
Marks the folder as a Python package. Don't edit this.

---

## How a change here flows through the app

A change to `molecules.py` shows up immediately in the molecule picker. A change to `categories.py` or `prompts.py` affects the next search you run — older results stay as they were until you re-fetch. A change to `scoring.py` only affects newly scored papers. A change to `filters.py` takes effect on the next search.

If you change something and the app doesn't reflect it, the cause is usually that Streamlit Cloud hasn't redeployed yet (wait 30 seconds after committing) or that the change is in a code path that only runs during a fresh search.
