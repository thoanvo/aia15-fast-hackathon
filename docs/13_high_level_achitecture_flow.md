# Architecture Story – Database Query Assistant

## Story

The Database Query Assistant enables business users to ask questions in natural language and receive trusted, data-driven answers. The system protects against out-of-scope requests, intelligently routes each request to the most suitable capability (Fixed Tools, RAG, or Dynamic SQL), validates generated SQL, performs retries when necessary, and returns answers enriched with insights, recommendations, charts, sources, and Text-to-Speech (TTS).

---

# End-to-End Flow

```text
Business User
      │
      ▼
Streamlit UI
      │
      ▼
FastAPI Backend
      │
      ▼
OOS Guardrail
      │
      ▼
LangChain Agent
      │
      ├── Fixed Business Tools
      ├── RAG Tool
      └── Dynamic SQL Workflow
              │
              ▼
      PostgreSQL / FAISS KB
              │
              ▼
 Answer + Insight + Recommendation
 Chart + Sources + TTS
              │
              ▼
         Business User
```

---

# 1. User Layer

## Business User

A non-technical business user interacts with the system through a conversational interface.

Example question:

> What are the Top 5 products by revenue in Q1 2024?

---

# 2. Frontend Layer (Streamlit)

The Streamlit application provides a rich user experience including:

- Conversational chat interface
- Business charts and visualizations
- Chat history
- Source references
- Built-in TTS player

The user's request is sent to the backend via HTTPS (JSON).

---

# 3. Backend Layer (FastAPI)

The backend processes requests through multiple services.

## API Gateway / Chat Endpoint

Receives user requests and routes them into the system.

## Request Validator

Validates:

- Request format
- Request size
- Request type

## Orchestrator / Service Layer

Manages:

- User session
- Conversation context
- Service coordination

## Response Builder

Prepares:

- Final answer
- Insights
- Sources
- TTS content

## TTS Generation

Converts text responses into Base64 audio for playback.

---

# 4. OOS Guardrail

Before any AI processing, the system evaluates the user's request through a multi-stage screening process to determine how the query should be handled.

## Step 1. Greeting Detection

The system first checks whether the user input is a greeting, small talk, or conversational message.

Examples:

- Hello
- Hi
- Good morning
- How are you?
- Thank you

If the input is identified as a greeting, the assistant responds with a friendly introduction and guidance on supported capabilities, without invoking business tools or data retrieval workflows.

---

## Step 2. In-Scope Check

If the request is not a greeting, the system verifies whether the question belongs to the supported business domain.

Examples:

- What are the top 5 products by revenue?
- Show sales performance by region.
- Compare customer growth between Q1 and Q2.

In-scope requests are forwarded to the LangChain Agent for intelligent tool routing and processing.

---

## Step 3. Out-of-Scope Detection

Requests that fall outside supported business analytics capabilities are classified as out-of-scope.

Examples:

- Write a poem about summer.
- Explain quantum physics.
- Who won the football match yesterday?

The system returns a friendly response explaining its domain limitations and suggests supported use cases.

---

## Decision Flow

