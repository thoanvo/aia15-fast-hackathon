"""Frontend Page - Home.

Landing page: project intro, backend/database connection status, quick link
to the Chat page.
"""

import streamlit as st

import api_client

st.set_page_config(page_title="Home - Database Query Assistant", page_icon="🏠", layout="wide")

st.title("🏠 Database Query Assistant")
st.markdown(
    "Ask business questions about products, customers, sales, and regions "
    "in plain English or Vietnamese - no SQL required.\n\n"
)

st.subheader("System status")
col1, col2 = st.columns(2)
with col1:
    st.metric("Backend API", "🟢 Online" if api_client.check_backend_health() else "🔴 Offline")
with col2:
    st.metric("Database", "🟢 Online" if api_client.check_db_health() else "🔴 Offline")

st.markdown("---")
st.page_link("pages/chat.py", label="Go to Chat", icon="💬")
