# FAST Team - Database Query Assistant — Hackathon (LangChain-native, greenfield)

An AI-powered chatbot that lets business users query and analyze company
data (products, customers, sales, regions) using natural language instead
of SQL — same business domain as Workshop 2/3, rebuilt with a LangChain
tool-calling agent (business tools + RAG retrieval over a FAISS vector
store) instead of a hand-rolled OpenAI function-calling loop.

Full background: [`docs/01_business_requirements.md`](docs/01_business_requirements.md).
Architecture + phase-by-phase build plan:
[`docs/04_solution_design.md`](docs/04_solution_design.md).
Project structure reference: [`docs/08_project_structure.md`](docs/08_project_structure.md).
Full developer setup + troubleshooting: [`docs/09_environment_setup_guide.md`](docs/09_environment_setup_guide.md).
API reference: [`docs/11_api_documentation.md`](docs/11_api_documentation.md).
Database schema: [`docs/07_database_schema_reference.md`](docs/07_database_schema_reference.md).

## Technical stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| AI / agent | [LangChain](https://python.langchain.com/) tool-calling agent (`create_tool_calling_agent` + `AgentExecutor`) over `ChatOpenAI` (`gpt-4o-mini` by default, configurable) |
| Vector store / RAG | [FAISS](https://github.com/facebookresearch/faiss) (`langchain-community`, in-process) + `sentence-transformers` embeddings |
| Database | PostgreSQL ([Neon](https://neon.tech/)) via [SQLAlchemy](https://www.sqlalchemy.org/) + `psycopg2` |
| Frontend | [Streamlit](https://streamlit.io/) (`st.navigation`/`st.Page` multipage app) |
| Frontend ↔ backend | [`requests`](https://requests.readthedocs.io/) (plain HTTP/JSON) |
| Config | [`python-dotenv`](https://github.com/theskumar/python-dotenv) |
| Data validation (API) | [Pydantic](https://docs.pydantic.dev/) (via FastAPI) |
| Testing | [pytest](https://pytest.org/) |

## Repository layout

```
docs/     - business description, architecture decisions, phase-by-phase plan
src/      - the application — see docs/08_project_structure.md for the full breakdown
```

See [`docs/08_project_structure.md`](docs/08_project_structure.md) for what lives
in each `src/` subfolder (config → database → langchain_app → backend →
frontend), and each subfolder's own `README.md` for its current
implementation status.

## Prerequisites

- Python 3.11+
- A PostgreSQL (Neon) database and its connection string
- An OpenAI API key (or an OpenAI-compatible proxy/gateway) with access to a
  chat-completion model (e.g. `gpt-4o-mini`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy the environment template and fill in your real values:

```bash
cp .env.example .env
# then edit .env: DATABASE_URL, OPENAI_API_KEY, OPENAI_BASE_URL (optional),
# OPENAI_MODEL, VECTOR_STORE_DIR, EMBEDDING_MODEL_NAME, and (frontend only) BACKEND_URL
```

## Initialize the database

Creates the schema (`products`, `customers`, `sales`, `regions`) and loads
sample data (see `src/database/README.md`). Run from `src/` (all app code
runs with `src/` as the working directory, `pip install -r requirements.txt`
at the repo root having already put everything on `sys.path` via `src`
itself being cwd):

```bash
cd src
python database/scripts/init_db.py
```

## Run the app

Two processes, both from `src/`:

```bash
# Terminal 1 - backend API (port 8000)
cd src
uvicorn app:app --host 127.0.0.1 --port 8000

# OR, without a real DB connection (real OPENAI_API_KEY still required):
python dev_fake_backend.py

# Terminal 2 - Streamlit UI (port 8501)
cd src
streamlit run frontend/app.py --server.port 8501
```

Open the Streamlit URL it prints (defaults to `http://localhost:8501`) and
try the example conversation from the business description:

1. "What are the top 5 products by revenue?"
2. "Only in Asia."
3. "What insights can you provide?"

## Test cases

Manual/smoke test cases covering the main flows — all verified during
development against a stubbed LLM (a scripted fake chat model) plus, for
TC-01/02, a fake `DATABASE_URL` (see `docs/09_environment_setup_guide.md` §Troubleshooting H
for why that's enough to exercise most of the stack without real
credentials). Run the backend and frontend (see above), then walk through
these — either through the Streamlit UI or directly against the API
(`curl` / `http://127.0.0.1:8000/docs`). See
[`02_test_cases_database_query_assistant.md`](02_test_cases_database_query_assistant.md)