```text
User Request
      │
      ▼
Greeting Detection
      │
 ┌────┴────┐
 │ Greeting│
 └────┬────┘
      ▼
 Friendly Introduction
      │
      End

      ▼
 In-Scope Check
      │
 ┌────┴───────┐
 │ In-Scope ? │
 └────┬───────┘
      │ Yes
      ▼
 LangChain Agent
      │
      ▼
 Business Processing

      │ No
      ▼
 Out-of-Scope Response
      │
      ▼
 Friendly Reject
``

## In-Scope Request

Requests related to supported business analytics are forwarded to the LangChain Agent.

## Out-of-Scope Request

The system returns a friendly explanation and does not execute unnecessary processing.

Example:

- General business analytics → Allowed
- Unsupported topics → Rejected

---

# 5. LangChain Agent (Unified Orchestrator)

The LangChain Agent acts as the central intelligence layer.

Responsibilities:

- Understand user intent
- Determine the optimal execution path
- Invoke the appropriate tool(s)
- Aggregate results
- Generate final responses

---

# Intelligent Tool Routing

The agent dynamically chooses among three capabilities.

## A. Fixed Business Tools

Purpose:

- Standard business questions
- Frequently used metrics
- High-speed retrieval

Characteristics:

- Pre-built SQL queries
- Exact match business logic
- Fast and reliable

Examples:

- Top products
- Revenue KPIs
- Standard reports

---

## B. RAG Tool

Purpose:

- Knowledge retrieval
- Documentation search
- Business definitions

Capabilities:

- Metric explanations
- Schema information
- SQL guidance
- FAQ retrieval

Data Source:

- FAISS Knowledge Base

---

## C. Dynamic SQL Tool

Purpose:

- Ad-hoc business analysis
- Questions without predefined reports

Capabilities:

- Dynamic SQL generation
- SQL validation
- Retry and refinement
- Read-only query execution

Framework:

- LangGraph Workflow

---

# 6. Data Sources

## PostgreSQL / Neon

Business database containing:

- Products
- Customers
- Sales
- Regions
- Business metrics

Access Mode:

- Read-only

---

## FAISS Knowledge Base

Stores:

- Business documentation
- Data definitions
- SQL guidelines
- FAQs
- Domain knowledge

---

# 7. Dynamic SQL Workflow (LangGraph)

When Dynamic SQL is selected, the system executes the following workflow.

## Step 1. Intent Analysis

Understand:

- Business intent
- Required data
- Analytical objective

---

## Step 2. SQL Generation

Generate SQL using:

- Database schema
- Business context
- User requirements

---

## Step 3. SQL Validation

Apply safety checks:

- SELECT-only queries
- LIMIT enforcement
- Single-statement restriction

---

## Step 4. Execution

Execute SQL against PostgreSQL using a read-only role.

---

## Step 5. Result Validation

Verify:

- Data quality
- Completeness
- Relevance

---

## Retry & Refine

If validation fails or results are insufficient:

- Refine SQL
- Regenerate query
- Retry execution

This loop continues until acceptable results are obtained.

---

# 8. Output Generation

The backend consolidates all information and generates enriched outputs.

## Answer

Natural language response.

## Insight

Business observations and findings.

## Recommendation

Suggested business actions.

## Chart

Visual representation of results.

## Sources

References used to produce the answer.

Examples:

- Database tables
- Knowledge Base chunks

## TTS

Audio version of the response.

---

# 9. RAG Pipeline

The knowledge retrieval pipeline consists of the following steps.

## Knowledge Sources

Input data includes:

- Documents
- Data schemas
- Business metrics
- SQL guides
- FAQs

---

## Text Processing

Data preparation:

- Cleaning
- Chunking

---

## Embeddings

Generate vector embeddings using sentence-transformer models.

---

## Vector Store

Store embeddings inside FAISS.

---

## Semantic Search

Retrieve the most relevant knowledge chunks during user queries.

---

# 10. Safety & Trust (Defense-in-Depth)

Multiple security layers protect the system.

## OOS Guardrail

Blocks unsupported requests.

---

## Prompt Injection Protection

Filters malicious instructions and prompt attacks.

---

## SQL Guardrail

Validates every generated SQL statement.

Rules:

- SELECT only
- LIMIT required
- Single statement only

---

## Read-Only Database Access

Prevents:

- INSERT
- UPDATE
- DELETE
- DDL operations

---

## Source Attribution

Every answer includes traceable supporting evidence from:

- Database tables
- Knowledge Base documents

---

## Audit & Monitoring

Tracks:

- Query executions
- Latency
- Error rates
- Retry attempts

---

# Architecture Overview

```text
┌──────────────┐
│ Business User│
└──────┬───────┘
       ▼
┌──────────────┐
│ Streamlit UI │
└──────┬───────┘
       ▼
┌──────────────┐
│ FastAPI API  │
└──────┬───────┘
       ▼
┌──────────────┐
│ OOS Guardrail│
└──────┬───────┘
       ▼
┌───────────────────────┐
│   LangChain Agent     │
│ Intelligent Routing   │
└─┬─────────┬─────────┬─┘
  │         │         │
  ▼         ▼         ▼
Fixed      RAG    Dynamic SQL
Tools      Tool     Workflow
  │         │         │
  ▼         ▼         ▼
Postgres   FAISS   PostgreSQL
 /Neon       KB      /Neon

        ▼
Answer • Insight
Recommendation
Chart • Sources • TTS
```

---

# Key Value Proposition

**Natural Language Question → OOS Validation → Intelligent Tool Routing → Trusted Data Retrieval → Validated Response → Insight + Chart + Sources + TTS**