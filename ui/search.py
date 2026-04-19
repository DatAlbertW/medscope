"""
Search panel: molecule input, date range, preview count, fetch trigger.

Renders in the sidebar or top region. Writes results to st.session_state:
    - st.session_state.preview: dict from pipelines.preview_search()
    - st.session_state.report:  MoleculeReport from pipelines.run_full_pipeline()
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from config import filters
from config.molecules import get_all_generics
from core import pipelines
from core.llm_client import get_client
from ui.styles import section_label


# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR SEARCH PANEL
# ════════════════════════════════════════════════════════════════════════════

def render_sidebar_search() -> None:
    """Render the full search workflow in the sidebar."""
    st.sidebar.markdown("## MedScope")
    st.sidebar.markdown(
        '<div class="section-label" style="margin-bottom:1rem">'
        'Literature Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Groq key ─────────────────────────────────────────────────────────
    section_label("API key")
    groq_key = st.sidebar.text_input(
        "Groq API key",
        type="password",
        placeholder="gsk_...",
        help="Free key at console.groq.com",
        key="groq_key_input",
        label_visibility="collapsed",
    )

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Molecule input ───────────────────────────────────────────────────
    section_label("Molecule")
    molecule_options = ["— type to search —"] + sorted(get_all_generics())
    picked = st.sidebar.selectbox(
        "Pick from list",
        molecule_options,
        index=0,
        key="molecule_picker",
        label_visibility="collapsed",
    )
    free_text = st.sidebar.text_input(
        "Or type (brand, generic, or synonym)",
        placeholder="e.g. Herceptin, Keytruda, Ozempic",
        key="molecule_text",
        label_visibility="collapsed",
    )

    # Decide which input to use
    user_input = free_text.strip() if free_text.strip() else (
        picked if picked != "— type to search —" else ""
    )

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Date range ───────────────────────────────────────────────────────
    current_year = datetime.now().year
    default_from = current_year - filters.DEFAULT_LOOKBACK_YEARS

    section_label("Date range")
    col1, col2 = st.sidebar.columns(2)
    year_from = col1.number_input(
        "From", min_value=filters.MIN_SEARCH_YEAR, max_value=current_year,
        value=default_from, step=1, key="year_from", label_visibility="collapsed",
    )
    year_to = col2.number_input(
        "To", min_value=filters.MIN_SEARCH_YEAR, max_value=current_year,
        value=current_year, step=1, key="year_to", label_visibility="collapsed",
    )

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Preview button ───────────────────────────────────────────────────
    if st.sidebar.button("Preview search", key="btn_preview", use_container_width=True):
        if not user_input:
            st.sidebar.warning("Enter or pick a molecule first.")
        else:
            with st.spinner("Checking PubMed..."):
                preview = pipelines.preview_search(user_input, int(year_from), int(year_to))
            st.session_state.preview = preview
            st.session_state.report = None   # invalidate any prior report

    # ── Show preview result ──────────────────────────────────────────────
    preview = st.session_state.get("preview")
    if preview:
        _render_preview_result(preview)

        if preview.get("resolved") and preview.get("hit_count", 0) > 0:
            fetch_msg = f"Run full analysis on {preview['will_fetch']} papers"
            if st.sidebar.button(fetch_msg, key="btn_fetch", use_container_width=True):
                if not groq_key:
                    st.sidebar.error("Groq API key required for analysis.")
                else:
                    _run_pipeline(groq_key, preview, int(year_from), int(year_to))


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _render_preview_result(preview: dict) -> None:
    """Show the outcome of a preview call in the sidebar."""
    if not preview.get("resolved"):
        st.sidebar.error(preview.get("message", "Could not resolve molecule."))
        return

    st.sidebar.markdown(
        f'<div class="section-label">Resolved</div>'
        f'<div style="font-family:Fraunces,serif;font-size:1.3rem;line-height:1.2;'
        f'margin-bottom:2px;">{preview["generic"]}</div>'
        f'<div style="font-size:0.78rem;color:var(--ink-faint);margin-bottom:12px;">'
        f'{preview["match_type"]} match on "{preview["matched_term"]}" '
        f'({preview["match_confidence"]:.0f}%)'
        f'</div>',
        unsafe_allow_html=True,
    )

    hits = preview.get("hit_count", 0)
    willf = preview.get("will_fetch", 0)
    st.sidebar.markdown(
        f'<div class="section-label">PubMed hits</div>'
        f'<div style="font-family:Fraunces,serif;font-size:2.1rem;line-height:1;'
        f'margin-bottom:4px;">{hits:,}</div>'
        f'<div style="font-size:0.78rem;color:var(--ink-faint);margin-bottom:12px;">'
        f'will fetch {willf} for analysis'
        f'</div>',
        unsafe_allow_html=True,
    )


def _run_pipeline(groq_key: str, preview: dict, year_from: int, year_to: int) -> None:
    """Run the full pipeline with live progress feedback."""
    progress = st.sidebar.progress(0, text="Starting...")
    status = st.sidebar.empty()

    def cb(stage: str, done: int, total: int):
        pct = int((done / total) * 100) if total else 0
        progress.progress(pct / 100, text=f"{stage} — {done}/{total}")
        status.caption(f"{stage}")

    try:
        client = get_client(groq_key)
        report = pipelines.run_full_pipeline(
            client=client,
            user_input=preview["generic"],
            year_from=year_from,
            year_to=year_to,
            progress_cb=cb,
        )
        st.session_state.report = report
        progress.empty()
        status.empty()
        st.rerun()
    except Exception as e:
        progress.empty()
        status.empty()
        st.sidebar.error(f"Pipeline failed: {e}")
