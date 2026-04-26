"""
Shared paper-table renderer used by every category tab.

Renders a sortable table with:
    - Single composite Score column with hover tooltip showing the breakdown
    - Filter by minimum score
    - Filter by study type (multi-select)
    - CSV download
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import filters
from core.models import Paper
from ui.styles import section_label


def _format_score_breakdown(p: Paper) -> str:
    """Build the tooltip-style breakdown string for a paper."""
    bd = p.score_breakdown or {}
    rel = bd.get("relevance")
    sjr_norm = bd.get("sjr_norm")
    sjr_raw = bd.get("sjr_raw")
    cit_norm = bd.get("citations_norm")
    cit_raw = bd.get("citations_raw")
    composite = bd.get("composite", p.score)

    parts = []
    if rel is not None:
        parts.append(f"Relevance {rel}")
    if sjr_norm is not None:
        sjr_label = f"SJR {sjr_norm}"
        if sjr_raw is not None:
            sjr_label += f" (raw {sjr_raw})"
        parts.append(sjr_label)
    if cit_norm is not None:
        cit_label = f"Citations {cit_norm}"
        if cit_raw is not None:
            cit_label += f" (raw {cit_raw})"
        parts.append(cit_label)

    return " · ".join(parts) + f" → composite {composite}"


def render_papers_table(
    papers: list[Paper],
    category_label: str,
    extra_columns: list[str] | None = None,
    extra_getter=None,
) -> None:
    """Render a paper table with score, study-type filter, and tooltip."""
    if not papers:
        st.markdown(
            '<div style="color:var(--ink-faint);padding:1.5rem 0;font-style:italic;">'
            'No papers in this category for the current search.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Filters row ─────────────────────────────────────────────────────────
    available_types = sorted({p.study_type or "Other" for p in papers})

    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        min_score = st.slider(
            "Minimum score",
            min_value=0, max_value=100,
            value=filters.MIN_DISPLAY_SCORE,
            step=5,
            key=f"min_score_{category_label}",
        )
    with fcol2:
        picked_types = st.multiselect(
            "Study type",
            options=available_types,
            default=available_types,
            key=f"study_types_{category_label}",
        )

    # ── Build DataFrame ─────────────────────────────────────────────────────
    rows = []
    for p in papers:
        if p.score < min_score:
            continue
        if (p.study_type or "Other") not in picked_types:
            continue
        row = {
            "Score":       round(p.score, 1),
            "Breakdown":   _format_score_breakdown(p),
            "Title":       p.title,
            "Journal":     p.journal,
            "Year":        p.pub_year,
            "Study type":  p.study_type,
            "Key finding": p.key_finding or "—",
            "PubMed":      p.pubmed_url,
        }
        if extra_columns and extra_getter:
            extras = extra_getter(p) or {}
            for col in extra_columns:
                row[col] = extras.get(col, "—")
        rows.append(row)

    if not rows:
        st.info("No papers match these filters. Loosen them to see more.")
        return

    df = pd.DataFrame(rows)
    standard = ["Title", "Journal", "Year", "Study type", "Key finding", "PubMed"]
    col_order = ["Score", "Breakdown"] + (extra_columns or []) + standard
    df = df[[c for c in col_order if c in df.columns]]

    section_label(f"{len(df)} {category_label} papers")

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Score": st.column_config.NumberColumn(
                "Score",
                format="%.1f",
                width="small",
                help="Composite of Relevance (40%), SJR (30%), and Citations (30%). "
                     "Hover the Breakdown column to see the components.",
            ),
            "Breakdown": st.column_config.TextColumn(
                "Breakdown",
                width="medium",
                help="Components that produced the composite score",
            ),
            "Title":  st.column_config.TextColumn("Title", width="large"),
            "Key finding": st.column_config.TextColumn("Key finding", width="medium"),
            "PubMed": st.column_config.LinkColumn("PubMed", display_text="open ↗"),
        },
        height=min(600, 60 + 36 * len(df)),
    )

    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"medscope_{category_label.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
