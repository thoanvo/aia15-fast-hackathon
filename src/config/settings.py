"""Shared configuration/settings loader.

Centralizes environment variables used across database, backend, and
langchain_app layers (DATABASE_URL, OPENAI_*, VECTOR_STORE_*). Loads the
repo-root `.env` (copy `.env.example` there and fill in real values).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)



def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env (repo root) and fill it in."
        )
    return value


# --- Database ---
DATABASE_URL = _require("DATABASE_URL")

# --- OpenAI / gateway ---
OPENAI_API_KEY = _require("OPENAI_API_KEY")
# Optional: only needed if using an OpenAI-compatible proxy/gateway instead
# of https://api.openai.com/v1 directly.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# The shared workshop gateway ignores TLS verification; set to "false" only
# when actually pointed at that gateway (see langchain_app/llm.py).
OPENAI_VERIFY_SSL = os.getenv("OPENAI_VERIFY_SSL", "true").lower() != "false"

# --- Vector store (langchain_app/vectorstore) ---
# Default is an absolute path (independent of cwd, same reasoning as
# _ENV_PATH above) since the app is normally run with src/ as the working
# directory - a relative default here would otherwise resolve inconsistently
# depending on where the process was launched from.
_DEFAULT_VECTOR_STORE_DIR = Path(__file__).resolve().parent.parent / "langchain_app" / "vectorstore" / "index"
VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR") or str(_DEFAULT_VECTOR_STORE_DIR)
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

# --- Agent loop (langchain_app/agent.py) ---
# LangChain's AgentExecutor default (15) is too low for multi-tool-call
# turns (e.g. a filtering follow-up plus an insight reuse) and was getting
# hit on legitimate questions, returning the unhelpful "Agent stopped due
# to max iterations." instead of an answer.
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "30"))
AGENT_MAX_EXECUTION_TIME_SECONDS = float(os.getenv("AGENT_MAX_EXECUTION_TIME_SECONDS", "90"))

# --- Out-of-scope detection (langchain_app/oos_guard.py) ---
# See docs/03_functional_and_out_of_scope_requirements.md. The doc's
# recommended "0.70" threshold assumes a similarity scale that doesn't
# match this embedding model's typical cosine-similarity range for
# related-but-differently-worded sentences (empirically calibrated much
# lower here - see oos_guard.py's module docstring for the calibration
# data behind this default).
OOS_ENABLED = os.getenv("OOS_ENABLED", "true").lower() != "false"
OOS_SIMILARITY_THRESHOLD = float(os.getenv("OOS_SIMILARITY_THRESHOLD", "0.35"))
# Layer 0 (prompt-injection/jailbreak screen, oos_guard.classify_security())
# - an extra LLM call on every turn, so it's independently toggleable from
# OOS_ENABLED in case its latency/cost isn't worth it for a given deployment.
OOS_SECURITY_CHECK_ENABLED = os.getenv("OOS_SECURITY_CHECK_ENABLED", "true").lower() != "false"
# How far below OOS_SIMILARITY_THRESHOLD (or above it, when the LLM says
# OUT_OF_SCOPE) counts as "UNCERTAIN" rather than a confident reject - see
# oos_guard.py's module docstring. Untuned placeholder; narrow or widen
# once real traffic shows how often the gray zone is actually hit.
OOS_UNCERTAIN_MARGIN = float(os.getenv("OOS_UNCERTAIN_MARGIN", "0.10"))

# --- SQL agent (langchain_app/sql_validation.py, tools/sql_tools.py) ---
# Matches the existing fixed-tool cap (business_tools.py's _limited()) -
# consistent convention, not a new number invented for this feature.
SQL_AGENT_MAX_ROWS = int(os.getenv("SQL_AGENT_MAX_ROWS", "100"))
# How many run_sql_query attempts (including retries after an error) are
# allowed per turn before the tool tells the model to stop instead of
# retrying further - bounds the SQL path's share of AGENT_MAX_ITERATIONS.
SQL_AGENT_MAX_RETRIES = int(os.getenv("SQL_AGENT_MAX_RETRIES", "3"))

# A separate, SELECT-only Postgres role/connection string for the SQL
# agent's query-execution path (database/connection/readonly_pool.py) - a
# database-enforced boundary independent of application-level SQL
# validation. Falls back to DATABASE_URL (same privileges as the rest of
# the app) only for local dev when a separate role hasn't been provisioned
# yet - the SQL agent path should stay disabled in any environment relying
# on this fallback for anything beyond local development.
READONLY_DATABASE_URL = os.getenv("READONLY_DATABASE_URL") or DATABASE_URL

# Gates whether the fixed business tools (business_tools.py's 16
# entity-specific tools) are registered as agent tools. The dynamic-SQL
# tools (sql_db_schema/answer_with_sql, tools/sql_tools.py) are always
# registered regardless of this flag - see agent.get_tools(). Default
# true so existing deployments keep the fixed tools unless explicitly
# turned off.
#
# Note: run_sql_query/answer_with_sql executes through
# READONLY_DATABASE_URL above; if that hasn't been pointed at a real,
# dedicated read-only Postgres role, generated SQL runs with the same
# full-privilege connection as the rest of the app, relying on
# application-level validation (sql_validation.py) alone - independent
# of this flag.
#
# Exposed as a function (not a plain module-level constant) so it can be
# flipped at runtime via the frontend's demo toggle (backend.controllers.
# settings_controller) without a process restart - a plain `from
# config.settings import FIXED_TOOLS_ENABLED` would bind a frozen copy of
# the value at import time in every consumer, so callers must call
# `is_fixed_tools_enabled()` fresh each time instead.
_fixed_tools_enabled = os.getenv("FIXED_TOOLS_ENABLED", "true").lower() == "true"


def is_fixed_tools_enabled() -> bool:
    return _fixed_tools_enabled


def set_fixed_tools_enabled(value: bool) -> None:
    global _fixed_tools_enabled
    _fixed_tools_enabled = value

# How many business-context chunks (embedding/ docs) to retrieve per
# question for the SQL-generation prompt (langchain_app/sql_context.py) -
# same retrieval mechanism/index as search_knowledge_base, just a
# different consumer, so this is independently tunable from
# retrieval_tool.py's own fixed k=3.
SQL_CONTEXT_RETRIEVAL_K = int(os.getenv("SQL_CONTEXT_RETRIEVAL_K", "4"))

# --- Frontend only (frontend/api_client.py) ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
