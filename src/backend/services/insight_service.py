"""Service Layer - Insight Service.

Implements the Insight & Recommendation business function from
docs/business_description.md > Core Business Functions:
generate_business_insight(). Reuses `langchain_app.llm.get_llm()` directly
against the conversation's most recently retrieved tool result - no agent
tool-calling loop needed, since this only reasons over data already
fetched this session (plan doc's Architecture decision: insight/
recommendation generation bypasses the tool-calling loop entirely).
"""

import json

from langchain_core.messages import HumanMessage

from backend.models.conversation import Conversation
from langchain_app.llm import get_llm
from langchain_app.prompts import INSIGHT_PROMPT

NO_DATA_MESSAGE = (
    "I don't have any retrieved data yet to generate insights from - "
    "ask a data question first (e.g. \"What are the top 5 products by revenue?\")."
)


def generate_business_insight(conversation: Conversation, question: str) -> str:
    """Generate business insights from the most recently retrieved tool result."""
    tool_results = conversation.last_tool_results()
    if not tool_results:
        return NO_DATA_MESSAGE

    latest = tool_results[-1]
    prompt = INSIGHT_PROMPT.format(
        question=question,
        tool_name=latest["tool"],
        result=json.dumps(latest["result"], default=str),
    )
    response = get_llm().invoke([HumanMessage(content=prompt)])
    return response.content or ""
