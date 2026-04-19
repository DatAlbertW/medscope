"""
Shared helpers used by the category tab views.

Keeps the table rendering logic in one place so clinical/safety/trials/RWE
views stay consistent and thin.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import filters
from core.models import Paper
from ui.styles import section_label


def render_papers_table(
    papers: list[Paper],
    category_label: str,
    extra_columns: list[str] | None = None,
    extra_getter=None,
) -> None:
    """
    Render a sortable, filterable table of papers.

    `extra_columns` are additional column names (e.g. "Phase", "Region").
    `extra_getter(paper)` must return a dict of extra_column → value for each paper.
    """
    if not papers:
        st.markdown(
            '<div style="color:var(--ink-faint);padding:1.5rem 0;font-style:italic;">'
            'No papers in this category for the current search.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Filter: minimum score slider ────────────────────────────────────────
    col_a, col_b = st.columns([1, 3])
    min_score = col_a.slider(
        "Minimum score",
        min_value=0, max_value=100,
        value=filters.MIN_DISPLAY_SCORE,
        step=5,
        key=f"min_score_{category_label}",
        label_visibility="visible",
    )

    # ── Build DataFrame ─────────────────────────────────────────────────────
    rows = []
    for p in papers:
        if p.score < min_score:
            continue
        row = {
            "Score":       round(p.score, 1),
            "Title":       p.title,
            "Journal":     p.journal,
            "Year":        p.pub_year,
            "Study type":  p.study_type,
            "Citations":   p.citations if p.citations is not None else "—",
            "SJR":         round(p.sjr, 2) if p.sjr is not None else "—",
            "PubMed":      p.pubmed_url,
            "Key finding": p.key_finding or "—",
        }
        if extra_columns and extra_getter:
            extras = extra_getter(p) or {}
            for col in extra_columns:
                row[col] = extras.get(col, "—")
        rows.append(row)

    if not rows:
        st.info(f"No papers above score {min_score}. Lower the threshold to see more.")
        return

    df = pd.DataFrame(rows)

    # Column ordering: Score first, then extras, then standard columns
    standard = ["Title", "Journal", "Year", "Study type", "Citations", "SJR",
                "Key finding", "PubMed"]
    col_order = ["Score"] + (extra_columns or []) + standard
    df = df[[c for c in col_order if c in df.columns]]

    # ── Table header ────────────────────────────────────────────────────────
    section_label(f"{len(df)} {category_label} papers")

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "PubMed": st.column_config.LinkColumn("PubMed", display_text="open ↗"),
            "Title":  st.column_config.TextColumn("Title", width="large"),
            "Key finding": st.column_config.TextColumn("Key finding", width="medium"),
            "Score":  st.column_config.NumberColumn("Score", format="%.1f", width="small"),
        },
        height=min(600, 60 + 36 * len(df)),
    )

    # ── Download ────────────────────────────────────────────────────────────
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"medscope_{category_label.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
