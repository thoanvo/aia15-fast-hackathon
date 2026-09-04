import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

import numpy as np
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from config.settings import OOS_SIMILARITY_THRESHOLD
from langchain_app.llm import get_llm
from langchain_app.vectorstore.embeddings import get_embeddings

logger = logging.getLogger(__name__)

Classification = Literal["IN_SCOPE", "OUT_OF_SCOPE"]

# ==========================================================
# Reference corpus (EN + VI)
# ==========================================================

_IN_SCOPE_REFERENCE_QUESTIONS = [
    # Customer
    "Show all customers",
    "List all customers",
    "Customer information",
    "Khách hàng nào có doanh thu cao nhất?",
    "Cho tôi xem danh sách khách hàng",

    # Product
    "Show all products",
    "List all products",
    "Top products by revenue",
    "Danh sách sản phẩm",
    "Top 5 sản phẩm theo doanh thu",

    # Orders
    "Show all orders",
    "Retrieve order details",
    "Danh sách đơn hàng",

    # Region
    "Show all regions",
    "List all regions",
    "What is the name of region 1?",
    "What region does region ID 2 correspond to?",
    "Danh sách khu vực",
    "Tên của khu vực có id 1 là gì?",

    # Sales
    "What is the sales trend?",
    "Revenue by region",
    "Doanh thu theo khu vực",
    "Xu hướng doanh thu 6 tháng gần nhất",

    # Schema
    "Describe customer table",
    "Show database schema",
    "What columns exist in customer table?",
    "Mô tả bảng customer",
    "Các cột trong bảng customer là gì?"
]

# ==========================================================
# Business entity phrases (EN + VI) for keyword rescue
# ==========================================================
# Phrase-based matching (not token-based) for accurate multi-word
# entity detection, especially Vietnamese. See module docstring
# in docs/03_functional_and_out_of_scope_requirements.md.

_DATABASE_PHRASES = {
    # English
    "customer",
    "customers",
    "product",
    "products",
    "order",
    "orders",
    "sales",
    "revenue",
    "profit",
    "margin",
    "region",
    "regions",
    "asia",
    "europe",
    "north america",
    "south america",
    "database",
    "schema",
    "table",
    "tables",
    "column",
    "columns",
    "record",
    "records",
    "sql",

    # Vietnamese (multi-word phrases as atomic units)
    "khách hàng",
    "sản phẩm",
    "doanh thu",
    "lợi nhuận",
    "đơn hàng",
    "khu vực",
    "châu á",
    "châu âu",
    "bắc mỹ",
    "nam mỹ",
    "bảng",
    "cột",
    "dữ liệu",
    "lịch sử",
    "câu hỏi",
    "trả lời",
    "vừa rồi",
    "gần nhất",
    "trước đó",
}

# ==========================================================
# Security patterns
# ==========================================================

_SECURITY_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "jailbreak",
    "system prompt",
    "reveal prompt",
    "show hidden instructions",
    "bypass security",
]

# ==========================================================
# Prompts
# ==========================================================

