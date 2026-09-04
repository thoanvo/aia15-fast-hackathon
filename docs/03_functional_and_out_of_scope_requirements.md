# Out-of-Scope (OOS) Handling Requirements for Database Query Assistant

> **Implementation status:** Implemented in `src/langchain_app/oos_guard.py`
> (FR-01, FR-02, FR-03, FR-04, FR-05) plus the pre-existing prompt-only
> Layer 3 guardrails in `src/langchain_app/prompts.py`. The actual pipeline
> has diverged from the architecture in Sections 6-8 below in several ways,
> all found and fixed via real testing rather than assumed upfront — see
> **Section 10 (Actual Implementation)** for the current decision flow,
> config, and the reasoning behind each deviation. The >90% accuracy target
> (Non-Functional Requirements > Accuracy) has not been measured against a
> real LLM yet (no credentials available during development); everything
> else has been verified. See `01_business_requirements.md`'s Future
> Enhancements section for the full status writeup. Sections 1-9 below are
> preserved as originally written (the initial spec); they are no longer a
> complete description of the shipped behavior.

# 1. Purpose

This document defines the requirements and design approach for handling Out-of-Scope (OOS) user queries in the Database Query Assistant.

The objective is to ensure that the assistant responds only to supported business-related questions while preventing hallucinations, irrelevant responses, and unintended behavior.

---

# 2. Scope of the Assistant

The Database Query Assistant is designed to answer questions related to business data stored in enterprise databases.

Supported topics include:

- Sales reports
- Customer information
- Product information
- Order management
- Inventory status
- Business analytics and KPIs
- Operational reporting

Examples:

- What was the total revenue last month?
- Show the top 10 customers by sales.
- How many orders were created this week?
- What is the inventory level of Product A?

---

# 3. Definition of Out-of-Scope Queries

An Out-of-Scope query is any question not related to the supported business domain.

Examples:

- What is the weather today?
- Who is the president of the United States?
- Write a poem about AI.
- How do I cook fried rice?

Such queries must not trigger database access or SQL generation.

---

# 4. Functional Requirements

## FR-01 Intent Classification

The system shall classify every user query before executing retrieval or database operations.

Classification labels:

- IN_SCOPE
- OUT_OF_SCOPE

---

## FR-02 Semantic Relevance Validation

The system shall validate query relevance using vector similarity search.

Conditions:

- If similarity score is above the configured threshold, continue processing.
- If similarity score is below the threshold, classify the query as Out-of-Scope.

Recommended threshold:

```text
Similarity Score >= 0.70
```

---

## FR-03 Query Rejection

When a query is identified as Out-of-Scope, the system shall:

- Stop SQL generation.
- Stop retrieval operations.
- Return a friendly response.
- Explain supported capabilities.

Example response:

```text
I am a Database Query Assistant and can only answer questions related to business data such as customers, orders, products, sales, and reports.
```

---

## FR-04 User Guidance

The chatbot shall provide suggested questions to help users stay within the supported scope.

Example:

```text
Try asking:
- What were the sales figures for July?
- Show the top customers by revenue.
- How many orders were created today?
```

---

## FR-05 Logging and Monitoring

The system shall record Out-of-Scope queries for analytics and continuous improvement.

Captured information:

- User query
- Classification result
- Similarity score
- Timestamp

---

# 5. Non-Functional Requirements

## Accuracy

- Intent classification accuracy should be greater than 90%.

## Performance

- Classification should complete before SQL generation.
- OOS detection should not significantly impact response time.

## Security

- Out-of-Scope requests must never execute database queries.
- Unsupported requests must not expose internal schemas or sensitive information.

---

# 6. Recommended Architecture

```text
User Question
      |
      v
Intent Classifier
      |
      +--> OUT_OF_SCOPE
      |        |
      |        +--> Friendly Rejection
      |
      +--> IN_SCOPE
               |
               v
        Embedding Search
               |
               v
      Similarity Validation
               |
               v
          SQL Generation
               |
               v
         Database Query
               |
               v
          Final Response
```

---

# 7. Technical Approach

## Layer 1: Intent Classification

Possible technologies:

- GPT-5
- Azure OpenAI
- Semantic Kernel
- LangChain Router

Goal:

