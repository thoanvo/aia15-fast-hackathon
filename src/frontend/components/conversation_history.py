"""Frontend Component - Conversation History.

Renders the sidebar list of past user questions in the current session and
supports clearing history.
"""

import streamlit as st


def render_history_sidebar(questions: list[str], disabled: bool = False) -> bool:
    """Render past user questions in the sidebar. Returns True if "Clear chat" was clicked."""
    st.subheader("Conversation History")
    if questions:
        for i, question in enumerate(questions, 1):
            st.markdown(f"**{i}.** {question}")
    else:
        st.caption("No questions yet.")

    return st.button("🗑️ Clear chat", disabled=disabled, use_container_width=True)
