# FAST Team - Database Query Assistant
## Comprehensive Business Description

---

## Executive Summary

The Database Query Assistant is an AI-powered conversational analytics application that enables business users to ask questions about products, customers, sales, and regions in natural language. The solution combines a LangChain tool-calling agent — business-data tools plus a FAISS-backed RAG retrieval tool over a schema/SQL knowledge base — with a PostgreSQL-backed data layer, so users can retrieve answers, continue multi-turn conversations, ask schema/SQL background questions, and receive business insights without writing SQL.

This is the Hackathon (greenfield, LangChain-native) implementation: the same business domain and core business functions as the original Workshop 2/3 build, rebuilt around a single unified LangChain agent instead of a hand-rolled OpenAI function-calling loop. In the current workspace, the implementation is organized as a layered application under the `src` directory, with a FastAPI backend, a Streamlit frontend, DAO-based database access, and a `langchain_app` package holding the entire AI/tool-calling/RAG core (see [`08_project_structure.md`](08_project_structure.md)).

---

## Table of Contents

1. [Project Information](#project-information)
2. [Business Background](#business-background)
3. [Problem Statement](#problem-statement)
4. [Proposed Solution](#proposed-solution)
5. [Target Users](#target-users)
6. [Scope and Assumptions](#scope-and-assumptions)
7. [Project Goals](#project-goals)
8. [System Architecture](#system-architecture)
9. [Technical Architecture](#technical-architecture)
10. [Project Structure](#project-structure)
11. [Core Business Functions](#core-business-functions)
12. [Example Conversation](#example-conversation)
13. [Deliverables](#deliverables)
14. [Success Criteria](#success-criteria)
15. [Success Metrics](#success-metrics)
16. [Risks and Mitigations](#risks-and-mitigations)
17. [Future Enhancements](#future-enhancements)

---

## Project Information

### Project Name

**Database Query Assistant**

### Team Objective

Build an AI-powered chatbot that enables users to query and analyze business data using natural language instead of SQL.

The solution leverages:

- LangChain (`create_tool_calling_agent` + `AgentExecutor`) over an OpenAI-compatible chat model
- Retrieval-Augmented Generation (RAG) via a FAISS vector store + `sentence-transformers` embeddings
- Business-data tools (16 `@tool`-wrapped functions) + a knowledge-base retrieval tool, in one unified agent
- A dynamic, embedding-grounded SQL-generation path (LangGraph state machine) for questions no fixed tool covers
- Hybrid out-of-scope (OOS) detection in front of the agent
- Multi-turn Conversations
- Context Management
- Prompt Engineering
- PostgreSQL (Neon)

### Workshop Reference

Hackathon: RAG + LangChain-native rebuild of the Database Query Assistant.
Same business domain as Workshop 2 (Building Chatbot Systems Using Azure
OpenAI API) and its Workshop 3 additive iteration — this build replaces
the hand-rolled OpenAI function-calling loop with a LangChain agent and
adds RAG retrieval, per Workshop 2's own "Future Enhancements > Phase 2"
scope (see [`04_solution_design.md`](04_solution_design.md) for the full
rationale).

---

## Business Background

Organizations store large amounts of business data in databases, ERP systems, CRM systems, Excel files, and reporting tools.

Although valuable information exists within these data sources, business users often struggle to access it because:

- They do not know SQL
- They are unfamiliar with database structures
- They rely heavily on Developers or Data Analysts
- Report requests take significant time to complete
- Existing dashboards only answer predefined questions

As a result, decision-making is delayed and data is underutilized.

### Current State Challenges

- **Technical Barrier**: Most business users lack SQL expertise
- **Dependency**: Heavy reliance on technical teams creates bottlenecks
- **Time Delay**: Reporting requests can take days or weeks to fulfill
- **Limited Insights**: Static dashboards cannot answer ad-hoc questions
- **Underutilized Data**: Valuable data assets remain unexploited

---

## Problem Statement

Business users need quick access to data-driven insights but often lack the technical skills required to retrieve and analyze data from databases.

### Key Challenges

| Challenge | Impact |
|-----------|--------|
| Limited SQL knowledge | Users cannot self-serve data queries |
| Dependence on technical teams | Slow turnaround time for insights |
| Slow turnaround for reporting requests | Delayed decision-making |
| Difficulty discovering business insights | Missed opportunities |
| Lack of self-service analytics capabilities | Inefficient resource utilization |

---

## Proposed Solution

Develop an AI-powered chatbot that allows users to ask business questions in natural language.

### Solution Capabilities

The chatbot will:

1. **Understand user intent** - Analyze natural language questions
2. **Identify required business function** - Map questions to data queries
3. **Execute data queries** - Query PostgreSQL (Neon) database
4. **Analyze retrieved data** - Process and interpret results
5. **Generate business insights** - Extract meaningful patterns
6. **Provide recommendations** - Suggest actionable next steps
7. **Maintain conversation context** - Support multi-turn dialogues

### Key Benefits

- **Democratizes data access** - No SQL knowledge required
- **Improves decision speed** - Instant access to insights
- **Reduces technical dependency** - Enables self-service analytics
- **Enhances data utilization** - Uncovers hidden insights
- **Increases user productivity** - Faster information retrieval

---

## Target Users

The solution targets the following user personas:

- **Business Analysts** - Need to analyze data trends and patterns
- **Sales Team** - Require quick access to sales metrics and forecasts
- **Operations Team** - Monitor operational performance and KPIs
- **Project Managers** - Track project metrics and timelines
- **Management Team** - Need executive summaries and insights
- **Product Owners** - Analyze product performance and user behavior

---

## Scope and Assumptions

### In Scope

- Natural-language questions about products, customers, sales, regions, and KPIs
- Multi-turn conversations with context retention
- Function calling to route requests to business-specific handlers
- Business insights and recommendations based on retrieved data
- REST API access and a Streamlit-based web interface

### Out of Scope

- Full enterprise BI platform functionality
- Complex forecasting or predictive modeling
- Advanced role-based access control
- Real-time streaming analytics

### Assumptions

- Source data is available in PostgreSQL (Neon) and can be queried through SQLAlchemy-based DAOs
- Environment configuration is provided through a local .env file
- The initial release focuses on a defined set of core business functions for workshop/demo purposes
- The solution is intended to be demo-ready rather than a full-scale enterprise deployment

### User Journey

1. A user enters a question such as “What are the top 5 products by revenue?”
2. The system interprets the request and selects the relevant business function
3. The function retrieves data from the database and returns structured results
4. The assistant presents an answer and, when appropriate, generates insights and recommendations
5. The user can ask follow-up questions that build on the previous context

---

## Project Goals

### Primary Goals

- **Democratize data access** - Enable non-technical users to query databases
- **Reduce dependency on SQL knowledge** - Eliminate technical barriers
- **Enable self-service analytics** - Empower users to find their own insights
- **Improve decision-making speed** - Provide instant access to data
- **Demonstrate a LangChain-native RAG/agent architecture** - Using LangChain best practices over any OpenAI-compatible endpoint

### Workshop Goals

Implement and demonstrate:

- LangChain tool-calling agent (`create_tool_calling_agent` + `AgentExecutor`)
- Retrieval-Augmented Generation (RAG) via a FAISS vector store
- Tool calling mechanisms (16 business tools + 1 retrieval tool)
- Multi-turn Chatbot architecture
- Conversation Memory Management
- Few-shot Prompting techniques
- Chain-of-Thought Prompting strategies (insight/recommendation generation)
- Batching operations (multiple tool calls in one agent round)
- PostgreSQL Integration

---

## System Architecture

### High-Level Flow

```
User
  ↓
Web UI (Streamlit)
  ↓
Controller Layer (Request Routing)
  ↓
Chat Service (conversation store + locking)
  ↓
LangChain Agent (AgentExecutor: ChatOpenAI + tool-calling loop)
  ↓
Business Tools (16 @tool functions)  +  RAG Retrieval Tool (FAISS)
  ↓
DAO Layer (Data Access)              +  Knowledge-base docs (embedding/)
  ↓
Neon PostgreSQL (Database)
  ↓
Response Generation (Answer + source_tables attribution)
  ↓
Business Insight (Pattern Analysis, reuses last tool result)
  ↓
Recommendation (Actionable Suggestions)
  ↓
User (Final Response)
```

See [`05_system_architecture.md`](05_system_architecture.md) for the full
layered diagram and [`06_database_design.md`](06_database_design.md) for
the agent/tool request-flow diagram for one chat turn.

### Architecture Principles

- **Separation of Concerns** - Distinct layers with specific responsibilities
- **Scalability** - Design for growing user base and data volume
- **Maintainability** - Clean code structure for future enhancements
- **Reliability** - Error handling and data validation
- **Security** - Secure database connections and data protection

---

## Technical Architecture

### Technology Stack

- **Backend API:** FastAPI with Uvicorn
- **Frontend UI:** Streamlit
- **AI / Agent:** LangChain (`langchain-classic`'s `create_tool_calling_agent` + `AgentExecutor`) over `ChatOpenAI` (`langchain-openai`), any OpenAI-compatible endpoint
- **RAG / Vector store:** FAISS (`langchain-community`, in-process) + `sentence-transformers` embeddings, no external vector DB service — shared by the RAG retrieval tool and the dynamic-SQL generation path
- **Dynamic SQL generation:** LangGraph (`langgraph`) state machine (`sql_graph.py`) + `sqlparse`-backed validation, always registered on the agent (`FIXED_TOOLS_ENABLED` instead gates the 16 fixed business tools — see below)
- **Database access:** SQLAlchemy with PostgreSQL / Neon connectivity (a second, restricted read-only role for the dynamic-SQL path's execution step)
- **Validation and models:** Pydantic
- **Configuration:** python-dotenv
- **Testing:** pytest (planned, see [`10_implementation_guide.md`](10_implementation_guide.md) Phase 7 — currently verified with ad-hoc scripts, not yet a committed suite)

### Frontend Layer

#### Web UI

**Responsibilities:**
- Accept user questions in natural language
- Display chatbot responses in user-friendly format
- Display business insights and recommendations
- Manage conversation history and context
- Provide visual representation of data


**Key Features:**
- Conversational interface
- Response streaming
- Historical conversation view
- Insight visualization

---

### Backend Layer

#### Controller Layer

**Responsibilities:**
- Process incoming API requests
- Route requests to appropriate services
- Handle request validation
- Return formatted responses
- Manage API versioning


**Key Features:**
- RESTful API endpoints
- Request/response formatting
- Error handling
- Rate limiting

#### Service Layer

**Responsibilities:**
- Implement business logic
- Delegate each chat turn to the LangChain agent
- Handle multi-turn conversations (conversation store + per-conversation locking)
- Generate business insights
- Create recommendations


**Key Features:**
- Conversation state management (`backend/models/conversation.py`)
- Insight generation reusing the last tool result (no repeat tool call)
- Recommendation engine

#### AI Layer (`langchain_app/`)

**Responsibilities:**
- LangChain agent construction (`create_tool_calling_agent` + `AgentExecutor`)
- `ChatOpenAI` factory: gateway `base_url`/`http_client` compat + per-call random `seed` override (defeats shared-gateway response caching)
- Hybrid out-of-scope detection (`oos_guard.py`) runs before the agent — a rejected question never reaches a tool call or the database
- Prompt template: scope rules, refusal behavior, few-shot examples, tool-routing rules for when to use a fixed business tool vs. the dynamic-SQL tool
- Tool-calling loop: business tools + RAG retrieval tool + dynamic-SQL tools, in one unified agent
- Dynamic SQL generation (`sql_graph.py`'s LangGraph state machine): per-question schema reflection + FAISS retrieval → generate → validate → execute, with bounded retry
- `source_tables` attribution: mapping each tool call back to the DB table(s) it read (the dynamic-SQL tool derives this from its executed query)
- Deterministic chart-worthiness extraction (`chart_data.py`) over a turn's tool results, for the frontend's show/hide chart toggle


**Key Features:**
- Single `get_llm()` factory used everywhere an LLM call is needed
- `StructuredTool`/`@tool`-wrapped business functions (16), each gracefully returning `{"error": ...}` instead of crashing the turn
- FAISS-backed retrieval tool over a schema/SQL knowledge base — the same index also grounds dynamic-SQL generation
- A `SELECT`-only, single-statement, `LIMIT`-capped safety gate (`sql_validation.py`) before any generated SQL executes, plus a separate restricted read-only DB role for execution
- Per-temperature LLM instance caching

---

### Database Layer

#### PostgreSQL (Neon)

**Responsibilities:**
- Store business data (products, customers, sales, regions)
- Execute analytical queries
- Support multi-table joins
- Provide data consistency
- Enable backup and recovery


**Key Features:**
- Optimized indexes for analytical queries
- Query performance monitoring
- Data integrity constraints
- Connection pooling
- Transaction management

**Database Schema:**
- Products table (product details)
- Customers table (customer information)
- Sales table (transaction records)
- Regions table (geographic data)
- Supporting lookup tables

---

## Project Structure

See [`08_project_structure.md`](08_project_structure.md) for the current,
authoritative project structure and layering rule (single source of
truth — not duplicated here).

---

## Core Business Functions

In the current implementation these are exposed to the LangChain agent as
`@tool`-decorated functions (`langchain_app/tools/business_tools.py`), not
a hand-rolled function-calling registry — same 16 functions, same
signatures, different wrapping mechanism. A 17th tool,
`search_knowledge_base` (RAG retrieval over `embedding/` docs), sits
alongside them in the same agent for schema/SQL background questions and
isn't listed below since it isn't a business-data function.

Two more tools, always registered on the agent (not gated by a feature
flag), handle questions no fixed business tool's shape covers — e.g. a
plain "list all X" with no ranking implied, or a join no fixed tool
anticipated: `sql_db_schema` (on-demand column lookup) and
`answer_with_sql` (takes the user's question in natural language, runs a
LangGraph generate → validate → execute pipeline grounded in schema
reflection + embedding retrieval, returns rows). The 16 fixed business
tools below are themselves gated behind `FIXED_TOOLS_ENABLED` (default
`true`) — when off, only the two dynamic-SQL tools plus
`search_knowledge_base` are registered. See
[`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md)
for the full design.

Two functions in the table below aren't implemented as separate callable
functions: `resolve_follow_up_question()` is handled implicitly by the
agent reusing `chat_history` (no dedicated function), and
`generate_executive_summary()` isn't implemented at all yet.

### Data Retrieval Functions

| Function | Description | Use Case |
|----------|-------------|----------|
| `get_top_products()` | Retrieve top products by revenue | "What are our best-selling products?" |
| `get_top_customers()` | Retrieve top customers by revenue | "Who are our biggest customers?" |
| `get_region_performance()` | Analyze business performance by region | "How is each region performing?" |
| `get_sales_trend()` | Analyze sales trends over time | "What is our sales trend?" |
| `get_profit_analysis()` | Analyze profit performance by various dimensions | "What is our profit analysis?" |
| `get_summary_kpi()` | Generate KPI summary (revenue, profit, margin) | "What are our key metrics?" |
| `get_top_products_by_quantity()` | Retrieve products ranked by units sold | "Which products sell the most units?" |
| `get_top_products_by_profit()` | Retrieve products ranked by total profit | "Which products are most profitable?" |
| `get_category_performance()` | Analyze revenue and profit by category | "How are our product categories performing?" |
| `get_segment_performance()` | Analyze revenue and profit by customer segment | "Which customer segment generates the most revenue?" |
| `get_product_region_performance()` | Compare product performance across regions | "Where does the Laptop perform best?" |
| `get_customer_purchase_history()` | Retrieve a customer's purchase history | "What has Acme Corp purchased?" |
| `get_low_margin_products()` | Find products with the lowest profit margins | "Which products have weak margins?" |
| `get_sales_by_date_range()` | Summarize sales within a required date range | "How much did we sell in Q1?" |
| `get_month_over_month_growth()` | Calculate monthly revenue growth | "How is revenue growing month over month?" |
| `get_repeat_customer_summary()` | Summarize repeat customers by region | "Which regions have repeat customers?" |

### Insight & Recommendation Functions

| Function | Description | Output |
|----------|-------------|--------|
| `generate_business_insight()` | Generate business insights from data patterns | Actionable insights and observations |
| `generate_recommendation()` | Generate business recommendations | Strategic recommendations |
| `resolve_follow_up_question()` | Handle follow-up questions with context | Contextual answers |
| `generate_executive_summary()` | Generate executive summary report | High-level business summary |

### Function Implementation

Each function will:
- Accept user parameters (filters, dimensions)
- Validate input parameters
- Execute database queries
- Format results
- Handle errors gracefully
- Return structured responses

---

## Example Conversation

### User Query 1: Initial Question

```
What are the top 5 products by revenue?
```

### Assistant Response 1

```
Based on the current data, here are the top 5 products by revenue:

1. Laptop ($2,450,000 - 28% of total revenue)
2. Printer ($1,890,000 - 21% of total revenue)
3. Monitor ($1,567,000 - 18% of total revenue)
4. Scanner ($1,234,000 - 14% of total revenue)
5. Camera ($987,000 - 11% of total revenue)

These five products represent 92% of total revenue.
```

### User Query 2: Filtering Follow-up

```
Only in Asia.
```

### Assistant Response 2

```
In the Asia region specifically, the top products by revenue are:

1. Laptop ($1,102,500 - 45% of Asia revenue)
2. Printer ($650,000 - 27% of Asia revenue)
3. Monitor ($450,000 - 18% of Asia revenue)

These three products account for 90% of Asia regional revenue.
```

### User Query 3: Request for Insights

```
What insights can you provide?
```

### Assistant Response 3

```
Based on the analysis, here are key insights:

**Key Insights:**
- Laptop dominates Asia revenue, contributing approximately 45% of the region's total
- Concentration Risk: Three products account for 90% of Asia revenue
- Growth Opportunity: Asia region shows strong Laptop demand

**Recommendations:**
1. Increase Laptop inventory levels in Asia to meet demand
2. Expand marketing investment for Laptop products in Asia
3. Develop complementary products (accessories) for Laptop buyers
4. Monitor competition in the Laptop segment

**Action Items:**
- Review inventory forecasts for Q3-Q4
- Allocate additional marketing budget to Asia region
- Develop targeted campaigns for Laptop products
```

---

## Deliverables

Status reflects the actual current state of this repo (Phases 0-6 and 8
of [`10_implementation_guide.md`](10_implementation_guide.md); see
[`04_solution_design.md`](04_solution_design.md) for the full phase list).

### Development Deliverables

- ✅ Web UI with conversational interface (Streamlit)
- ✅ LangChain agent with `ChatOpenAI` integration (gateway-compatible, per-call seed override)
- ✅ Business tools (16 `@tool` functions) + RAG retrieval tool, in one unified agent
- ✅ FAISS vector store / RAG retrieval over a schema/SQL knowledge base
- ✅ Multi-turn Conversation management (`chat_history`, per-conversation locking)
- ✅ PostgreSQL (Neon) Integration with connection pooling
- ✅ Business Functions implementation (16 core functions + retrieval tool)
- ✅ Graceful error handling (bad args / DB errors return `{"error": ...}`, never crash a turn)
- ✅ `source_tables` UI attribution (which DB table an answer came from)
- ✅ Conversation context management
- ✅ Hybrid out-of-scope (OOS) detection in front of the agent (`oos_guard.py`)
- ✅ Dynamic, embedding-grounded SQL generation (LangGraph state machine, always registered on the agent — `FIXED_TOOLS_ENABLED` gates the fixed business tools instead)
- ✅ Deterministic chart-data extraction + a show/hide chart toggle in the UI

### Testing Deliverables

- 🟡 Verified with ad-hoc scripts throughout development (scripted fake chat model, `TestClient`, Streamlit `AppTest`) — not yet a committed `pytest` suite (Phase 7, open)
- ⬜ Unit Test Cases (controller, service, DAO layers) — planned, not yet committed
- ⬜ Integration Testing — planned, not yet committed
- ⬜ End-to-End Testing — planned, not yet committed
- ⬜ Retrieval accuracy / response quality / performance / UAT — needs real LLM credentials (see Future Enhancements below)

### Documentation Deliverables

- ✅ README with setup instructions
- ✅ Business Description (this document)
- ✅ Technical/System Architecture (`05_system_architecture.md`, `06_database_design.md`)
- ✅ API Documentation (`11_api_documentation.md`)
- ✅ Database Schema Documentation (`07_database_schema_reference.md`)
- ✅ Setup Guide incl. troubleshooting (`09_environment_setup_guide.md`)
- ⬜ User Stories / Use Cases as a dedicated document — planned, see Future Enhancements
- ⬜ Deployment Guide — not started, optional (see Future Enhancements)

### Presentation Deliverables

- ✅ Presentation outline/template ready to fill in (20 slides — see Future Enhancements below)
- ⬜ Project Overview / Architecture walkthrough content — not yet filled into the deck
- ⬜ Live demonstration / screenshots — needs real LLM credentials or an agreed stubbed-backend demo
- ⬜ Lessons learned discussion — content exists in this repo's docs, not yet assembled into the deck
- ⬜ Q&A session — N/A until presented

---

## Success Criteria

The project will be considered **successful** if the following criteria are met:

### Functional Success Criteria

- ✅ **Natural Language Processing**: Users can ask questions in plain English/Vietnamese
- ✅ **Tool Calling**: The LangChain agent selects and calls the correct business tool (or the RAG retrieval tool) with correct arguments
- ✅ **Data Retrieval**: Data is accurately retrieved from PostgreSQL (Neon) database
- ✅ **Multi-turn Conversation**: System maintains context across multiple user turns
- ✅ **Business Insights**: System generates meaningful business insights from data
- ✅ **Recommendations**: System provides actionable recommendations
- ✅ **End-to-End Flow**: Complete chatbot flow works seamlessly from user input to insight generation

### Quality Success Criteria

- ✅ **Accuracy**: Data results are accurate and validated
- ✅ **Relevance**: Responses are relevant to user queries
- ✅ **Clarity**: Insights and recommendations are clear and understandable
- ✅ **Performance**: Response times are acceptable (<3 seconds)
- ✅ **Reliability**: System handles errors gracefully

### Business Success Criteria

- ✅ **User Adoption**: Users can use the system without extensive training
- ✅ **Self-Service**: Business users can independently query data
- ✅ **Time Reduction**: Significant reduction in time to access insights
- ✅ **Value Delivery**: System delivers measurable business value

---

## Success Metrics

The solution should be considered successful when the following outcomes are observed:

- Users can ask questions in natural language and receive a relevant answer without writing SQL
- Follow-up questions are handled correctly using conversation context
- Core business functions return accurate results from the PostgreSQL-backed data layer
- Insight and recommendation generation adds value beyond raw query results
- The end-to-end flow works reliably through the API and the Streamlit UI
- Response times remain acceptable for a workshop/demo scenario

---

## Risks and Mitigations

### Potential Risks

- The model may misinterpret a user’s intent or select the wrong function
- Database schema or data quality issues may reduce answer accuracy
- Context window limitations may affect multi-turn conversations
- External API failures may interrupt the experience

### Mitigations

- Use LangChain tool calling with structured arguments and parameter validation to constrain model behavior
- Validate query results and handle errors gracefully
- Maintain conversation state in a controlled way and truncate history when needed
- Provide fallback messages and logging for API or database issues

---

## Future Enhancements

### Phase 2 (RAG + LangChain) — complete

Workshop 2's own "Future Enhancements > Phase 2" section originally listed
this as forward-looking work; Hackathon (this repo) has now built it:

- ✅ **RAG (Retrieval-Augmented Generation)** — a `search_knowledge_base`
  tool alongside the business tools, in the same agent
- ✅ **Vector Database Integration** — FAISS (in-process, no external service)
- ✅ **Embeddings** — `sentence-transformers` via `HuggingFaceEmbeddings`
- ✅ **LangChain Integration** — `create_tool_calling_agent` + `AgentExecutor`
  replace the hand-rolled OpenAI function-calling loop
- ✅ **Text-to-SQL Generation** — revisited and now implemented, safely:
  the *outer* tool-calling model still never writes SQL directly as a
  tool argument; `answer_with_sql` takes the user's question in natural
  language and a dedicated internal LLM call (`sql_graph.py`) generates
  SQL grounded in schema reflection + embedding retrieval, gated by a
  deterministic `SELECT`-only/`LIMIT`-capped validator and a restricted
  read-only DB role before anything executes — see
  [`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md)
- ✅ **LangGraph Support** — implemented for the dynamic-SQL path
  specifically: `discover_schema → generate_sql → validate_sql →
  execute_sql`, with a bounded retry that feeds the failing error back
  into the next generation attempt. The main business-tool-calling loop
  stays a single `AgentExecutor`, unchanged — LangGraph was adopted only
  where an explicit, retryable multi-step pipeline was the better fit

---

## Conclusion

The **Database Query Assistant** demonstrates how a LangChain tool-calling
agent — business-data tools plus RAG retrieval, all through one
OpenAI-compatible chat model — can be effectively integrated with
PostgreSQL databases to provide intelligent, source-attributed
conversational access to business data.

The solution combines:
- **Natural language interaction** for intuitive user experience
- **Tool calling** (business tools + RAG retrieval) for precise, source-attributed data retrieval
- **Business analytics** for deep insights
- **AI-generated insights** for strategic decision support

By reducing dependency on technical teams and enabling self-service analytics, the Database Query Assistant empowers organizations to make faster, data-driven decisions while maximizing the value of their existing data assets.

### Key Takeaways

1. **AI democratizes data access** - Non-technical users can now query databases
2. **A unified LangChain agent bridges AI, data, and knowledge** - one tool-calling loop handles both live business data and RAG retrieval
3. **Context management enables natural conversations** - Multi-turn dialogues feel intuitive
4. **Business intelligence augments AI** - AI generates actionable insights
5. **Source attribution builds trust** - every data-backed answer cites which table(s) it came from

### Vision

This project sets the foundation for intelligent data analytics platforms that combine the power of large language models, RAG, and enterprise data systems to unlock new possibilities for data-driven decision making.

---

**Document Version:** 1.0
**Last Updated:** 2026-08-25
**Status:** Current — reflects the implemented system, including the dynamic-SQL LangGraph path and embedding-driven SQL generation; see [`04_solution_design.md`](04_solution_design.md), [`05_system_architecture.md`](05_system_architecture.md), [`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md), and [`10_implementation_guide.md`](10_implementation_guide.md) for detail