Determine whether the question belongs to the supported business domain.

---

## Layer 2: Similarity Threshold Validation

Possible technologies:

- OpenAI Embeddings
- BGE Embeddings
- Instructor Embeddings
- Sentence Transformers

Vector databases:

- Pinecone
- FAISS
- ChromaDB
- Azure AI Search

Goal:

Detect questions that are semantically unrelated to the knowledge base.

---

## Layer 3: Guardrails

Example system prompt:

```text
You are a Database Query Assistant.

You only answer questions related to:
- Customers
- Orders
- Sales
- Products
- Business Reports

If a question falls outside the supported domain, politely decline and suggest supported topics.
```

---

# 8. Best Practice Recommendation

Use a Hybrid OOS Detection Strategy:

1. Intent Classification
2. Similarity Threshold Validation
3. LLM Guardrails

This approach provides:

- Higher accuracy
- Reduced hallucination risk
- Better user experience
- Stronger production readiness

---

# 9. Expected Outcome

The Database Query Assistant should:

- Answer business-related questions accurately.
- Reject irrelevant or unsupported requests safely.
- Prevent unnecessary database operations.
- Improve trustworthiness and user experience.
- Demonstrate production-grade AI governance and guardrail capabilities.

---

# 10. Actual Implementation

This section describes the pipeline as it actually ships in
`src/langchain_app/oos_guard.py` (Layers 0-2) and
`src/langchain_app/prompts.py` (Layer 3), as of 2026-08-24. It supersedes
Sections 6-8 above, which describe the originally-planned architecture.

## 10.1 Decision Flow

```text
User Question
      |
      v
Layer 0: Prompt-Injection Check (is_prompt_injection)
      |
      +--> match on a known attack phrase --> Reject (OUT_OF_SCOPE)
      |
      v
Layer 1: Intent Classification (classify_intent)
      |
      +--> OUT_OF_SCOPE --> Reject (friendly message, logged)
      |
      v  (IN_SCOPE)
Layer 2: Semantic Relevance (semantic_relevance_score, top-3 average)
      |
      +--> score >= threshold (0.35)              --> Accept
      |
      +--> has_business_keyword AND
      |    score >= threshold * 0.7 (keyword rescue) --> Accept
      |
      +--> otherwise                               --> Reject (friendly message, logged)
      |
      v  (Accept)
Layer 3: Agent System Prompt (prompts.py SYSTEM_PROMPT)
      |
      +--> no tool covers the request --> Decline
      |    (e.g. broad "all X" requests now map to the closest
      |    ranked/aggregated tool at its max limit instead - see 10.5)
      |
      v
Tool call(s) -> Final Response
```

A query must pass Layers 0-2 to reach the agent at all (no tool call, no
retrieval, no agent-loop LLM call for a rejected query); Layer 3 is a
further safety net for anything that has a passing similarity score but
no way to actually be answered by a registered tool.

## 10.2 Deviations from Sections 6-8, and why

