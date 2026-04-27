"""
Plotly chart builders for the dashboard.

Three charts:
    1. Publication timeline — line chart, papers per year by category
    2. World map — RWE geographic distribution with country drill-down
    3. Phase breakdown — donut chart of trial phases

All charts use the same minimal white/gray/slate aesthetic as the rest
of the UI. Tightly styled with explicit margins and typography.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.categories import CATEGORIES


# ── Shared styling ─────────────────────────────────────────────────────────
INK          = "#1a1f2e"
INK_SOFT     = "#4a5364"
INK_FAINT    = "#8590a1"
LINE         = "#e3e1dc"
ACCENT       = "#2d4a7a"
PAPER_TINT   = "#f6f5f2"

# Palette for categories (muted, purposeful)
CATEGORY_COLORS = {
    "clinically_relevant":  "#2d4a7a",   # slate blue
    "safety_efficacy":       "#9a6014",   # ochre
    "trial_results":         "#2d6a4f",   # forest
    "real_world_evidence":   "#6b3e8b",   # plum
}


def _apply_minimal_layout(fig: go.Figure, height: int = 320) -> go.Figure:
    """Apply the minimal white/gray layout to any Plotly figure."""
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter Tight, sans-serif", size=12, color=INK),
        title=dict(
            font=dict(family="Fraunces, Georgia, serif", size=16, color=INK),
            x=0, y=0.96, xanchor="left",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.25,
            xanchor="left",   x=0,
            font=dict(size=11, color=INK_SOFT),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showgrid=False,
            linecolor=LINE,
            tickcolor=LINE,
            color=INK_SOFT,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=LINE,
            linecolor=LINE,
            tickcolor=LINE,
            color=INK_SOFT,
            zeroline=False,
        ),
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════
#  1. PUBLICATION TIMELINE
# ════════════════════════════════════════════════════════════════════════════

def publication_timeline(yearly_counts: dict[str, dict[int, int]]) -> go.Figure:
    """
    Line chart: papers per year, colored by category.
    Input: { "clinically_relevant": { 2022: 4, ... }, ... }
    """
    rows: list[dict[str, Any]] = []
    for cat, year_map in yearly_counts.items():
        label = CATEGORIES.get(cat, {}).get("label", cat)
        for year, count in sorted(year_map.items()):
            rows.append({"year": year, "count": count, "category": label, "cat_id": cat})

    if not rows:
        return _empty_figure("Publication timeline", "No papers in the selected range.")

    df = pd.DataFrame(rows)

    fig = go.Figure()
    for cat_id in CATEGORIES:
        sub = df[df["cat_id"] == cat_id]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"],
            y=sub["count"],
            mode="lines+markers",
            name=CATEGORIES[cat_id]["label"],
            line=dict(color=CATEGORY_COLORS.get(cat_id, INK), width=2.5),
            marker=dict(size=7, line=dict(width=1, color="white")),
            hovertemplate="<b>%{x}</b><br>%{y} papers<extra></extra>",
        ))

    fig.update_layout(title="Publications by year")
    fig.update_xaxes(dtick=1, tickformat="d")
    fig.update_yaxes(rangemode="tozero")
    return _apply_minimal_layout(fig, height=340)


# ════════════════════════════════════════════════════════════════════════════
#  2. RWE WORLD MAP
# ════════════════════════════════════════════════════════════════════════════

def rwe_world_map(geography: list[dict]) -> go.Figure:
    """
    Choropleth map of RWE study distribution by country, with hover info
    showing regional detail and cohort sizes when available.
    """
    if not geography:
        return _empty_figure("Real-world evidence geography", "No geographic data yet.")

    # Aggregate by country (ISO-2 → count + details)
    by_country: dict[str, dict] = {}
    for g in geography:
        iso = g.get("iso2")
        country = g.get("country")
        if not iso or not country:
            continue
        entry = by_country.setdefault(iso, {
            "country": country,
            "count": 0,
            "cohort_total": 0,
            "regions": set(),
        })
        entry["count"] += 1
        if g.get("cohort_size"):
            try:
                entry["cohort_total"] += int(g["cohort_size"])
            except (TypeError, ValueError):
                pass
        if g.get("region"):
            entry["regions"].add(g["region"])

    if not by_country:
        return _empty_figure("Real-world evidence geography", "No geographic data resolved.")

    df = pd.DataFrame([
        {
            "iso3": _iso2_to_iso3(iso),
            "iso2": iso,
            "country": data["country"],
            "count":   data["count"],
            "cohort":  data["cohort_total"],
            "regions": ", ".join(sorted(data["regions"])) or "—",
        }
        for iso, data in by_country.items()
    ])

    fig = go.Figure(data=go.Choropleth(
        locations=df["iso3"],
        z=df["count"],
        text=df["country"],
        customdata=df[["regions", "cohort"]],
        colorscale=[
            [0.0,  "#dbe5f1"],   # pale blue, still visible against white
            [0.25, "#a8bddc"],   # light blue
            [0.5,  "#6e8db9"],   # medium blue
            [0.75, "#3d5d8e"],   # darker blue
            [1.0,  "#1a2e4a"],   # deep slate (darkest)
        ],
        marker_line_color="white",
        marker_line_width=0.5,
        colorbar=dict(
            title=dict(text="Papers", font=dict(size=11, color=INK_SOFT)),
            thickness=10, len=0.6, x=1.02,
            tickfont=dict(size=10, color=INK_SOFT),
        ),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "%{z} paper(s)<br>"
            "Regions: %{customdata[0]}<br>"
            "Reported cohort total: %{customdata[1]:,}"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="Real-world evidence geography",
        geo=dict(
            showframe=False,
            showcoastlines=False,
            showland=True,
            landcolor=PAPER_TINT,
            projection_type="natural earth",
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=440,
        paper_bgcolor="white",
        font=dict(family="Inter Tight, sans-serif", size=12, color=INK),
    )
    fig.update_layout(title=dict(
        font=dict(family="Fraunces, Georgia, serif", size=16, color=INK),
        x=0, y=0.96, xanchor="left",
    ))
    return fig


# ════════════════════════════════════════════════════════════════════════════
#  3. TRIAL PHASE BREAKDOWN
# ════════════════════════════════════════════════════════════════════════════

def trial_phase_donut(phases: dict[str, int]) -> go.Figure:
    """Donut chart of trial phases from the Trial Results papers."""
    if not phases:
        return _empty_figure("Trial phases", "No trial phase data yet.")

    labels = list(phases.keys())
    values = list(phases.values())

    phase_colors = {
        "Phase 1":        "#c9d3e3",
        "Phase 2":        "#8aa0c2",
        "Phase 3":        ACCENT,
        "Phase 4":        "#1a2e4a",
        "Not specified":  "#d8d5cf",
    }
    colors = [phase_colors.get(p, "#b8b5ae") for p in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(family="Inter Tight", size=11, color=INK_SOFT),
        hovertemplate="<b>%{label}</b><br>%{value} paper(s) (%{percent})<extra></extra>",
    )])

    total = sum(values)
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:11px;color:{INK_FAINT}'>trials</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(family="Fraunces, Georgia, serif", size=26, color=INK),
    )

    fig.update_layout(
        title="Trial phases",
        showlegend=False,
        height=340,
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor="white",
        font=dict(family="Inter Tight, sans-serif", size=12, color=INK),
    )
    fig.update_layout(title=dict(
        font=dict(family="Fraunces, Georgia, serif", size=16, color=INK),
        x=0, y=0.96, xanchor="left",
    ))
    return fig


# ════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        font=dict(family="Inter Tight", size=13, color=INK_FAINT),
    )
    fig.update_layout(
        title=title,
        height=300,
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        font=dict(family="Inter Tight, sans-serif", color=INK),
    )
    fig.update_layout(title=dict(
        font=dict(family="Fraunces, Georgia, serif", size=16, color=INK),
        x=0, y=0.96, xanchor="left",
    ))
    return fig


def _iso2_to_iso3(iso2: str) -> str:
    """Convert ISO-2 to ISO-3 country code (for Plotly choropleth)."""
    mapping = {
        "US": "USA", "GB": "GBR", "DE": "DEU", "FR": "FRA", "IT": "ITA",
        "ES": "ESP", "CH": "CHE", "NL": "NLD", "SE": "SWE", "DK": "DNK",
        "JP": "JPN", "CN": "CHN", "KR": "KOR", "CA": "CAN", "AU": "AUS",
        "BR": "BRA", "MX": "MEX", "AR": "ARG", "IN": "IND", "RU": "RUS",
        "AT": "AUT", "BE": "BEL", "FI": "FIN", "GR": "GRC", "IE": "IRL",
        "NO": "NOR", "PL": "POL", "PT": "PRT", "TR": "TUR", "IL": "ISR",
        "SA": "SAU", "SG": "SGP", "HK": "HKG", "TW": "TWN", "NZ": "NZL",
        "ZA": "ZAF", "EG": "EGY", "TH": "THA", "MY": "MYS", "ID": "IDN",
    }
    return mapping.get((iso2 or "").upper(), "")
