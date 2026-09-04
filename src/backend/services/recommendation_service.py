"""Service Layer - Recommendation Service.

Implements the remaining Insight & Recommendation business function from
docs/business_description.md > Core Business Functions:
generate_recommendation(). Reuses `langchain_app.llm.get_llm()` directly -
no tool-calling loop needed, this only reasons over insight text already
generated.
"""

from langchain_core.messages import HumanMessage

from langchain_app.llm import get_llm
from langchain_app.prompts import RECOMMENDATION_PROMPT


def generate_recommendation(insight: str) -> str:
    """Turn a generated insight into actionable, strategic recommendations."""
    prompt = RECOMMENDATION_PROMPT.format(insights=insight)
    response = get_llm().invoke([HumanMessage(content=prompt)])
    return response.content or ""
