# frontend/pages/

| File | Purpose |
|---|---|
| `home.py` | Landing page: project intro, live Backend/Database status (`api_client.check_backend_health()` / `check_db_health()`), link to Chat. |
| `chat.py` | Main conversational interface: session-scoped `conversation_id`, chat history, suggested questions, sends questions to `POST /api/v1/chat`, plus "Generate Insight"/"Generate Recommendation" buttons wired to the corresponding backend endpoints. |

Imports here are relative to `frontend/` (e.g. `import api_client`,
`from components.chat_interface import ...`), not `frontend.pages...` —
`streamlit run frontend/app.py` puts `frontend/` on `sys.path`, and that
stays true when `st.navigation` switches to a page in this folder.
