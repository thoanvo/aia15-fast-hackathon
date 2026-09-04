"""Controller Layer - Chat Controller.

Responsibilities (docs/business_description.md > Technical Architecture >
Controller Layer): process incoming API requests, route them to the
appropriate service, validate requests, return formatted responses.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import chat_service, insight_service, recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, description="Client-chosen id for the conversation session.")
    question: str = Field(..., min_length=1, description="The user's natural-language question.")


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    source_tables: list[str] = Field(default_factory=list)
    kb_chunks: list[str] = Field(default_factory=list)
    chart_data: Optional[list[dict[str, Any]]] = None


class InsightRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question the insight should address.")


class InsightResponse(BaseModel):
    conversation_id: str
    insight: str


class RecommendationRequest(BaseModel):
    insight: str = Field(..., min_length=1, description="Insight text to turn into recommendations.")


class RecommendationResponse(BaseModel):
    conversation_id: str
    recommendation: str


class MessageOut(BaseModel):
    role: str
    content: Any = None
    source_tables: list[str] = Field(default_factory=list)
    kb_chunks: list[str] = Field(default_factory=list)
    chart_data: Optional[list[dict[str, Any]]] = None


class HistoryResponse(BaseModel):
    conversation_id: str
    messages: list[MessageOut]


@router.post("", response_model=ChatResponse)
def post_chat(request: ChatRequest) -> ChatResponse:
    """Handle one chat turn end to end (LangChain agent + multi-turn context)."""
    try:
        result = chat_service.handle_message(request.conversation_id, request.question)
    except Exception as exc:  # noqa: BLE001 - never leak internals; log and return a clean 500
        logger.exception("chat_service.handle_message failed for conversation_id=%s", request.conversation_id)
        raise HTTPException(status_code=500, detail="Failed to process the chat message.") from exc

    return ChatResponse(
        conversation_id=request.conversation_id,
        answer=result["answer"],
        source_tables=result["source_tables"],
        kb_chunks=result.get("kb_chunks", []),
        chart_data=result.get("chart_data"),
    )


@router.get("/{conversation_id}/history", response_model=HistoryResponse)
def get_history(conversation_id: str) -> HistoryResponse:
    """Return the full message history for a conversation (for the frontend's history view)."""
    conversation = chat_service.get_conversation(conversation_id)
    messages = [
        MessageOut(
            role=m.role,
            content=m.content,
            source_tables=m.source_tables,
            kb_chunks=m.kb_chunks,
            chart_data=m.chart_data,
        )
        for m in conversation.messages
    ]
    return HistoryResponse(conversation_id=conversation_id, messages=messages)


@router.post("/{conversation_id}/insight", response_model=InsightResponse)
def post_insight(conversation_id: str, request: InsightRequest) -> InsightResponse:
    """Generate a business insight from the conversation's most recently retrieved data."""
    conversation = chat_service.get_conversation(conversation_id)
    try:
        insight = insight_service.generate_business_insight(conversation, request.question)
    except Exception as exc:  # noqa: BLE001
        logger.exception("insight_service.generate_business_insight failed for conversation_id=%s", conversation_id)
        raise HTTPException(status_code=500, detail="Failed to generate insight.") from exc

    return InsightResponse(conversation_id=conversation_id, insight=insight)


@router.post("/{conversation_id}/recommendation", response_model=RecommendationResponse)
def post_recommendation(conversation_id: str, request: RecommendationRequest) -> RecommendationResponse:
    """Turn a previously generated insight into actionable recommendations."""
    try:
        recommendation = recommendation_service.generate_recommendation(request.insight)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "recommendation_service.generate_recommendation failed for conversation_id=%s", conversation_id
        )
        raise HTTPException(status_code=500, detail="Failed to generate recommendation.") from exc

    return RecommendationResponse(conversation_id=conversation_id, recommendation=recommendation)


@router.delete("/{conversation_id}")
def delete_chat(conversation_id: str) -> dict:
    """Clear a conversation's history (e.g. a "clear chat" action in the UI)."""
    chat_service.reset_conversation(conversation_id)
    return {"conversation_id": conversation_id, "status": "cleared"}
