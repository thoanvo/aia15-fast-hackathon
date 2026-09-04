"""LangChain tool - RAG retrieval over the FAISS knowledge-base store.

Sits alongside `business_tools` in the same agent (see plan doc's "One
unified LangChain tool-calling agent" decision) so a single turn can freely
mix live business-data lookups and schema/SQL knowledge-base questions.
"""

from langchain_core.tools import tool

from langchain_app.vectorstore.store import get_retriever

_RETRIEVAL_K = 3


@tool(parse_docstring=True)
def search_knowledge_base(query: str) -> str:
    """Search the database schema and sample-SQL knowledge base for background info.

    Use this for questions about how the database is structured, what a
    column or table means, or what a typical SQL query looks like - not for
    questions that need live data (use the business data tools for actual
    top products/customers/sales figures instead).

    Args:
        query: The schema/SQL question to search for.
    """
    try:
        docs = get_retriever(k=_RETRIEVAL_K).invoke(query)
    except Exception as exc:  # noqa: BLE001 - a retrieval failure must not crash the agent turn
        return f"Knowledge-base search failed: {exc}"
    if not docs:
        return "No relevant knowledge-base content found."
    return "\n\n---\n\n".join(
        f"[{doc.metadata.get('source', 'unknown')} > {doc.metadata.get('title', '')}]\n{doc.page_content}"
        for doc in docs
    )


def get_retrieval_tool():
    """Return the retrieval tool for agent construction (Phase 4)."""
    return search_knowledge_base
