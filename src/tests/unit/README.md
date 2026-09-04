# Unit Tests

This directory contains isolated tests for the assistant's domain models,
DAO adapters, LangChain tools, agent orchestration, and service layer.

The tests are designed to run without:

- A PostgreSQL database
- OpenAI credentials
- A FAISS index
- Downloading an embedding model
- Network access

External boundaries are replaced with small fakes or `pytest`'s
`monkeypatch` fixture. Database tests verify DAO behavior with fake sessions;
they do not execute SQL against PostgreSQL.

## Running the Suite

From the repository root:

```powershell
cd src
python -m pytest tests/unit
```

With the Windows Python launcher:

```powershell
cd src
py -m pytest tests/unit -q
```

The current suite contains 37 tests. The collection setup in
[`../conftest.py`](../conftest.py) supplies placeholder configuration values
and prevents the application embedding model from loading during unit-test
collection.

## Test Modules

### `test_models.py`

Tests the `Message` and `Conversation` dataclasses:

- Default conversation state and timestamps
- Appending messages and updating timestamps
- Conversion to LangChain `HumanMessage` and `AIMessage` history
- Retrieval of the latest assistant tool results
- Empty history and empty tool-result behavior

### `test_database_layer.py`

Tests the database connection helper and representative DAO behavior with a
fake SQLAlchemy session:

- Decimal and date serialization in `serialize_row()`
- Product DAO parameter forwarding and result serialization
- Rejection of unsupported sales-trend periods
- Empty KPI result handling

SQL semantics and real PostgreSQL compatibility belong in integration tests.

### `test_business_tools.py`

Tests the 16 LangChain business-tool wrappers without calling a real DAO
connection:

- Limit validation for values from 1 through 100
- DAO argument forwarding
- Tool response shapes and counts
- Conversion of DAO exceptions to error dictionaries
- Unique tool names and complete business-tool registration

### `test_retrieval_tool.py`

Tests the knowledge-base retrieval adapter with fake retrievers and documents:

- Retriever creation with `k=3`
- Document formatting and metadata fallbacks
- Empty result responses
- Retrieval failure handling

FAISS behavior and embedding quality belong in integration or end-to-end
checks.

### `test_table_sources.py`

Tests database-source attribution used by the UI:

- Static mappings for business tools
- Empty mappings for RAG and unknown tools
- Dimension-specific mappings for profit analysis
- Stable, de-duplicated aggregation across tool steps

### `test_oos_guard.py`

Tests the hybrid out-of-scope guard using fake embeddings and LLM responses:

- In-scope intent with sufficient similarity
- Rejection caused by low similarity
- Rejection caused by out-of-scope intent
- Case normalization of classifier output
- Friendly rejection guidance
- Zero-vector cosine similarity
- Maximum similarity across reference questions

### `test_agent.py`

Tests `run_turn()` without constructing a real agent loop:

- Forwarding the question and prior chat history
- Extracting tool results and source tables
- Returning an out-of-scope response without invoking the executor
- Failing open when the OOS check raises an exception

### `test_chat_service.py`

Tests conversation orchestration with a fake executor:

- Persisting user and assistant messages
- Persisting tool results and source tables
- Passing prior turns to follow-up questions
- Resetting conversation state

Concurrency across real HTTP requests belongs in integration tests.

### `test_services.py`

Tests the insight and recommendation service adapters with a fake LLM:

- Guard response when no data has been retrieved
- Use of the latest tool result for insight generation
- Inclusion of the user question and tool data in the insight prompt
- Inclusion of insight text in the recommendation prompt
- Returning generated and empty response content

## Test Doubles

[`helpers.py`](helpers.py) contains the reusable test doubles:

- `FakeResponse`: minimal LLM response with a `content` field
- `FakeLlm`: records messages passed to `invoke()` and returns a fake response
- `FakeExecutor`: records agent payloads and returns a configured result

Keep these doubles small. If a test needs realistic database data or a real
HTTP application stack, place it under `integration/` instead of expanding
the unit-test fakes.
