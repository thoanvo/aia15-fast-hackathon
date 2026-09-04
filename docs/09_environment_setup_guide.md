# Developer Setup Guide

Step-by-step environment setup for the Database Query Assistant
(Hackathon, LangChain-native), plus a troubleshooting section covering
real issues hit while building and testing this.

See also: [`../README.md`](../README.md) (quick start),
[`08_project_structure.md`](08_project_structure.md) (architecture), and each
`src/` subfolder's own `README.md` for what lives where.

---

## 1. Prerequisites

- Python 3.11+ (built and tested on 3.13)
- Git
- An OpenAI API key, **or** an OpenAI-compatible gateway URL + key
- A PostgreSQL (Neon) connection string — optional; the app still runs
  without one for everything except real database-backed answers (see
  §6 for how to swap in a fake/mocked backend for testing)

## 2. Clone and create a virtual environment

```bash
git clone <repo-url>
cd workshop04
python -m venv .venv
```

Activate it:

```powershell
# PowerShell
.venv\Scripts\Activate.ps1
```
```bash
# bash/zsh
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

This pulls in `torch` (via `sentence-transformers`) and `sqlalchemy` —
expect a sizeable download the first time (see §Troubleshooting F for a
DLL-load-order issue between the two on Windows).

## 4. Configure environment variables

```bash
cp .env.example .env
```

Edit the repo-root `.env` (not `src/.env` — this differs from some other
workshop repos):

| Variable | Required? | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes* | Neon PostgreSQL connection string. *Can be a placeholder if you're not running real DB-backed queries yet. |
| `OPENAI_API_KEY` | Yes | Your OpenAI (or gateway) API key. |
| `OPENAI_BASE_URL` | No | Only set this if going through an OpenAI-compatible proxy/gateway instead of `api.openai.com` directly. |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini`. |
| `OPENAI_VERIFY_SSL` | No | Set to `false` only if your gateway needs TLS verification disabled. |
| `VECTOR_STORE_DIR` | No | Defaults to `src/langchain_app/vectorstore/index` (absolute path, resolved regardless of cwd). |
| `EMBEDDING_MODEL_NAME` | No | Defaults to `sentence-transformers/all-MiniLM-L6-v2`. |
| `BACKEND_URL` | No | Frontend-only; where the backend API is running. Defaults to `http://127.0.0.1:8000`. |

`config/settings.py` fails fast with a clear message at import time if a
required variable is missing.

## 5. Initialize the database

If you have a working Neon connection:

```bash
cd src
python database/scripts/init_db.py
```

This drops/recreates `regions`, `products`, `customers`, `sales`, loads
sample data, then prints row counts to confirm. See
[`07_database_schema_reference.md`](07_database_schema_reference.md) for the schema.

## 6. Run the app