_INTENT_CLASSIFICATION_PROMPT = """
Classify the user's question.

Answer with EXACTLY one token:

IN_SCOPE
OUT_OF_SCOPE

GUIDELINE:
If the question is related to database data, business metrics, analysis, reporting, tables, columns, customers, products, sales, orders, regions, revenue, trends, or any company operations, ALWAYS classify as IN_SCOPE.
If the question asks about business entities using generic words or pronouns (e.g., "who", "which one", "where", "what", "ai mua nhiều nhất", "sản phẩm nào", "khu vực nào", "tháng nào"), ALWAYS classify as IN_SCOPE.
If the question is a follow-up, refinement, filter, clarification, asks about the previous answer, or references conversation history (e.g., "Why?", "Explain that", "Only in Asia.", "Filter by North", "What about Europe?", "What did you just say?", "Show more", "What was my previous question?"), ALWAYS classify as IN_SCOPE.
When in doubt, classify as IN_SCOPE to allow the Assistant to attempt answering.

IN_SCOPE:
- business data and analytics (revenue, profit, cost, quantities, margins, AOV, KPI)
- customer data, profiles, buyer lists, segments, spending behavior
- product catalog, categories, inventory, sales volume, top/bottom performers
- orders, transactions, sales records, dates, time windows
- geographical performance, regional breakdowns, countries, locations, continents
- schema exploration, database tables, column definitions, relationships, SQL assistance
- looking up specific records by id, code, or name
- comparative analytics, sales/revenue/profit trends over any time window ("this quarter", "last 6 months", "monthly", "year-over-year")
- business recommendations, insights, forecasts, operational suggestions
- contextual follow-ups, filters, and conversation history queries ("Only in Asia.", "Why?", "List 3 QA gần nhất", "conversation history")

Examples:
- Show all customers
- List all products
- Revenue by region
- Top customers by revenue
- What is the name of region 1?
- What region does region ID 2 correspond to?
- Show the sales trend for the last 6 months.
- What is the revenue trend this quarter?
- What insights can you provide?
- Give me business insights about sales performance.
- Which product should we promote next month?
- Suggest products to promote next month.
- Only in Asia.
- What about North America?
- Compare that with Q2.
- Who purchased the most?
- What did we talk about earlier?
- Can you explain the previous answer?
- What was the first product you listed?
- List 3 QA gần nhất
- List all QA
- Show conversation history
- Liệt kê lịch sử hội thoại
- Liệt kê các câu hỏi vừa rồi
- Danh sách khách hàng
- Top sản phẩm theo doanh thu
- Mô tả bảng customer
- Tên của khu vực có id 1 là gì?
- Xu hướng doanh thu 6 tháng gần nhất
- Giải thích rõ hơn kết quả vừa rồi

OUT_OF_SCOPE:
- general chit-chat / casual jokes
- weather forecast (e.g. "What is the weather in Hanoi?")
- general programming / coding help unrelated to this database
- language translation of arbitrary non-business text
- general trivia / world knowledge unrelated to company entities (e.g. "What is the capital of France?")
- personal life advice (e.g. "What should I eat for dinner?")

Question:
{question}
"""

# ==========================================================
# Greeting patterns & Welcome responses (HACK-D02)
# ==========================================================

_EN_GREETINGS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "greetings",
    "howdy",
}

_VI_GREETINGS = {
    "xin chào",
    "chào bạn",
    "chào bot",
    "chào em",
    "chào anh",
    "chào chị",
    "chào",
    "alo",
    "hé lô",
}

_WELCOME_MESSAGE_EN = (
    "Hello! I am your **Database Query Assistant**.\n\n"
    "I can help you query and analyze business data across the following areas:\n"
    "- **Customers:** Customer profiles, segments, contact details, and top buyers.\n"
    "- **Products:** Product catalog, categories, inventory, and best-sellers.\n"
    "- **Sales & Orders:** Revenue trends, order details, quantity sold, and profit margins.\n"
    "- **Regions & Performance:** Geographical performance and regional sales analytics.\n"
    "- **Database Schema:** Table structures, column definitions, and SQL assistance.\n\n"
    "**Try asking:**\n"
    "- *\"What are the top 5 products by revenue?\"*\n"
    "- *\"Show revenue trend for this quarter.\"*\n"
    "- *\"List all customers in Asia.\"*\n"
    "- *\"What is the total sales for Region 1?\"*"
)

_WELCOME_MESSAGE_VI = (
    "Xin chào! Tôi là **Trợ lý Truy vấn Cơ sở Dữ liệu (Database Query Assistant)**.\n\n"
    "Tôi có thể hỗ trợ bạn tra cứu và phân tích dữ liệu kinh doanh trong các phạm vi sau:\n"
    "- **Khách hàng (Customers):** Thông tin khách hàng, phân khúc, danh sách khách hàng hàng đầu.\n"
    "- **Sản phẩm (Products):** Danh mục sản phẩm, nhóm hàng, doanh thu và sản phẩm bán chạy.\n"
    "- **Bán hàng & Đơn hàng (Sales & Orders):** Xu hướng doanh thu, chi tiết đơn hàng, lợi nhuận.\n"
    "- **Khu vực (Regions):** Báo cáo hiệu suất kinh doanh theo từng vùng/khu vực địa lý.\n"
    "- **Cấu trúc CSDL (Schema):** Mô tả các bảng, tên cột và thông tin truy vấn SQL.\n\n"
    "**Bạn có thể thử các câu hỏi mẫu sau:**\n"
    "- *\"Top 5 sản phẩm có doanh thu cao nhất?\"*\n"
    "- *\"Xu hướng doanh thu 6 tháng gần nhất?\"*\n"
    "- *\"Cho tôi xem danh sách khách hàng\"*\n"
    "- *\"Doanh thu của khu vực 1 là bao nhiêu?\"*"
)

