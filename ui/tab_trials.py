"""Trial Results tab."""
from __future__ import annotations

import streamlit as st

from core.models import MoleculeReport, Paper
from ui.tab_shared import render_papers_table


def render(report: MoleculeReport) -> None:
    st.markdown("## Trial Results")
    st.markdown(
        '<div style="color:var(--ink-soft);font-size:0.95rem;margin-bottom:1.5rem;">'
        'Papers reporting outcomes from interventional clinical trials '
        '(Phase 1–4) with primary or secondary endpoint data on this molecule.'
        '</div>',
        unsafe_allow_html=True,
    )

    papers = report.papers.get("trial_results", [])
    render_papers_table(
        papers,
        "Trial Results",
        extra_columns=["Phase", "NCT", "Primary endpoint", "N"],
        extra_getter=_trial_extras,
    )


def _trial_extras(p: Paper) -> dict:
    meta = p.trial_metadata or {}
    return {
        "Phase":             meta.get("phase") or "—",
        "NCT":               meta.get("nct_id") or "—",
        "Primary endpoint":  meta.get("primary_endpoint") or "—",
        "N":                 meta.get("n_enrolled") or "—",
    }