Two processes, both from `src/` (the app is designed to run with `src/`
as the working directory — see `08_project_structure.md`'s layering rule):

```bash
# Terminal 1 - backend API
cd src
uvicorn app:app --reload

# OR, without a real DB connection (see Troubleshooting D):
python dev_fake_backend.py

# Terminal 2 - web UI
cd src
streamlit run frontend/app.py
```

## 7. Verify it works

1. `http://127.0.0.1:8000/health` → `{"status": "ok"}`
2. `http://127.0.0.1:8000/health/db` → `{"status": "ok"}` (or `503` if the
   real DB is unreachable — expected if you skipped §5)
3. `http://127.0.0.1:8000/docs` → interactive API docs; try `POST /api/v1/chat`
   directly from the browser (see [`11_api_documentation.md`](11_api_documentation.md))
4. Open the Streamlit URL it prints (`http://localhost:8501`) and try:
   1. "What are the top 5 products by revenue?"
   2. "Only in Asia."
   3. "What insights can you provide?"

---

## Troubleshooting

### A. `streamlit`/`uvicorn` not recognized

`pip install` put the scripts in a directory that isn't on your `PATH`.
Call them as Python modules instead:

```bash
python -m streamlit run frontend/app.py
python -m uvicorn app:app --reload
```

### B. `403 URLBlocked` / proxy errors calling the backend from the frontend, or in your own test scripts

Some corporate networks run a web-filtering proxy that intercepts *even
loopback* traffic when `HTTP_PROXY`/`HTTPS_PROXY` are set system-wide —
confirmed present in the environment this repo was developed in.
`frontend/api_client.py` already works around this
(`requests.Session().trust_env = False`, so it ignores those env vars for
backend calls). If you write a new HTTP call anywhere in `frontend/` or in
a test script, route it through a `Session` with `trust_env = False` too —
a plain `requests.get(...)` will otherwise silently hang or fail against
`127.0.0.1` in this kind of environment (this bit us writing the Phase 6
frontend↔backend integration test).

If you hit this testing manually with `curl`, add `--noproxy '*'`.

### C. `openai.APIConnectionError` / TLS errors calling the AI gateway

Seen as e.g.:
```
httpcore.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1018)
openai.APIConnectionError: Connection error.
```

A corporate network may perform TLS interception on outbound HTTPS
traffic (gateway or otherwise), breaking default certificate
verification. Set `OPENAI_VERIFY_SSL=false` in `.env` in that case —
`langchain_app/llm.py`'s `get_llm()` always builds its own `httpx.Client(verify=...)`
(not only when `OPENAI_BASE_URL` is set) so this fixes both the
gateway case and a direct-to-`api.openai.com` connection behind the same
kind of network. Confirmed live: this exact error surfaced through both
the OOS classifier call (`oos_guard.py` caught it and failed open,
proceeding to the agent — see log `ERROR:langchain_app.agent:OOS check
failed; failing open...`) and the agent's own LLM call (which isn't
fail-open, since a genuine answer requires a working LLM — the request
correctly 500s with a logged, non-crashing error via
`chat_controller.py`'s existing exception handling) — both are the
intended behavior for this failure, not bugs.

**Don't guess whether `.env` actually took effect - check the startup log.**
`src/app.py` logs the resolved (non-secret) config once at startup:
```
INFO:app:Config: OPENAI_MODEL=... OPENAI_BASE_URL=... OPENAI_VERIFY_SSL=... EMBEDDING_MODEL_NAME=... VECTOR_STORE_DIR=... OOS_ENABLED=... OOS_SIMILARITY_THRESHOLD=...
```
If `OPENAI_VERIFY_SSL` prints `True` after you thought you set it to
`false`, one of these is true: `.env` isn't at the repo root (not
`src/.env`), the line has a typo (e.g. `False` vs `false` doesn't matter -
anything but the literal string `false` is treated as `true` - but a
stray quote or space can break the match), or the process wasn't
restarted after editing `.env` (env vars are read once at import time).
This is exactly how a second occurrence of the same
`CERTIFICATE_VERIFY_FAILED` error (after the `llm.py` fix above had
already landed) was confirmed to be a `.env` configuration gap, not a
code regression - the startup log showed `OPENAI_VERIFY_SSL=True` in the
actual running process.

You may also see this one-time, unrelated warning in the logs — it's
benign in this codebase and can be ignored:
```
WARNING: langchain-openai injected a custom httpx transport to apply `http_socket_options`, which disables httpx's proxy auto-detection ...
```
It fires because a corporate/system HTTP proxy is detected and
`langchain-openai` (>=1.5) wants to warn that its own *default* client
construction would otherwise silently stop respecting that proxy. It
doesn't apply here: `get_llm()` always passes its own explicit
`http_client`, so `langchain-openai`'s default-client-building path (the
one the warning is about) never actually runs — our client already
respects `HTTP_PROXY`/`HTTPS_PROXY` via `httpx`'s normal `trust_env`
behavior (the default, unchanged).

### D. Real DB connection fails or times out

```
sqlalchemy.exc.OperationalError: ... connection to server at "...neon.tech" ... port 5432 failed
```

Usually a network/firewall issue (some networks block or reset outbound
connections to non-HTTP ports), not an app bug. `GET /health/db` returns
a clean `503` rather than crashing the process either way — two ways to
keep working without a real DB connection:

