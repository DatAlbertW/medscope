"""
Chatbot panel for the dashboard.

The user picks ONE predefined question at a time. The answer is generated
live by the LLM, streaming token-by-token into the UI. Uses tight scope —
LLM only sees the loaded MoleculeReport data.
"""
from __future__ import annotations

import streamlit as st

from core import chat_engine
from core.llm_client import get_client
from core.models import MoleculeReport
from ui.styles import section_label


def render(report: MoleculeReport) -> None:
    """Render the chatbot panel at the bottom of the dashboard."""
    st.markdown('<div class="chat-panel">', unsafe_allow_html=True)

    section_label("Ask MedScope")
    st.markdown(
        f'<div style="font-family:Fraunces,Georgia,serif;font-size:1.3rem;'
        f'color:var(--ink);margin-bottom:0.3rem;">'
        f'Questions about {report.molecule}'
        f'</div>'
        f'<div style="font-size:0.85rem;color:var(--ink-soft);margin-bottom:1rem;">'
        f'Pick a question and the assistant will generate a live answer '
        f'using only the data on this dashboard.'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Question picker ─────────────────────────────────────────────────────
    questions = chat_engine.get_question_labels()   # list of (id, label)
    labels = ["— choose a question —"] + [q[1] for q in questions]
    label_to_id = {label: qid for qid, label in questions}

    picked_label = st.selectbox(
        "Question",
        labels,
        index=0,
        key="chatbot_question",
        label_visibility="collapsed",
    )

    # ── Ask button ──────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 5])
    ask_disabled = picked_label == "— choose a question —"
    ask = col1.button("Ask", key="chatbot_ask", disabled=ask_disabled)

    # ── Generate live answer ────────────────────────────────────────────────
    if ask and not ask_disabled:
        # Get key from secrets, then fall back to manually entered key
        api_key = ""
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or ""
        except Exception:
            api_key = ""
        if not api_key:
            api_key = st.session_state.get("manual_api_key", "")
        if not api_key:
            st.error("Anthropic API key required. Enter it in the sidebar.")
        else:
            qid = label_to_id[picked_label]
            _stream_answer(api_key, report, qid, picked_label)


# ════════════════════════════════════════════════════════════════════════════
#  STREAMING HELPER
# ════════════════════════════════════════════════════════════════════════════

def _stream_answer(
    groq_key: str,
    report: MoleculeReport,
    question_id: str,
    question_label: str,
) -> None:
    """Stream the LLM answer into a live-updating panel."""
    st.markdown(
        f'<div class="chat-answer">'
        f'<div class="section-label" style="margin-bottom:0.5rem">Answer</div>'
        f'<div style="font-family:Fraunces,Georgia,serif;font-size:1.05rem;'
        f'margin-bottom:0.8rem;color:var(--ink);">'
        f'{question_label}'
        f'</div>',
        unsafe_allow_html=True,
    )

    placeholder = st.empty()
    buffer = ""

    try:
        client = get_client(groq_key)
        for delta in chat_engine.ask(client, report, question_id):
            buffer += delta
            # Live render the accumulated answer
            placeholder.markdown(buffer)
    except Exception as e:
        placeholder.error(f"Could not generate answer: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