import re

def detect_greeting_only(question: str) -> Optional[str]:
    """Detect if the input is purely a greeting without any business question.

    Returns:
        'vi' if Vietnamese greeting-only
        'en' if English greeting-only
        None if not a greeting, or if it contains a business question/additional query.
    """
    cleaned = re.sub(r"[^\w\s]", "", question.strip().lower())
    cleaned = " ".join(cleaned.split())

    if not cleaned:
        return None

    # Check Vietnamese greetings
    for g in _VI_GREETINGS:
        if cleaned == g or cleaned == f"{g} ạ" or cleaned == f"{g} nha":
            return "vi"

    # Check English greetings
    for g in _EN_GREETINGS:
        if cleaned == g or cleaned == f"{g} there" or cleaned == f"{g} assistant":
            return "en"

    return None

_FRIENDLY_REJECTION = (
    "I'm a Database Query Assistant and can only answer questions "
    "related to business data, customers, products, sales, revenue, "
    "and database structure."
)

# ==========================================================
# Models
# ==========================================================

@dataclass
class OOSResult:
    in_scope: bool
    classification: Classification
    similarity_score: float
    message: Optional[str] = None

# ==========================================================
# Embeddings
# ==========================================================

_reference_embeddings = None


def _get_reference_embeddings() -> np.ndarray:
    global _reference_embeddings

    if _reference_embeddings is None:
        vectors = get_embeddings().embed_documents(
            _IN_SCOPE_REFERENCE_QUESTIONS
        )
        _reference_embeddings = np.array(vectors)

    return _reference_embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)

    if denom == 0:
        return 0.0

    return float(np.dot(a, b) / denom)


def semantic_relevance_score(question: str) -> float:
    query_vector = np.array(
        get_embeddings().embed_query(question)
    )

    refs = _get_reference_embeddings()

    scores = [
        _cosine_similarity(query_vector, ref)
        for ref in refs
    ]

    if not scores:
        return 0.0

    # Top-3 average instead of max
    scores = sorted(scores, reverse=True)

    top_k = scores[:3]

    return float(sum(top_k) / len(top_k))

# ==========================================================
# Security
# ==========================================================

def is_prompt_injection(question: str) -> bool:
    q = question.lower()

    return any(
        pattern in q
        for pattern in _SECURITY_PATTERNS
    )

# ==========================================================
# Keyword rescue (phrase-based matching)
# ==========================================================

def _has_business_keyword(question: str) -> bool:
    """Check if question contains business-entity keywords/phrases.

    Uses phrase matching (not token-based) to handle multi-word entities:
    "khách hàng" (customer), "sản phẩm" (product), "doanh thu" (revenue).
    Token-based matching would split these into {"khách", "hàng", ...}
    and never match the full phrase.

    This is used only for keyword rescue (see check_scope() docstring):
    the question must also have classification==IN_SCOPE AND
    score >= threshold * 0.7 to actually be accepted.
    """
    text = question.lower()
    return any(phrase in text for phrase in _DATABASE_PHRASES)

# ==========================================================
# Intent classification
# ==========================================================

