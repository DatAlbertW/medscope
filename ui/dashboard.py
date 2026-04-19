"""
Dashboard view — the landing page for a loaded MoleculeReport.

Layout:
    Header:      molecule name + drug class + indication + hit counts
    Stats row:   4 counters (one per category)
    Charts row:  Publication timeline | Trial phases donut
    Map row:     RWE world map (full width)
    Lower:       Top papers list | Top journals
    Chatbot:     Collapsible panel with predefined question selector
"""
from __future__ import annotations

import streamlit as st

from config.categories import CATEGORIES
from core.models import MoleculeReport
from ui import charts, chatbot
from ui.styles import section_label, rule, rule_thin


def render(report: MoleculeReport) -> None:
    """Render the full dashboard for a loaded report."""
    _render_header(report)
    _render_stats_row(report)
    rule()
    _render_charts_row(report)
    rule()
    _render_map_row(report)
    rule()
    _render_bottom_row(report)
    rule()
    chatbot.render(report)


# ════════════════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════════════════

def _render_header(report: MoleculeReport) -> None:
    sp = report.search_params

    st.markdown(f"# {report.molecule}")
    st.markdown(
        f'<div style="margin-top:-0.7rem;margin-bottom:1rem;'
        f'color:var(--ink-soft);font-size:1.05rem;">'
        f'{report.drug_class}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:0.9rem;color:var(--ink-faint);margin-bottom:0.5rem;">'
        f'<em>{report.indication_hint}</em>'
        f'</div>',
        unsafe_allow_html=True,
    )

    meta_parts = []
    if sp.get("year_from") and sp.get("year_to"):
        meta_parts.append(f'{sp["year_from"]}–{sp["year_to"]}')
    meta_parts.append(f'{report.total_pubmed_hits:,} PubMed hits')
    meta_parts.append(f'{report.total_classified} classified')
    meta_parts.append(f'ran in {report.elapsed_seconds:.1f}s')

    st.markdown(
        f'<div style="font-size:0.78rem;color:var(--ink-faint);'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-top:0.5rem;">'
        f' · '.join(meta_parts)
        + '</div>',
        unsafe_allow_html=True,
    )

# DEBUG: show pipeline warnings
    if report.pipeline_warnings:
        with st.expander("Debug info (pipeline warnings)"):
            for w in report.pipeline_warnings:
                st.caption(w)

# ════════════════════════════════════════════════════════════════════════════
#  STATS ROW — one card per category
# ════════════════════════════════════════════════════════════════════════════

def _render_stats_row(report: MoleculeReport) -> None:
    st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, cat_id in zip(cols, CATEGORIES):
        count = report.counts.get(cat_id, 0)
        label = CATEGORIES[cat_id]["label"]
        col.markdown(
            f'<div class="stat-card">'
            f'<div class="value">{count}</div>'
            f'<div class="label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════════════════
#  CHARTS ROW — timeline + trial phases
# ════════════════════════════════════════════════════════════════════════════

def _render_charts_row(report: MoleculeReport) -> None:
    left, right = st.columns([2, 1])
    with left:
        fig = charts.publication_timeline(report.aggregates.get("yearly_counts", {}))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = charts.trial_phase_donut(report.aggregates.get("trial_phases", {}))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ════════════════════════════════════════════════════════════════════════════
#  MAP ROW — full-width RWE world map
# ════════════════════════════════════════════════════════════════════════════

def _render_map_row(report: MoleculeReport) -> None:
    fig = charts.rwe_world_map(report.aggregates.get("geography", []))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ════════════════════════════════════════════════════════════════════════════
#  BOTTOM ROW — top papers + top journals
# ════════════════════════════════════════════════════════════════════════════

def _render_bottom_row(report: MoleculeReport) -> None:
    left, right = st.columns([3, 2])

    # ── Top papers ─────────────────────────────────────────────────────────
    with left:
        section_label("Top-scoring papers")
        top = report.aggregates.get("top_papers", [])
        if not top:
            st.markdown(
                '<div style="color:var(--ink-faint);padding:1rem 0;">'
                'No papers yet. Run a search to populate.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for p in top:
                cat_label = CATEGORIES.get(p.get("category") or "", {}).get("label", "—")
                st.markdown(
                    f'<div class="paper-row">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:flex-start;gap:1rem;">'
                    f'<div style="flex:1;">'
                    f'<div class="title">{p["title"]}</div>'
                    f'<div class="meta">'
                    f'<span class="pill">{cat_label}</span>&nbsp;&nbsp;'
                    f'{p["journal"]} · {p["year"] or "—"} · '
                    f'<a href="{p["url"]}" target="_blank">PubMed</a>'
                    f'</div>'
                    f'</div>'
                    f'<div class="score">{p["score"]:.0f}</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Top journals ───────────────────────────────────────────────────────
    with right:
        section_label("Top journals")
        journals = report.aggregates.get("top_journals", [])
        if not journals:
            st.markdown(
                '<div style="color:var(--ink-faint);padding:1rem 0;">No data.</div>',
                unsafe_allow_html=True,
            )
        else:
            for j in journals[:8]:
                sjr_txt = f"SJR {j['avg_sjr']:.2f}" if j.get("avg_sjr") else "SJR —"
                st.markdown(
                    f'<div class="paper-row">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:center;">'
                    f'<div style="flex:1;">'
                    f'<div style="font-weight:500;">{j["journal"]}</div>'
                    f'<div class="meta">{sjr_txt}</div>'
                    f'</div>'
                    f'<div class="score" style="font-size:1.1rem;">'
                    f'{j["paper_count"]}'
                    f'</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
