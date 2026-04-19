"""
Global CSS for MedScope.

Design intent: refined minimalism — white/off-white base, disciplined
typography, generous whitespace, a single accent color (slate blue) used
sparingly. No gradients, no rounded-everything, no shadows by default.
The aesthetic should read as "Bloomberg for medical literature".

Injected once from app.py via inject_css().
"""
import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Inter+Tight:wght@300;400;500;600;700&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────── */
:root {
    --ink:          #1a1f2e;
    --ink-soft:     #4a5364;
    --ink-faint:    #8590a1;
    --paper:        #fdfdfc;
    --paper-tint:   #f6f5f2;
    --line:         #e3e1dc;
    --line-soft:    #eceae4;
    --accent:       #2d4a7a;
    --accent-soft:  #dce4f0;
    --good:         #2d6a4f;
    --warn:         #9a6014;
    --bad:          #8b2a2a;
}

/* ── Base ──────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter Tight', -apple-system, sans-serif !important;
    color: var(--ink);
}
.stApp {
    background: var(--paper);
}

/* ── Display typography ────────────────────────────────────────────── */
h1, h2, h3, h4 {
    font-family: 'Fraunces', Georgia, serif !important;
    color: var(--ink) !important;
    letter-spacing: -0.01em !important;
    font-weight: 500 !important;
}
h1 { font-size: 2.4rem !important; font-weight: 400 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 1.6rem !important; margin-top: 1.8rem !important; }
h3 { font-size: 1.15rem !important; margin-top: 1.2rem !important; }

/* Streamlit's default "Home" header spacing */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--paper-tint) !important;
    border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: var(--ink-soft) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--ink) !important;
}

/* ── Small-caps section labels ─────────────────────────────────────── */
.section-label {
    font-family: 'Inter Tight', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: 6px;
}

/* ── Buttons ───────────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: var(--ink) !important;
    color: var(--paper) !important;
    border: 1px solid var(--ink) !important;
    border-radius: 0 !important;
    font-family: 'Inter Tight', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    padding: 0.55rem 1.4rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] > button:hover {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}
[data-testid="stButton"] > button:focus {
    box-shadow: none !important;
    outline: 2px solid var(--accent-soft) !important;
    outline-offset: 2px !important;
}

/* ── Inputs ────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stDateInput input,
.stNumberInput input {
    background: var(--paper) !important;
    border: 1px solid var(--line) !important;
    border-radius: 0 !important;
    color: var(--ink) !important;
    font-family: 'Inter Tight', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: none !important;
}

/* ── Metric-style stat cards ───────────────────────────────────────── */
.stat-card {
    background: var(--paper);
    border: 1px solid var(--line);
    padding: 1.2rem 1.4rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.stat-card .value {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 400;
    line-height: 1;
    color: var(--ink);
}
.stat-card .label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-faint);
}
.stat-card.accent {
    background: var(--paper-tint);
    border-left: 3px solid var(--accent);
}

/* ── Divider ───────────────────────────────────────────────────────── */
.rule {
    height: 1px;
    background: var(--line);
    margin: 2rem 0 1.5rem 0;
}
.rule-thin {
    height: 1px;
    background: var(--line-soft);
    margin: 1.2rem 0;
}

/* ── Tabs ──────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid var(--line) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter Tight', sans-serif !important;
    font-weight: 500 !important;
    color: var(--ink-soft) !important;
    background: transparent !important;
    border-radius: 0 !important;
    padding: 10px 20px !important;
    margin-right: 2px !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--ink) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* ── DataFrames / Tables ───────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid var(--line) !important;
}
.stDataFrame [role="columnheader"] {
    background: var(--paper-tint) !important;
    color: var(--ink) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid var(--line) !important;
}

/* ── Badges / pills ────────────────────────────────────────────────── */
.pill {
    display: inline-block;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink-soft);
}
.pill.accent { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.pill.good   { background: #e3efe9; border-color: var(--good);   color: var(--good); }
.pill.warn   { background: #f7ecd6; border-color: var(--warn);   color: var(--warn); }
.pill.bad    { background: #f2dddd; border-color: var(--bad);    color: var(--bad); }

/* ── Paper card for top-paper lists ────────────────────────────────── */
.paper-row {
    padding: 0.9rem 0;
    border-bottom: 1px solid var(--line-soft);
}
.paper-row:last-child { border-bottom: none; }
.paper-row .title {
    font-weight: 500;
    color: var(--ink);
    margin-bottom: 4px;
    line-height: 1.35;
}
.paper-row .meta {
    font-size: 0.8rem;
    color: var(--ink-faint);
}
.paper-row .meta a {
    color: var(--accent);
    text-decoration: none;
}
.paper-row .score {
    font-family: 'Fraunces', serif;
    font-size: 1.4rem;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
}

/* ── Chatbot panel ─────────────────────────────────────────────────── */
.chat-panel {
    background: var(--paper-tint);
    border: 1px solid var(--line);
    padding: 1.4rem 1.6rem;
}
.chat-answer {
    background: var(--paper);
    border-left: 3px solid var(--accent);
    padding: 1rem 1.2rem;
    margin-top: 1rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--ink);
}

/* ── Progress ──────────────────────────────────────────────────────── */
.stProgress > div > div > div > div {
    background: var(--accent) !important;
}

/* ── Info/success boxes ────────────────────────────────────────────── */
.stAlert { border-radius: 0 !important; }

/* ── Plotly chart spacing ──────────────────────────────────────────── */
.js-plotly-plot {
    font-family: 'Inter Tight', sans-serif !important;
}

/* ── Footer ────────────────────────────────────────────────────────── */
#MainMenu      { visibility: hidden; }
footer         { visibility: hidden; }
/* header kept visible so the sidebar toggle stays accessible */
#header         { visibility: hidden; }

/* ── Labels ────────────────────────────────────────────────────────── */
label, .stSelectbox label, .stDateInput label, .stTextInput label {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: var(--ink-soft) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── Illustrative mock data banner ─────────────────────────────────── */
.mock-banner {
    background: #fdf7ea;
    border: 1px solid #e8d5a3;
    padding: 8px 14px;
    font-size: 0.78rem;
    color: #735020;
    margin-bottom: 1rem;
}
</style>
"""


def inject_css() -> None:
    """Inject the stylesheet. Call once at the top of app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)


def section_label(text: str) -> None:
    """Render a small-caps section label."""
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def rule() -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)


def rule_thin() -> None:
    st.markdown('<div class="rule-thin"></div>', unsafe_allow_html=True)