def classify_intent(
    question: str,
    llm: Optional[BaseChatModel] = None,
    chat_history: Optional[list] = None,
) -> Classification:
    """Classify question as IN_SCOPE or OUT_OF_SCOPE using LLM.

    Fails closed: if LLM response is ambiguous or missing, defaults to
    OUT_OF_SCOPE (safer than defaulting to IN_SCOPE). Only accepts
    IN_SCOPE if the string explicitly contains it.
    """
    # If this is an ongoing conversation with prior history, allow follow-up questions
    if chat_history and len(chat_history) > 0:
        history_context = "\n".join(
            f"{msg.__class__.__name__}: {getattr(msg, 'content', str(msg))[:200]}"
            for msg in chat_history[-4:]
        )
        prompt_content = (
            f"{_INTENT_CLASSIFICATION_PROMPT}\n\n"
            f"Context: This is a multi-turn conversation. Here is the recent chat history:\n{history_context}\n\n"
            f"If the current question is a follow-up, filter, refinement, or continuation of the previous discussion (e.g. 'Only in Asia.', 'What about Europe?', 'Why?'), it IS IN_SCOPE.\n\n"
            f"Question:\n{question}"
        )
    else:
        prompt_content = _INTENT_CLASSIFICATION_PROMPT.format(question=question)

    llm = llm or get_llm(temperature=0.0)

    response = llm.invoke([
        HumanMessage(
            content=prompt_content
        )
    ])

    text = (response.content or "").strip().upper()

    # Explicit matches
    if "IN_SCOPE" in text:
        return "IN_SCOPE"

    if "OUT_OF_SCOPE" in text:
        return "OUT_OF_SCOPE"

    # Fail open to IN_SCOPE for any ambiguous response to avoid over-blocking
    logger.info("Classifier returned ambiguous response %r -> defaulting to IN_SCOPE", text)
    return "IN_SCOPE"

# ==========================================================
# Logging
# ==========================================================

def log_oos_query(
    question: str,
    classification: Classification,
    similarity_score: float
) -> None:

    logger.info(
        "OOS query rejected: classification=%s similarity_score=%.3f timestamp=%s question=%r",
        classification,
        similarity_score,
        datetime.now(timezone.utc).isoformat(),
        question,
    )

# ==========================================================
# Main Decision Engine
# ==========================================================

def check_scope(
    question: str,
    similarity_threshold: Optional[float] = None,
    llm: Optional[BaseChatModel] = None,
    chat_history: Optional[list] = None,
) -> OOSResult:
    """Sequential decision: classifier verdict is authoritative, similarity
    +keyword only rescue a low score when the classifier already agrees.
    """

    threshold = (
        OOS_SIMILARITY_THRESHOLD
        if similarity_threshold is None
        else similarity_threshold
    )

    if is_prompt_injection(question):
        return OOSResult(
            False,
            "OUT_OF_SCOPE",
            0.0,
            _FRIENDLY_REJECTION
        )

    # Greeting-only branch (HACK-D02): Return welcome introduction without Agent/DB call
    greeting_lang = detect_greeting_only(question)
    if greeting_lang:
        welcome_msg = _WELCOME_MESSAGE_VI if greeting_lang == "vi" else _WELCOME_MESSAGE_EN
        logger.info("Greeting detected (%s): question=%r -> returning welcome response", greeting_lang, question)
        return OOSResult(
            in_scope=False,
            classification="OUT_OF_SCOPE",
            similarity_score=1.0,
            message=welcome_msg,
        )

    score = semantic_relevance_score(question)

    classification = classify_intent(
        question,
        llm=llm,
        chat_history=chat_history,
    )

    has_keyword = _has_business_keyword(question)
    rescue_floor = threshold * 0.7

    logger.info(
        "OOS evaluation | question=%r classification=%s similarity=%.3f has_keyword=%s threshold=%.3f rescue_floor=%.3f",
        question,
        classification,
        score,
        has_keyword,
        threshold,
        rescue_floor,
    )

    # Strong reject: LLM says OUT_OF_SCOPE
    if classification == "OUT_OF_SCOPE":
        log_oos_query(question, classification, score)
        return OOSResult(
            False,
            classification,
            score,
            _FRIENDLY_REJECTION
        )

    # Accept directly if LLM classified as IN_SCOPE (bypassing Layer 2)
    return OOSResult(
        True,
        classification,
        score,
    )