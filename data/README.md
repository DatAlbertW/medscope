# Data files

Static lookup files used at runtime.

Files:
- `sjr_scores.csv` — SCImago Journal Rank scores, used for journal prestige scoring. Format: `issn,journal_name,sjr,quartile`. Auto-downloaded on first run if missing.
- `molecule_synonyms.json` — Supplementary brand/generic/synonym mappings. Auto-generated from `config/molecules.py` on first run.

Do not edit these by hand. They are rebuilt automatically from the config files and external sources.