| Spec (Sections 6-8) | Actual (`oos_guard.py`) | Why |
|---|---|---|
| FR-02 threshold `>= 0.70` | `OOS_SIMILARITY_THRESHOLD = 0.35` (`.env` override) | 0.70 assumes a similarity scale where unrelated topics score far lower than same-topic-different-wording ones. Empirically, this project's default embedding model (`sentence-transformers/all-MiniLM-L6-v2`) puts in-scope questions around 0.46-0.66 and out-of-scope around 0.09-0.24 - 0.70 would reject legitimate questions. |
| Similarity = single best match (`max()`) | Similarity = average of the **top-3** best matches | Less sensitive to a single lucky/unlucky reference-question match; a top-3 average is more stable against outliers on both sides. |
| 3 layers (Intent -> Similarity -> Guardrails) | 4 layers - a **prompt-injection screen** (`is_prompt_injection()`) runs first, before intent classification | Screens out jailbreak/instruction-override phrasing (`"ignore previous instructions"`, `"jailbreak"`, `"system prompt"`, etc.) before it can influence the topic classifier at all, not just get caught incidentally by it. Documented as an early-warning filter only - it is pattern-based and easy to bypass with rewording, so it is **not** a substitute for the real security controls (Layer 3 system-prompt rules, tool permission scoping, no direct SQL access - see `prompts.py`). |
| Similarity below threshold -> reject | Similarity below threshold **but above `threshold * 0.7`, with a business-entity keyword/phrase match** -> accept ("keyword rescue") | Plain record-listing requests ("Please provide me all the customer information", "Show all customers") and Vietnamese phrasing can legitimately score below the analytical-question-shaped reference corpus. The `0.7x` floor keeps this from over-accepting: e.g. "Tell me a joke about customers" (score ~0.1) still gets rejected because 0.1 < 0.35*0.7 = 0.245. |
| Reference corpus is implicitly English-only | Bilingual (English + Vietnamese) reference questions and few-shot classifier examples | This is a Vietnamese + English enterprise assistant (see `prompts.py` Operating Procedure step 5); an English-only corpus scores Vietnamese in-scope questions unfairly low purely on language, not topic. |
| Intent classifier: exact match against `"OUT_OF_SCOPE"`, else `IN_SCOPE` | Checks for `"IN_SCOPE"` or `"OUT_OF_SCOPE"` as a substring; if **neither** is found, logs a warning and **fails closed to `OUT_OF_SCOPE`** | The exact-match version defaulted an ambiguous/off-format LLM response (e.g. "This appears to be OUT_OF_SCOPE.") to `IN_SCOPE` - the wrong direction to fail. |
| Business-keyword matching (if used) | Phrase-based substring matching (`_DATABASE_PHRASES`), not tokenization | Vietnamese business terms are multi-word ("khách hàng", "doanh thu", "sản phẩm"). A word-tokenizer (`re.findall(r"\w+", text)`) splits these into separate tokens that never match a combined keyword like `"khách_hàng"`. Phrase matching (`phrase in text.lower()`) treats the multi-word term as one unit. |

## 10.3 Config (`src/config/settings.py`, `.env`)

| Setting | Default | Purpose |
|---|---|---|
| `OOS_ENABLED` | `true` | Master switch. `false` disables Layers 0-2 entirely and falls back to Layer 3 (system-prompt) guardrails only. |
| `OOS_SIMILARITY_THRESHOLD` | `0.35` | FR-02 similarity threshold; re-run the calibration in `oos_guard.py`'s module docstring if `EMBEDDING_MODEL_NAME` changes. |

`OOS_SECURITY_CHECK_ENABLED` and `OOS_UNCERTAIN_MARGIN` also exist in
`config/settings.py` / `.env.example` from an earlier iteration that added
a togglable security-classifier LLM call and a three-state
(`IN_SCOPE`/`OUT_OF_SCOPE`/`UNCERTAIN`) decision. That iteration was
superseded by the current `is_prompt_injection()` pattern-check design
(Section 10.2) - these two settings are currently unused dead
configuration, not part of the live decision flow. Cross-reference before
relying on them.

## 10.4 FR-03/FR-04 response text (actual)

```text
I'm a Database Query Assistant and can only answer questions related
to business data, customers, products, sales, revenue, and database
structure.
```

This is `_FRIENDLY_REJECTION` in `oos_guard.py` - close to, but not
word-for-word, the FR-03 example in Section 4. There is currently a
single English-only rejection message (an earlier iteration added a
Vietnamese variant selected via language detection; that was also
superseded and is not in the current implementation). FR-04's suggested
questions are not currently included in the rejection message.

## 10.5 Layer 3 refinement: broad/unscoped requests

No tool returns a raw, complete export of a table (e.g. every customer
record) - only ranked/aggregated views (`get_top_customers`,
`get_segment_performance`, etc., see
`src/langchain_app/tools/business_tools.py`). Once Layers 0-2 correctly
accept a broad request like "Please provide me all the customer
information" (it is a legitimate in-scope business question), the agent
previously had no tool to satisfy it literally and fell back to its
generic "no legitimate analysis remains" decline
(`prompts.py`'s prompt-injection-handling fallback text), which reads as
a second, redundant OOS rejection.

`prompts.py`'s `SYSTEM_PROMPT` now instructs the agent that for a
broad/unscoped request, it should call the closest ranked/aggregated tool
for that entity at its maximum supported limit (e.g.
`get_top_customers(limit=100)`) and report the result as the top N, not a
complete export, instead of declining outright.
