# Database Entity-Relationship Diagram

Source: `src/database/scripts/schema.sql`

## Overview

Star-schema style layout: `sales` is the fact table, `regions` / `products` / `customers` are dimension tables. `customers.region_id` also links each customer to a home region.

```
+------------------+                            +------------------+
|     REGIONS      |------ located in --------->|     CUSTOMERS    |
+------------------+                            +------------------+
| PK region_id     |                            | PK customer_id   |
|    region_name   |                            |    customer_name |
|    country       |                            |    segment       |
+------------------+                            | FK region_id     |
        |                                       +------------------+
        |                                                |
        | sold in                                        | makes
        |                                                |
        |                 +------------------+           |
        +---------------->|       SALES      |<----------+
                           +------------------+
                           | PK sale_id       |
                           | FK product_id    |
                           | FK customer_id    |
                           | FK region_id     |
                           |    sale_date     |
                           |    quantity      |
                           |    unit_price    |
                           |    unit_cost     |
                           |    revenue (gen) |
                           |    profit  (gen) |
                           +------------------+
                                    ^
                                    |
                                 sold as
                                    |
                           +------------------+
                           |     PRODUCTS     |
                           +------------------+
                           | PK product_id    |
                           |    product_name  |
                           |    category      |
                           |    unit_cost     |
                           |    unit_price    |
                           +------------------+
```

## Notes

- `sales.revenue` and `sales.profit` are `GENERATED ALWAYS` columns (`quantity * unit_price`, `quantity * (unit_price - unit_cost)`) — not stored independently, always derived.
- Every FK on `sales` (`product_id`, `customer_id`, `region_id`) has a supporting index, plus `sale_date`, since these are the join/filter columns used by the DAO query layer (`src/database/dao/*.py`).
- `customers.region_id` is a separate relationship from `sales.region_id` — a sale's region is not guaranteed to equal the customer's home region in the data model (no constraint enforces it).

## LangChain agent prompt flow → tables

How a question travels from the LangChain agent's prompt
(`src/langchain_app/prompts.py`) down to these tables and back, for one
chat turn plus the insight/recommendation follow-ons. (See
[`05_system_architecture.md`](05_system_architecture.md) for the full layered
view, including where `retrieval_tool`/FAISS fits in.)

```
User
  |
  | 1) question: "Top 5 products by revenue in Asia?"
  v
chat_service ------------------------------------------------+
  |                                                           |
  | 2) history + system prompt (ChatPromptTemplate)           |
  v                                                           |
AgentExecutor (langchain_app.agent) -> ChatOpenAI              |
  |                                                           |
  | 3) tool call: get_top_products(limit=5, region="Asia")    |
  v                                                           |
AgentExecutor                                                  |
  |                                                           |
  | 4) invoke StructuredTool                                   |
  v                                                           |
tools.business_tools                                           |
  |                                                           |
  | 5) get_top_products(...)                                  |
  v                                                           |
database.dao                                                  |
  |                                                           |
  | 6) SELECT ... JOIN sales, products, regions                |
  v                                                           |
Database tables                                                |
  |                                                           |
  | 7) rows                                                    |
  v                                                           |
database.dao --8) rows--> tools.business_tools                 |
                             |                                 |
                             | 9) tool result (intermediate_steps)
                             v                                 |
                           AgentExecutor <----------------------+
  |
  | 10) history + tool result
  v
ChatOpenAI
  |
  | 11) final answer (plain text) + table_sources.get_source_tables(intermediate_steps)
  v
chat_service
  |
  | 12) answer + source_tables
  v
User

----------------------------------------------------------------
opt  User asks: "What insights can you provide?"
----------------------------------------------------------------
insight_service --13) insight prompt(last tool name + result)--> ChatOpenAI (langchain_app.llm.get_llm())
ChatOpenAI --14) "Key Insights: ..."--> insight_service --15) insights--> User

----------------------------------------------------------------
opt  User asks: "What should we do?"
----------------------------------------------------------------
recommendation_service --16) recommendation prompt(prior insights)--> ChatOpenAI (langchain_app.llm.get_llm())
ChatOpenAI --17) "Recommendations / Action Items"--> recommendation_service --18) recommendations--> User
```

Notes on this flow:

- `langchain_app/prompts.py` teaches the model which of the registered
  `StructuredTool`s maps to which table(s) (e.g. `get_top_products` →
  `sales` joined with `products`/`regions`) via few-shot examples — no
  query is ever hand-written by the model, only a tool name + structured
  args. The same agent also has a `retrieval_tool` over the FAISS store for
  schema/SQL knowledge-base questions, callable in the same turn.
- `insight_service` / `recommendation_service` never touch the database
  directly — they reason over the **already-fetched** rows stored on the
  conversation (`Conversation.last_function_calls()`), so a table is
  queried at most once per user question.
- Follow-up filtering ("Only in Asia.") is resolved by the model reusing
  the same tool against the same tables with an added argument — not a new
  tool or a new table.
- `table_sources.get_source_tables()` maps each tool name in
  `intermediate_steps` back to the table(s) it queried, for the `source_tables`
  UI attribution surfaced by `response_display.py`.
