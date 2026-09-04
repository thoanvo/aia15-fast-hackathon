"""Frontend Component - Response Display.

Renders the assistant's answer, business insights, recommendations, and any
attached chart/visualization.
"""

import pandas as pd
import streamlit as st

import api_client


def render_answer(text: str, source_tables: list[str] | None = None) -> None:
    st.markdown(text)
    if source_tables:
        st.caption(f"📊 Data source: {', '.join(t.capitalize() for t in source_tables)} table(s)")


def render_kb_chunks(chunks: list[str]) -> None:
    """Render the knowledge-base chunks that were retrieved for this answer.

    Shows each chunk in a collapsible expander so the user can inspect the
    exact schema / SQL snippets that the RAG retriever surfaced.
    """
    if not chunks:
        return
    with st.expander(f"📚 Knowledge Base used ({len(chunks)} chunk(s))", expanded=False):
        for i, chunk in enumerate(chunks, start=1):
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #f0f4ff 0%, #f8f9ff 100%);
                    border-left: 3px solid #4f8ef7;
                    border-radius: 6px;
                    padding: 10px 14px;
                    margin-bottom: 10px;
                    font-size: 0.82em;
                    font-family: 'JetBrains Mono', 'Courier New', monospace;
                    color: #2d3748;
                    white-space: pre-wrap;
                    word-break: break-word;
                ">
                <span style="color:#4f8ef7;font-weight:600;font-family:sans-serif;">
                    Chunk {i}
                </span><br/>{chunk}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_tts(text: str, key_prefix: str) -> None:
    audio_key = f"{key_prefix}_tts_audio"
    loading_key = f"{key_prefix}_tts_loading"

    if st.button("🔊 Listen", key=f"{key_prefix}_tts_button", help="Read this response aloud"):
        st.session_state[loading_key] = True
        st.session_state.pop(audio_key, None)

    if st.session_state.get(loading_key):
        with st.spinner("Synthesizing speech..."):
            audio_bytes = api_client.synthesize_speech(text)
        st.session_state[loading_key] = False
        if audio_bytes:
            st.session_state[audio_key] = audio_bytes
        else:
            st.warning(
                "⚠️ TTS model is not ready yet "
                "(still downloading or unavailable). Please try again shortly."
            )

    if st.session_state.get(audio_key):
        st.audio(st.session_state[audio_key], format="audio/wav", autoplay=True)


def render_insights(insight: str) -> None:
    with st.expander("Business Insights", expanded=True, icon="📊"):
        st.markdown(insight)
        render_tts(insight, "insight")


def render_recommendations(recommendation: str) -> None:
    with st.expander("Recommendations", expanded=True, icon="✅"):
        st.markdown(recommendation)
        render_tts(recommendation, "recommendation")


def render_data_chart(chart_data: list[dict] | None) -> None:
    """Render `chart_data` (a list of {"x": ..., "y": ...} records from
    `langchain_app.chart_data.extract_chart_data()`) as a Streamlit
    built-in chart - no new charting library needed. No-op when
    `chart_data` is None/empty, which is the common case (most answers
    aren't chart-worthy), not an error.

    Chart type: a line chart when every `x` value looks like a date/time
    bucket (a string containing a digit, e.g. "2025-01"), a bar chart
    otherwise (categorical comparison, e.g. product/region names).
    """
    if not chart_data:
        return
    x_values = [row["x"] for row in chart_data]
    looks_like_a_trend = all(isinstance(x, str) and any(char.isdigit() for char in x) for x in x_values)
    data_frame = pd.DataFrame(chart_data).set_index("x")
    if looks_like_a_trend:
        st.line_chart(data_frame)
    else:
        st.bar_chart(data_frame)


def render_chart(figure) -> None:
    """Render an optional chart (e.g. Plotly figure), if one was produced.

    No-op when `figure` is None - chart generation isn't wired into the
    backend yet (see docs/business_description.md > Future Enhancements >
    Data Visualization); this hook exists so it can be dropped in later
    without touching page code.
    """
    if figure is not None:
        st.plotly_chart(figure, use_container_width=True)

