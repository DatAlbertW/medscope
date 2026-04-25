"""
Search panel: molecule input, date range, preview count, fetch trigger.

Renders in the sidebar. Writes results to st.session_state:
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


# Section label helper that renders inside the sidebar
def _sidebar_label(text: str) -> None:
    st.sidebar.markdown(
        f'<div class="section-label">{text}</div>',
        unsafe_allow_html=True,
    )


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

    # ── Anthropic key ────────────────────────────────────────────────────
    # Pre-fill from Streamlit Cloud secrets if available
    default_key = ""
    try:
        default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        default_key = ""

    _sidebar_label("API key")
    api_key = st.sidebar.text_input(
        "Anthropic API key",
        value=default_key,
        type="password",
        placeholder="sk-ant-...",
        help="Get a key at console.anthropic.com",
        key="api_key_input",
        label_visibility="collapsed",
    )

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Molecule input ───────────────────────────────────────────────────
    _sidebar_label("Molecule")
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

    user_input = free_text.strip() if free_text.strip() else (
        picked if picked != "— type to search —" else ""
    )

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Date range (month + year) ────────────────────────────────────────
    current = datetime.now()
    default_from_year = current.year - filters.DEFAULT_LOOKBACK_YEARS

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    year_range = list(range(current.year, filters.MIN_SEARCH_YEAR - 1, -1))

    _sidebar_label("From")
    col1, col2 = st.sidebar.columns([1, 1])
    month_from = col1.selectbox(
        "Month from", MONTHS, index=0,
        key="month_from", label_visibility="collapsed",
    )
    year_from = col2.selectbox(
        "Year from", year_range,
        index=year_range.index(default_from_year),
        key="year_from", label_visibility="collapsed",
    )

    _sidebar_label("To")
    col3, col4 = st.sidebar.columns([1, 1])
    month_to = col3.selectbox(
        "Month to", MONTHS, index=current.month - 1,
        key="month_to", label_visibility="collapsed",
    )
    year_to = col4.selectbox(
        "Year to", year_range, index=0,
        key="year_to", label_visibility="collapsed",
    )

    # Encode as YYYY/MM for PubMed's PDAT field
    month_from_num = MONTHS.index(month_from) + 1
    month_to_num = MONTHS.index(month_to) + 1
    date_from = f"{year_from}/{month_from_num:02d}"
    date_to = f"{year_to}/{month_to_num:02d}"

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Preview button ───────────────────────────────────────────────────
    if st.sidebar.button("Preview search", key="btn_preview", use_container_width=True):
        if not user_input:
            st.sidebar.warning("Enter or pick a molecule first.")
        else:
            with st.spinner("Checking PubMed..."):
                preview = pipelines.preview_search(user_input, date_from, date_to)
            st.session_state.preview = preview
            st.session_state.report = None

    preview = st.session_state.get("preview")
    if preview:
        _render_preview_result(preview)

        if preview.get("resolved") and preview.get("hit_count", 0) > 0:
            fetch_msg = f"Run full analysis on {preview['will_fetch']} papers"
            if st.sidebar.button(fetch_msg, key="btn_fetch", use_container_width=True):
                if not api_key:
                    st.sidebar.error("Anthropic API key required for analysis.")
                else:
                    _run_pipeline(api_key, preview, date_from, date_to)


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _render_preview_result(preview: dict) -> None:
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


def _run_pipeline(api_key: str, preview: dict, date_from, date_to) -> None:
    progress = st.sidebar.progress(0, text="Starting...")
    status = st.sidebar.empty()

    def cb(stage: str, done: int, total: int):
        pct = int((done / total) * 100) if total else 0
        progress.progress(pct / 100, text=f"{stage} — {done}/{total}")
        status.caption(f"{stage}")

    try:
        client = get_client(api_key)
        report = pipelines.run_full_pipeline(
            client=client,
            user_input=preview["generic"],
            date_from=date_from,
            date_to=date_to,
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
