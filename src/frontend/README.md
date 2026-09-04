# frontend/

Streamlit multipage UI (`st.navigation`/`st.Page`), talking to the backend
over plain HTTP/JSON (`api_client.py`). No business logic here — same chat
UI, same logic as the prior implementation, since only the backend AI
layer changed.

- `app.py` — `st.navigation` entry point
- `api_client.py` — thin `requests` wrapper around the backend API (`.env` is read from the repo root, not `src/.env`)
- [`pages/`](pages/README.md) — `home.py`, `chat.py`
- [`components/`](components/README.md) — `chat_interface.py`, `response_display.py`, `conversation_history.py` (both `chat_interface.render_message_thread()` and `response_display.render_answer()` already render `source_tables` captions)

## Run

```bash
# from src/
streamlit run frontend/app.py
```

Requires the backend to be running (see `../backend/README.md`) for
anything beyond the Home page's status check.

**Status:** Phase 6 complete — ported near-verbatim. Verified end-to-end
with a real backend (FastAPI `app` run via `uvicorn` in a background
thread, `chat_service`'s `AgentExecutor` swapped for one built from a
scripted fake chat model — same stubbing technique as Phases 4-5) driven
by Streamlit's official `AppTest` headless testing framework: both pages
render with no exceptions, backend/DB status metrics degrade gracefully
when unreachable, clicking a suggested question round-trips through the
real HTTP API and persists correctly across the page's internal
`st.rerun()`, and the `source_tables` caption renders correctly
("📊 Data source: Sales, Products, Regions table(s)"). This also confirmed
`api_client.py`'s `trust_env=False` workaround is necessary in this
environment — it has `HTTP_PROXY`/`HTTPS_PROXY` set system-wide, which
otherwise intercepts loopback traffic to the backend.
