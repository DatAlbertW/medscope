# MedScope

AI-powered literature and evidence intelligence for medical affairs and publication planning.

Built as a proof of concept for ContentEd Med.

## What it does

For any of the tracked molecules, MedScope searches PubMed, resolves brand names and synonyms, and classifies papers into four categories requested by medical affairs teams:

1. **Clinically Relevant Articles** — clinical context, animal/in-vitro data excluded
2. **Safety & Efficacy** — adverse events, tolerability, efficacy endpoints
3. **Trial Results** — RCT outcomes with reported results
4. **Real-World Evidence** — observational, registry, and real-world studies with geographic drill-down

Each category displays a ranked table of papers with a composite score based on journal prestige (SJR) and citation count.

## Tech stack

- Streamlit (UI)
- PubMed E-utilities (literature source, no API key required)
- Groq + LLaMA 3.3 (classification and extraction)
- RxNorm (brand/generic/synonym resolution)
- SCImago Journal Rank (journal prestige scoring)

## Structure

```
medscope/
├── app.py              # Streamlit entry point
├── config/             # Editable rules, molecules, prompts, scoring weights
├── core/               # Engine — PubMed, LLM, pipelines (do not modify)
├── ui/                 # Streamlit components (do not modify)
└── data/               # Static lookup files (journal rankings, synonyms)
```

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

A free Groq API key is required. Get one at https://console.groq.com.

## Deployment

Designed to deploy to Streamlit Community Cloud. Connect this repository and set `GROQ_API_KEY` in the app secrets.

## Status

Proof of concept, April 2026. Scope is limited to 10 reference molecules and English-language sources. Cached to a maximum of 50 papers per molecule per category to keep demo latency low.
