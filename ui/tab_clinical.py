"""Clinically Relevant Articles tab."""
from __future__ import annotations

import streamlit as st

from core.models import MoleculeReport
from ui.tab_shared import render_papers_table


def render(report: MoleculeReport) -> None:
    st.markdown("## Clinically Relevant Articles")
    st.markdown(
        '<div style="color:var(--ink-soft);font-size:0.95rem;margin-bottom:1.5rem;">'
        'Papers discussing this molecule in a clinical context: human patient use, '
        'guidelines, mechanism in humans, and positioning within standard of care. '
        'Animal-only and in-vitro-only studies are filtered out automatically.'
        '</div>',
        unsafe_allow_html=True,
    )

    papers = report.papers.get("clinically_relevant", [])
    render_papers_table(papers, "Clinically Relevant")
