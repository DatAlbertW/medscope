"""
Market Intelligence tab.

Shows marketing company, sales estimates, growth, HCP specialty mix,
and key competitors. All values are ILLUSTRATIVE mock data, clearly
flagged to avoid misleading the user.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.mock_market_data import IS_ILLUSTRATIVE
from core.models import MoleculeReport
from ui import charts
from ui.styles import section_label


def render(report: MoleculeReport) -> None:
    st.markdown("## Market Intelligence")

    mkt = report.market_context
    if not mkt:
        st.markdown(
            '<div style="color:var(--ink-faint);padding:1.5rem 0;">'
            'No market data available for this molecule.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    if IS_ILLUSTRATIVE:
        st.markdown(
            '<div class="mock-banner">'
            '⚠️ Illustrative mock data. A production deployment would wire this view '
            'to IQVIA, Evaluate Pharma, or equivalent licensed data sources.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Top metrics row ────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    c1.markdown(
        f'<div class="stat-card">'
        f'<div class="label">Marketing company</div>'
        f'<div style="font-family:Fraunces,serif;font-size:1.3rem;line-height:1.2;">'
        f'{mkt["marketing_company"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="stat-card accent">'
        f'<div class="value">${mkt["est_annual_sales_usd_m"]:,}M</div>'
        f'<div class="label">Est. annual sales</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    growth = mkt["growth_yoy_pct"]
    growth_color = "var(--good)" if growth >= 0 else "var(--bad)"
    growth_prefix = "+" if growth >= 0 else ""
    c3.markdown(
        f'<div class="stat-card">'
        f'<div class="value" style="color:{growth_color};">{growth_prefix}{growth}%</div>'
        f'<div class="label">YoY growth</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    # ── HCP targeting mix ──────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        section_label("HCP targeting mix")
        mix = mkt.get("hcp_targeting_mix") or {}
        if mix:
            fig = _hcp_mix_chart(mix)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.write("No data.")

    with right:
        section_label("Key competitor molecules")
        comps = mkt.get("key_competitor_molecules") or []
        if comps:
            pills = "".join(
                f'<span class="pill" style="display:inline-block;'
                f'margin-right:6px;margin-bottom:8px;">{c}</span>'
                for c in comps
            )
            st.markdown(f'<div style="margin-top:0.5rem;">{pills}</div>',
                        unsafe_allow_html=True)
        else:
            st.write("No data.")


# ════════════════════════════════════════════════════════════════════════════
#  HCP MIX CHART
# ════════════════════════════════════════════════════════════════════════════

def _hcp_mix_chart(mix: dict) -> go.Figure:
    """Horizontal bar chart of HCP specialty targeting mix."""
    labels = list(mix.keys())
    values = list(mix.values())

    # Sort descending by value
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=charts.ACCENT, line=dict(color="white", width=0)),
        text=[f"{v}%" for v in values],
        textposition="outside",
        textfont=dict(family="Inter Tight", color=charts.INK),
        hovertemplate="<b>%{y}</b><br>%{x}% of targeting<extra></extra>",
    ))

    fig.update_layout(
        height=min(420, 80 + 50 * len(labels)),
        margin=dict(l=10, r=40, t=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter Tight, sans-serif", size=12, color=charts.INK),
        xaxis=dict(
            showgrid=True, gridcolor=charts.LINE,
            zeroline=False, showline=False,
            range=[0, max(values) * 1.18],
            color=charts.INK_SOFT,
            ticksuffix="%",
        ),
        yaxis=dict(
            showgrid=False, showline=False,
            autorange="reversed",
            color=charts.INK,
        ),
    )
    return fig
