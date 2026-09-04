"""Collection-time setup shared by isolated unit tests."""

import os


# Application settings validate these values at import time. Unit tests use
# placeholders and monkeypatch the external boundaries they exercise.
os.environ.setdefault("DATABASE_URL", "postgresql://unit:unit@localhost/unit")
os.environ.setdefault("OPENAI_API_KEY", "unit-test-key")


# Importing langchain_app.tools normally forces the sentence-transformers
# model to load first for Windows DLL ordering. Unit tests do not exercise
# the embedding model, so prevent that heavyweight startup during collection.
from langchain_app.vectorstore import embeddings as embeddings_module

embeddings_module.get_embeddings = lambda: None