- **Realistic fake data:** `python dev_fake_backend.py` (from `src/`) runs
  the real app with `database.dao.*` monkeypatched to in-memory data
  matching `01_business_requirements.md`'s example conversation (same
  numbers: Laptop as the top product, Stark Traders as the top Asia
  customer, etc.) — a real `OPENAI_API_KEY` is still required, only the
  database is faked. `DATABASE_URL` can be any placeholder string.
- **Minimal/no setup:** a fake `DATABASE_URL` alone is enough to exercise
  argument validation and error handling — every business tool call just
  returns a graceful `{"error": ...}` dict instead of real data (see
  `src/langchain_app/tools/README.md` for the pattern this repo's own
  tests use).

### E. The chatbot gives an answer that doesn't match the question, or repeats the same tool call every round

If backend logs show **identical token usage** across consecutive rounds
despite the conversation growing, a shared AI gateway with response
caching (e.g. a LiteLLM proxy) may be serving a cached response unrelated
to your actual request. `langchain_app/llm.py`'s `_GatewayChatOpenAI`
already sends a random `seed` on every call specifically to defeat this —
if you still see it, confirm nothing strips that field before the request
reaches the gateway.

### F. `OSError: [WinError 1114] ... c10.dll ...` (Windows)

Two different DLL-load-order conflicts can produce this exact error on
Windows, both fixed already in this repo — if you see it in new code you
add, the fix pattern is "load the thing that imports torch before the
thing that doesn't":

1. **torch vs. `onnxruntime`** — if you ever add a Chroma-backed or other
   `onnxruntime`-using component alongside `sentence-transformers`, import
   the torch-dependent module first. This repo avoids the conflict
   entirely by using FAISS instead of Chroma (no `onnxruntime` dependency
   at all).
2. **torch vs. SQLAlchemy's compiled Cython extensions** — discovered
   while wiring `langchain_app/tools/business_tools.py` (eagerly imports
   SQLAlchemy) and `retrieval_tool.py` (lazily imports torch via
   `sentence-transformers`, only when an embedding is actually computed)
   into the same process. If SQLAlchemy's `cyextension` modules load
   first, torch's own DLL init then fails. Fixed in
   `langchain_app/tools/__init__.py`, which forces the embedding model to
   load before Python can reach the `business_tools` submodule — see that
   file's docstring. If you add a new module that imports both
   `database.dao` and anything torch-based, make sure it imports through
   `langchain_app.tools` (or another module that already applies this
   guard) rather than importing `database.dao` completely independently
   first.

### G. Frontend doesn't reflect a code change

Streamlit reliably re-executes the *page* file (`frontend/pages/*.py`) on
save, but can be inconsistent about picking up edits to files those pages
*import* (`api_client.py`, `components/*.py`). If a fix doesn't seem to
apply:

1. Fully stop the Streamlit process (Ctrl+C) — don't rely on autoreload.
2. Restart: `streamlit run frontend/app.py`
3. Hard-refresh the browser tab (Ctrl+Shift+R).

### H. Testing without real LLM/DB credentials

You don't need a real OpenAI-compatible endpoint or database to verify
most of this codebase end-to-end:

- `langchain_core`'s `FakeMessagesListChatModel` (subclassed to add a
  no-op `bind_tools()`) can be scripted with canned `AIMessage` responses
  and swapped into `langchain_app.agent.build_agent_executor(llm=..., tools=...)`
  or `backend.services.chat_service._agent_executor` to drive the full
  tool-calling loop without a network call.
- A fake `DATABASE_URL` is enough to exercise every business tool's
  argument validation and error handling (`{"error": ...}` results) since
  SQLAlchemy engines are lazy — no connection is attempted until a query
  actually runs.
- The frontend can be driven headlessly with Streamlit's own
  `streamlit.testing.v1.AppTest` framework against a real (stubbed-LLM)
  backend started via `uvicorn.Server` in a background thread — see
  `src/frontend/README.md`'s Status section for what this repo verified
  that way.

This is how every phase of this repo was actually verified during
development — see each `src/` subfolder's `README.md` "Status" note for
what was tested and how.
