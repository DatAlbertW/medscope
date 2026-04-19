"""Real-World Evidence tab with geographic drill-down."""
from __future__ import annotations

from collections import Counter

import streamlit as st

from core.models import MoleculeReport, Paper
from ui.tab_shared import render_papers_table


def render(report: MoleculeReport) -> None:
    st.markdown("## Real-World Evidence")
    st.markdown(
        '<div style="color:var(--ink-soft);font-size:0.95rem;margin-bottom:1.5rem;">'
        'Observational studies, registry analyses, retrospective cohorts, '
        'post-marketing surveillance, and real-world clinical practice data. '
        'Each paper is enriched with country and regional origin.'
        '</div>',
        unsafe_allow_html=True,
    )

    papers = report.papers.get("real_world_evidence", [])

    # ── Country / region summary pills ─────────────────────────────────────
    country_counts = Counter()
    region_counts = Counter()
    for p in papers:
        g = p.geography or {}
        if g.get("country"):
            country_counts[g["country"]] += 1
        if g.get("region"):
            region_counts[g["region"]] += 1

    if country_counts:
        st.markdown('<div class="section-label">Countries represented</div>', unsafe_allow_html=True)
        pills = "".join(
            f'<span class="pill" style="margin-right:6px;margin-bottom:6px;">'
            f'{country} <span style="color:var(--ink-faint);margin-left:6px;">{n}</span>'
            f'</span>'
            for country, n in country_counts.most_common(12)
        )
        st.markdown(f'<div style="margin-bottom:1rem;">{pills}</div>', unsafe_allow_html=True)

    if region_counts:
        st.markdown('<div class="section-label">Regions / states represented</div>', unsafe_allow_html=True)
        pills = "".join(
            f'<span class="pill accent" style="margin-right:6px;margin-bottom:6px;">'
            f'{region} <span style="color:var(--ink-faint);margin-left:6px;">{n}</span>'
            f'</span>'
            for region, n in region_counts.most_common(15)
        )
        st.markdown(f'<div style="margin-bottom:1.5rem;">{pills}</div>', unsafe_allow_html=True)

    # ── Papers table with geography columns ────────────────────────────────
    render_papers_table(
        papers,
        "Real-World Evidence",
        extra_columns=["Country", "Region", "Cohort"],
        extra_getter=_rwe_extras,
    )


def _rwe_extras(p: Paper) -> dict:
    g = p.geography or {}
    return {
        "Country": g.get("country") or "—",
        "Region":  g.get("region") or "—",
        "Cohort":  g.get("cohort_size") if g.get("cohort_size") else "—",
    }
