"""Safety & Efficacy tab."""
from __future__ import annotations

import streamlit as st

from core.models import MoleculeReport, Paper
from ui.tab_shared import render_papers_table


def render(report: MoleculeReport) -> None:
    st.markdown("## Safety & Efficacy")
    st.markdown(
        '<div style="color:var(--ink-soft);font-size:0.95rem;margin-bottom:1.5rem;">'
        'Papers specifically reporting on safety profile, adverse events, '
        'tolerability, pharmacovigilance findings, or efficacy endpoints.'
        '</div>',
        unsafe_allow_html=True,
    )

    papers = report.papers.get("safety_efficacy", [])

    # ── Summary of top adverse events (from aggregates) ────────────────────
    top_aes = report.aggregates.get("top_adverse_events", [])
    if top_aes:
        st.markdown(
            '<div class="section-label">Most frequently mentioned adverse events</div>',
            unsafe_allow_html=True,
        )
        pills = "".join(
            f'<span class="pill" style="margin-right:6px;margin-bottom:6px;">'
            f'{ae.title()} <span style="color:var(--ink-faint);margin-left:6px;">'
            f'{count}</span></span>'
            for ae, count in top_aes
        )
        st.markdown(f'<div style="margin-bottom:1.5rem;">{pills}</div>', unsafe_allow_html=True)

    # ── Papers table ────────────────────────────────────────────────────────
    render_papers_table(
        papers,
        "Safety & Efficacy",
        extra_columns=["Serious AEs", "Discontinuation"],
        extra_getter=_safety_extras,
    )


def _safety_extras(p: Paper) -> dict:
    meta = p.safety_metadata or {}
    return {
        "Serious AEs":    "Yes" if meta.get("serious_aes_mentioned") else "—",
        "Discontinuation": meta.get("discontinuation_rate") or "—",
    }
