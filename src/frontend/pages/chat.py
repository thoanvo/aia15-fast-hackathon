"""Frontend Page - Chat.

Main conversational interface: question input, streamed answer, insights,
and recommendations.
"""

import threading
import uuid

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx

import api_client
from components.chat_interface import render_chat_input, render_message_thread, render_suggested_questions
from components.conversation_history import render_history_sidebar
from components.response_display import render_insights, render_recommendations

st.set_page_config(page_title="Chat - Database Query Assistant", page_icon="💬", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Right-align the user's chat bubble; assistant stays on the left. */
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
        flex-direction: row-reverse;
        margin-left: auto;
        max-width: 80%;
    }
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"])
        [data-testid="stChatMessageContent"] {
        text-align: right;
    }

    .st-key-insight_recommendation_buttons {
        margin: 20px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "last_question" not in st.session_state:
    st.session_state.last_question = None
if "last_insight" not in st.session_state:
    st.session_state.last_insight = None
if "last_recommendation" not in st.session_state:
    st.session_state.last_recommendation = None
if "last_kb_chunks" not in st.session_state:
    # KB chunks from the most-recent assistant turn, for display below the answer.
    st.session_state.last_kb_chunks = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "chat_result" not in st.session_state:
    # Set by the background thread (see _send_message_worker) once the
    # in-flight /chat call finishes; None while a question is still pending.
    st.session_state.chat_result = None
if "pending_insight" not in st.session_state:
    st.session_state.pending_insight = False
if "pending_recommendation" not in st.session_state:
    st.session_state.pending_recommendation = False
# True from the moment any button is clicked until its request finishes -
# every button in the UI is rendered with disabled=processing so a user
# can't fire a second request (e.g. Clear chat) while one is in flight.
if "processing" not in st.session_state:
    st.session_state.processing = False

conversation_id = st.session_state.conversation_id


def _safe_get_history(cid: str) -> list[dict]:
    try:
        return api_client.get_history(cid)
    except Exception:
        return []


def _send_message_worker(cid: str, question: str) -> None:
    """Run on a background thread so the main script stays free to handle a Cancel click."""
    try:
        answer, source_tables, kb_chunks, chart_data = api_client.send_message(cid, question)
    except Exception as exc:
        answer, source_tables, kb_chunks, chart_data = f"⚠️ Could not reach the backend: {exc}", [], [], None
    st.session_state.chat_result = {
        "answer": answer,
        "source_tables": source_tables,
        "kb_chunks": kb_chunks,
        "chart_data": chart_data,
    }


def _start_question(question: str) -> None:
    st.session_state.pending_question = question
    st.session_state.processing = True
    st.session_state.chat_result = None
    thread = threading.Thread(
        target=_send_message_worker, args=(conversation_id, question), daemon=True
    )
    add_script_run_ctx(thread)
    thread.start()
    st.rerun()


@st.fragment(run_every=0.5)
def _render_pending_question() -> None:
    """Poll the background call while it runs; lets Cancel stay clickable while it's in flight.

    Note: clicking Cancel only stops the UI from waiting on the request - the
    backend call keeps running in a daemon thread and may still land in the
    conversation history once it finishes (HTTP requests can't be aborted
    mid-flight without closing the connection).
    """
    if not st.session_state.processing or not st.session_state.pending_question:
        return

    question = st.session_state.pending_question
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.status("Thinking & Retrieving Knowledge...", state="running")
            if st.button("✖️ Cancel", key="cancel_chat_request"):
                st.session_state.processing = False
                st.session_state.pending_question = None
                st.session_state.chat_result = None
                st.rerun()

    if st.session_state.chat_result is not None:
        st.session_state.last_question = question
        st.session_state.last_insight = None
        st.session_state.last_recommendation = None
        st.session_state.last_kb_chunks = st.session_state.chat_result.get("kb_chunks", [])
        st.session_state.pending_question = None
        st.session_state.processing = False
        st.session_state.chat_result = None
        st.rerun()


with st.sidebar:
    history_for_sidebar = _safe_get_history(conversation_id)
    past_questions = [m["content"] for m in history_for_sidebar if m["role"] == "user"]
    if render_history_sidebar(past_questions, disabled=st.session_state.processing):
        try:
            api_client.clear_conversation(conversation_id)
        except Exception as exc:
            st.error(f"Could not clear the conversation on the backend: {exc}")
        else:
            st.session_state.conversation_id = str(uuid.uuid4())
            st.session_state.last_question = None
            st.session_state.last_insight = None
            st.session_state.last_recommendation = None
            st.session_state.last_kb_chunks = []
            st.rerun()

    # Demo toggle: flip FIXED_TOOLS_ENABLED at runtime (backend.controllers.
    # settings_controller) instead of editing .env and restarting the
    # backend - takes effect on the next question.
    st.divider()
    st.caption("⚙️ Chat Settings")
    try:
        current_fixed_tools_enabled = api_client.get_fixed_tools_enabled()
    except Exception:
        current_fixed_tools_enabled = True
    fixed_tools_toggle = st.toggle(
        "Hybrid Analytics Engine​",
        value=current_fixed_tools_enabled,
        disabled=st.session_state.processing,
        help=(
            "On: Combines pre-built business analytics and AI-generated SQL for complete coverage.​ "
            "Off: only AI-generated SQL "
            "are available. Applies to the "
            "next question."
        ),
    )
    if fixed_tools_toggle != current_fixed_tools_enabled:
        try:
            api_client.set_fixed_tools_enabled(fixed_tools_toggle)
        except Exception as exc:
            st.error(f"Could not update the setting: {exc}")
        st.rerun()

    # System Status in sidebar
    st.divider()
    st.caption("🔌 Backend API")
    if api_client.check_backend_health():
        st.success("Backend API ✅ Online")
    else:
        st.error("Backend API ❌ Offline")

    st.caption("🗄️ Database Status")
    if api_client.check_db_health():
        st.success("PostgreSQL Database ✅ Connected")
    else:
        st.error("PostgreSQL Database ❌ Disconnected")

    st.caption("📚 RAG Vector Knowledge Base")
    rag_status = api_client.check_rag_health()
    if rag_status.get("status") == "ready":
        chunk_cnt = rag_status.get("total_chunks", 0)
        st.success(f"FAISS ✅ Active ({chunk_cnt} chunks)")
    else:
        st.warning("FAISS ⚠️ Unavailable")

    st.caption("🔊 Text-to-Speech")
    tts_status = api_client.check_tts_health()
    if tts_status.get("available"):
        st.success("TTS ✅ Ready (Kokoro-82M)")
    elif tts_status.get("downloading"):
        st.info("TTS ⏳ Downloading model...")
    else:
        st.warning("TTS ⚠️ Model not available")

st.title("💬 Database Query Assistant")
st.caption("Ask business questions in natural language - augmented with Database Schema & Sample SQL RAG.")

st.subheader("Suggested questions")
selected_suggestion = render_suggested_questions(disabled=st.session_state.processing)
if selected_suggestion:
    _start_question(selected_suggestion)

render_message_thread(_safe_get_history(conversation_id))

typed_question = render_chat_input(disabled=st.session_state.processing)
if typed_question:
    _start_question(typed_question)

_render_pending_question()

st.markdown("---")
with st.container(
    horizontal=True,
    horizontal_alignment="left",
    gap="small",
    width="content",
    key="insight_recommendation_buttons",
):
    insight_disabled = st.session_state.last_question is None or st.session_state.processing
    insight_clicked = st.button("📊 Generate Insight", disabled=insight_disabled)

    recommendation_disabled = st.session_state.last_insight is None or st.session_state.processing
    recommendation_clicked = st.button("✅ Generate Recommendation", disabled=recommendation_disabled)

if insight_clicked:
    st.session_state.pending_insight = True
    st.session_state.processing = True
    st.rerun()

if recommendation_clicked:
    st.session_state.pending_recommendation = True
    st.session_state.processing = True
    st.rerun()

if st.session_state.pending_insight:
    with st.spinner("Analyzing..."):
        try:
            st.session_state.last_insight = api_client.generate_insight(
                conversation_id, st.session_state.last_question
            )
        except Exception as exc:
            st.session_state.last_insight = f"⚠️ Could not generate insight: {exc}"
    st.session_state.pending_insight = False
    st.session_state.processing = False
    st.rerun()

if st.session_state.pending_recommendation:
    with st.spinner("Thinking of recommendations..."):
        try:
            st.session_state.last_recommendation = api_client.generate_recommendation(
                conversation_id, st.session_state.last_insight
            )
        except Exception as exc:
            st.session_state.last_recommendation = f"⚠️ Could not generate recommendation: {exc}"
    st.session_state.pending_recommendation = False
    st.session_state.processing = False
    st.rerun()

if st.session_state.last_insight:
    render_insights(st.session_state.last_insight)
if st.session_state.last_recommendation:
    render_recommendations(st.session_state.last_recommendation)
