"""Frontend - Web UI Entry Point.

Responsibilities (docs/business_description.md > Frontend Layer > Web UI):
- Accept user questions in natural language
- Display chatbot responses, business insights, and recommendations
- Manage conversation history and context
"""

import streamlit as st

pg = st.navigation([
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/chat.py", title="Chat", icon="💬"),
])
pg.run()
