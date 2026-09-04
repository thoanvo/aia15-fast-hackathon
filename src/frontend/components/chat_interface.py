"""Frontend Component - Chat Interface.

Renders the chat input box and message thread (user + assistant turns).
"""

import streamlit as st

from components.response_display import render_data_chart, render_kb_chunks, render_tts


_DEFAULT_SUGGESTED_QUESTIONS = [
    "What are the top 5 products by revenue?",
    "Who are the top customers this month?",
    "Show the sales trend for the last 6 months.",
    "What is the profit analysis by region?",
]

# Phrases that count as the user explicitly asking for a chart in their
# question - matched against the *user's* turn, not the assistant's answer.
_CHART_REQUEST_HINTS = (
    "chart", "graph", "plot", "visualize", "visualization",
    "biểu đồ", "đồ thị",
)


def _question_asked_for_chart(question: str) -> bool:
    text = question.lower()
    return any(hint in text for hint in _CHART_REQUEST_HINTS)


def _render_chart_toggle(chart_data: list[dict], index: int, question: str) -> None:
    """Show a chart only on demand: auto-visible if the user's own question
    asked for one (`_question_asked_for_chart`), otherwise hidden behind a
    "Show chart" button - most chart-worthy answers weren't explicitly
    asked for as a chart, so rendering one unconditionally is noisier than
    useful.
    """
    visible_key = f"chart_visible_{index}"
    if visible_key not in st.session_state:
        st.session_state[visible_key] = _question_asked_for_chart(question)

    label = "🙈 Hide chart" if st.session_state[visible_key] else "📈 Show chart"
    if st.button(label, key=f"chart_toggle_{index}"):
        st.session_state[visible_key] = not st.session_state[visible_key]

    if st.session_state[visible_key]:
        render_data_chart(chart_data)


def render_message_thread(messages: list[dict]) -> None:
    """Render the conversation as chat bubbles.

    Skips assistant turns with no text (backend.models.message.Message
    only ever stores user/assistant turns with content, but an empty/None
    content is skipped defensively). Also renders each message's
    `source_tables` as a caption, `kb_chunks` as a collapsible expander,
    and `chart_data` (if any) behind a show/hide toggle (see
    `_render_chart_toggle`). Each assistant message gets a 🔊 TTS button.
    """
    for i, msg in enumerate(messages):
        content = msg.get("content")
        if not content:
            continue
        with st.chat_message(msg["role"]):
            st.markdown(content)
            source_tables = msg.get("source_tables")
            if source_tables:
                st.caption(f"📊 Data source: {', '.join(t.capitalize() for t in source_tables)} table(s)")
            # Show KB chunks/chart for assistant turns that produced them
            if msg["role"] == "assistant":
                chart_data = msg.get("chart_data")
                if chart_data:
                    question = messages[i - 1].get("content", "") if i > 0 else ""
                    _render_chart_toggle(chart_data, i, question)
                kb_chunks = msg.get("kb_chunks", [])
                render_kb_chunks(kb_chunks)
                render_tts(content, f"message_{i}")


def render_chat_input(
    placeholder: str = "Ask a question about your data...", disabled: bool = False
) -> str | None:
    """Render the chat input box; returns the submitted question, or None."""
    return st.chat_input(placeholder, disabled=disabled)


def render_suggested_questions(questions: list[str] | None = None, disabled: bool = False) -> str | None:
    """Render quick-start prompts and return the selected question, if any."""
    st.caption("Try one of these quick questions")
    suggestions = questions or _DEFAULT_SUGGESTED_QUESTIONS

    selected_question = None
    columns = st.columns(2)
    for index, question in enumerate(suggestions):
        column = columns[index % len(columns)]
        with column:
            if st.button(
                question, key=f"suggested-question-{index}", disabled=disabled, use_container_width=True
            ):
                selected_question = question

    return selected_question
