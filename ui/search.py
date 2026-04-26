"""
Search panel: API status light, molecule input, therapeutic areas,
date range (month + year), preview count, fetch trigger.

Renders in the sidebar. Writes to st.session_state:
    - st.session_state.preview: dict from pipelines.preview_search()
    - st.session_state.report:  MoleculeReport from pipelines.run_full_pipeline()
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from config import filters
from config.molecules import get_all_generics
from config.therapeutic_areas import (
    THERAPEUTIC_AREAS,
    flatten_areas,
    get_areas_for_molecule,
    get_molecules_for_areas,
)
from core import pipelines
from core.llm_client import get_client


def _sidebar_label(text: str) -> None:
    st.sidebar.markdown(
        f'<div class="section-label">{text}</div>',
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def render_sidebar_search() -> str | None:
    """
    Render the full search workflow in the sidebar.
    Returns the resolved API key (from secrets or manual entry) so the
    caller can pass it to the pipeline.
    """
    st.sidebar.markdown("## MedScope")
    st.sidebar.markdown(
        '<div class="section-label" style="margin-bottom:1rem">'
        'Literature Intelligence'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── API status light + optional manual entry ─────────────────────────
    api_key = _render_api_status()

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Molecule + therapeutic area ──────────────────────────────────────
    user_input, picked_areas = _render_molecule_and_areas()

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Date range (month + year) ────────────────────────────────────────
    date_from, date_to = _render_date_range()

    st.sidebar.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)

    # ── Preview button ───────────────────────────────────────────────────
    if st.sidebar.button("Preview search", key="btn_preview", use_container_width=True):
        if not user_input:
            st.sidebar.warning("Pick a molecule first.")
        else:
            with st.spinner("Checking PubMed..."):
                preview = pipelines.preview_search(
                    user_input, date_from, date_to,
                    therapeutic_areas=picked_areas or None,
                )
            st.session_state.preview = preview
            st.session_state.report = None

    # ── Show preview result + Run button ─────────────────────────────────
    preview = st.session_state.get("preview")
    if preview:
        _render_preview_result(preview)

        if preview.get("resolved") and preview.get("hit_count", 0) > 0:
            fetch_msg = f"Run full analysis on {preview['will_fetch']} papers"
            if st.sidebar.button(fetch_msg, key="btn_fetch", use_container_width=True):
                if not api_key:
                    st.sidebar.error(
                        "No Anthropic API key. Add ANTHROPIC_API_KEY to "
                        "Streamlit secrets or expand the API status panel above."
                    )
                else:
                    _run_pipeline(api_key, preview, date_from, date_to, picked_areas)

    return api_key


# ════════════════════════════════════════════════════════════════════════════
#  API STATUS LIGHT
# ════════════════════════════════════════════════════════════════════════════

def _render_api_status() -> str:
    """
    Show a green/red dot for API key status. Click to expand a manual input
    field. Returns the active key (from secrets or manual entry).
    """
    # Check secrets first
    secrets_key = ""
    try:
        secrets_key = st.secrets.get("ANTHROPIC_API_KEY", "") or ""
    except Exception:
        secrets_key = ""

    manual_key = st.session_state.get("manual_api_key", "")
    active_key = secrets_key or manual_key
    has_key = bool(active_key)

    dot_color = "#2d6a4f" if has_key else "#8b2a2a"
    dot_label = "API key configured" if has_key else "No API key — click to set"

    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:6px 0;font-size:0.82rem;color:var(--ink-soft);">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:{dot_color};"></span>'
        f'<span>{dot_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Only show the manual input when there's no key configured
    if not has_key:
        with st.sidebar.expander("Enter API key manually", expanded=False):
            entered = st.text_input(
                "Anthropic API key",
                type="password",
                placeholder="sk-ant-...",
                help="Or set ANTHROPIC_API_KEY in Streamlit secrets",
                key="manual_api_key_input",
                label_visibility="collapsed",
            )
            if entered:
                st.session_state.manual_api_key = entered
                active_key = entered

    return active_key


# ════════════════════════════════════════════════════════════════════════════
#  MOLECULE + THERAPEUTIC AREA
# ════════════════════════════════════════════════════════════════════════════

def _render_molecule_and_areas() -> tuple[str, list[str]]:
    """
    Render the molecule and therapeutic-area pickers with adaptive narrowing
    based on a curated mapping. Returns (user_input, picked_area_labels).
    """
    # Read prior picks for adaptive narrowing
    prior_areas = st.session_state.get("ta_areas", [])

    # ── Molecule ──────────────────────────────────────────────────────────
    _sidebar_label("Molecule")
    all_generics = sorted(get_all_generics())
    if prior_areas:
        # Narrow to molecules that have evidence in any selected area
        narrow = get_molecules_for_areas(prior_areas)
        molecule_options_filtered = [m for m in all_generics if m in narrow]
        if not molecule_options_filtered:
            molecule_options_filtered = all_generics
        molecule_options = ["— type to search —"] + molecule_options_filtered
    else:
        molecule_options = ["— type to search —"] + all_generics

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

    # ── Therapeutic areas (multi-select, adaptive) ────────────────────────
    _sidebar_label("Therapeutic area (optional)")

    # Adaptive narrowing: if a molecule is picked, narrow to its areas
    all_areas = flatten_areas()
    if user_input:
        from core import drug_resolver
        r = drug_resolver.resolve(user_input)
        if r.resolved:
            relevant = get_areas_for_molecule(r.generic)
            if relevant:
                area_pool = relevant
            else:
                area_pool = all_areas
        else:
            area_pool = all_areas
    else:
        area_pool = all_areas

    # Group options visually with the chapter prefix
    options = [a["full_path"] for a in area_pool]

    picked_areas = st.sidebar.multiselect(
        "Therapeutic areas",
        options=options,
        default=[],
        key="ta_areas",
        label_visibility="collapsed",
        placeholder="Pick one or more (optional)",
    )

    return user_input, picked_areas


# ════════════════════════════════════════════════════════════════════════════
#  DATE RANGE
# ════════════════════════════════════════════════════════════════════════════

def _render_date_range() -> tuple[str, str]:
    """Render From/To month+year selects. Returns ('YYYY/MM', 'YYYY/MM')."""
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

    month_from_num = MONTHS.index(month_from) + 1
    month_to_num = MONTHS.index(month_to) + 1
    return f"{year_from}/{month_from_num:02d}", f"{year_to}/{month_to_num:02d}"


# ════════════════════════════════════════════════════════════════════════════
#  PREVIEW DISPLAY
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

    if preview.get("therapeutic_areas"):
        ta_html = "".join(
            f'<span class="pill accent" style="margin-right:4px;margin-bottom:4px;'
            f'display:inline-block;">{ta.split(" › ")[-1]}</span>'
            for ta in preview["therapeutic_areas"]
        )
        st.sidebar.markdown(
            f'<div class="section-label">Therapeutic areas</div>'
            f'<div style="margin-bottom:12px;">{ta_html}</div>',
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


# ════════════════════════════════════════════════════════════════════════════
#  RUN PIPELINE
# ════════════════════════════════════════════════════════════════════════════

def _run_pipeline(
    api_key: str,
    preview: dict,
    date_from: str,
    date_to: str,
    therapeutic_areas: list[str],
) -> None:
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
            therapeutic_areas=therapeutic_areas or None,
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
