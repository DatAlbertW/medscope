"""
MedScope — Streamlit entry point.

Run with:
    streamlit run app.py

Flow:
    1. Sidebar: API key + molecule search + date range + preview + fetch
    2. Main area: dashboard (or empty state) + 5 tabs once report is loaded
"""
from __future__ import annotations

import streamlit as st

from ui import (
    search,
    styles,
    dashboard,
    tab_clinical,
    tab_safety,
    tab_trials,
    tab_rwe,
    tab_market,
)


# ════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG (must be first Streamlit call)
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MedScope",
    page_icon="◐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global styling
styles.inject_css()


# ════════════════════════════════════════════════════════════════════════════
#  SESSION STATE DEFAULTS
# ════════════════════════════════════════════════════════════════════════════
if "report" not in st.session_state:
    st.session_state.report = None
if "preview" not in st.session_state:
    st.session_state.preview = None


# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
search.render_sidebar_search()


# ════════════════════════════════════════════════════════════════════════════
#  MAIN AREA
# ════════════════════════════════════════════════════════════════════════════
report = st.session_state.get("report")

if report is None:
    # ── Empty state ────────────────────────────────────────────────────────
    st.markdown("# MedScope")
    st.markdown(
        '<div style="margin-top:-0.5rem;color:var(--ink-soft);font-size:1.15rem;'
        'margin-bottom:2.5rem;max-width:680px;line-height:1.5;">'
        'Literature and evidence intelligence for medical affairs and publication planning. '
        'Pick a molecule, set a date range, and run the pipeline.'
        '</div>',
        unsafe_allow_html=True,
    )

    styles.rule()

    col1, col2, col3 = st.columns(3)
    col1.markdown(
        '<div class="stat-card">'
        '<div class="label">Step 1</div>'
        '<div style="font-family:Fraunces,serif;font-size:1.4rem;line-height:1.3;'
        'margin-top:4px;color:var(--ink);">Enter your Anthropic key</div>'
        '<div style="color:var(--ink-faint);font-size:0.85rem;margin-top:6px;">'
        'Free at console.anthropic.com'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    col2.markdown(
        '<div class="stat-card">'
        '<div class="label">Step 2</div>'
        '<div style="font-family:Fraunces,serif;font-size:1.4rem;line-height:1.3;'
        'margin-top:4px;color:var(--ink);">Pick a molecule</div>'
        '<div style="color:var(--ink-faint);font-size:0.85rem;margin-top:6px;">'
        'Generic, brand, or synonym'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    col3.markdown(
        '<div class="stat-card">'
        '<div class="label">Step 3</div>'
        '<div style="font-family:Fraunces,serif;font-size:1.4rem;line-height:1.3;'
        'margin-top:4px;color:var(--ink);">Run the analysis</div>'
        '<div style="color:var(--ink-faint);font-size:0.85rem;margin-top:6px;">'
        'Preview first, then fetch'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    styles.rule()

    styles.section_label("How it works")
    st.markdown(
        '<div style="color:var(--ink-soft);font-size:0.95rem;line-height:1.7;max-width:740px;">'
        'MedScope searches PubMed for a molecule, classifies each paper into one of '
        'four categories (clinically relevant, safety & efficacy, trial results, '
        'real-world evidence), extracts structured metadata, scores each paper by '
        'journal prestige and citation count, and assembles a dashboard that a '
        'medical affairs team can act on. A built-in assistant answers '
        'questions about the loaded evidence using only the data on screen.'
        '</div>',
        unsafe_allow_html=True,
    )

else:
    # ── Loaded report: dashboard + tabs ────────────────────────────────────
    tab_labels = [
        "◐ Dashboard",
        "Clinically Relevant",
        "Safety & Efficacy",
        "Trial Results",
        "Real-World Evidence",
        "Market Intelligence",
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        dashboard.render(report)
    with tabs[1]:
        tab_clinical.render(report)
    with tabs[2]:
        tab_safety.render(report)
    with tabs[3]:
        tab_trials.render(report)
    with tabs[4]:
        tab_rwe.render(report)
    with tabs[5]:
        tab_market.render(report)


# ════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div style="margin-top:4rem;padding-top:1rem;border-top:1px solid var(--line);'
    'color:var(--ink-faint);font-size:0.75rem;text-align:center;letter-spacing:0.08em;'
    'text-transform:uppercase;">'
    'MedScope · Proof of Concept · April 2026'
    '</div>',
    unsafe_allow_html=True,
)
