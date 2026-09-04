# Hackathon Work Breakdown Structure (WBS) - FAST Team

## Dự án: Database Query Assistant

## 1. Mục tiêu Hackathon

Hoàn thiện và trình diễn một **Database Query Assistant** cho phép người dùng nghiệp vụ đặt câu hỏi bằng ngôn ngữ tự nhiên, truy vấn dữ liệu PostgreSQL, tìm kiếm knowledge base, tạo insight và recommendation mà không cần viết SQL.

WBS này ưu tiên:

- Xác minh rõ tính năng **đã có**, **một phần**, **chưa có**.
- Tận dụng tối đa source code hiện tại.
- Tăng điểm ở các tiêu chí: business value, AI architecture, technical implementation, demo quality và evidence hệ thống hoạt động.
- Không bổ sung công nghệ chỉ để tăng số lượng nếu không tạo business value hoặc demo value rõ ràng.

---

## 2. Phạm vi xác minh

Kết quả dưới đây được xác minh từ:

- `docs/08_project_structure.md`
- Cấu trúc thư mục và mô tả trách nhiệm của từng file/module
- Trạng thái Phase 0–10 được ghi trong tài liệu project structure

> **Quy ước trạng thái**
>
> - **Đã có:** Có module/file và tài liệu xác nhận đã hoàn thành.
> - **Một phần:** Đã có thiết kế, folder hoặc cơ chế liên quan nhưng còn bị tắt, thiếu kiểm thử chính thức, hoặc chưa được xác minh với môi trường thật.
> - **Chưa thấy:** Không có bằng chứng trong project structure được cung cấp.

---

# 3. Bảng xác minh tính năng hiện tại

| Component | Trạng thái | Mô tả chi tiết | Evidence trong source structure | Nhận xét Hackathon |
|---|---|---|---|---|
| FastAPI Backend | Đã có | Backend cung cấp API nhận câu hỏi từ Frontend, kiểm tra request và chuyển xử lý sang Chat Service. | `src/app.py`, `backend/controllers/chat_controller.py` | Có thể demo REST API và separation of concerns |
| Streamlit Frontend | Đã có | Giao diện chatbot hỗ trợ nhập câu hỏi, hiển thị lịch sử hội thoại, nguồn dữ liệu, biểu đồ và phát câu trả lời bằng TTS. | `frontend/app.py`, `pages/`, `components/`, hàm `render_tts()` | Có conversational UI và các thành phần trực quan phục vụ live demo |
| PostgreSQL / Neon | Đã có | Lưu trữ dữ liệu products, customers, sales và regions; DAO chịu trách nhiệm thực thi các truy vấn nghiệp vụ. | `database/connection/`, `database/dao/`, `database/scripts/` | Có data layer thực tế và connection pool |
| LangChain | Đã có | Điều phối LLM, prompts và tools trong một unified Agent thay cho vòng lặp function calling tự xây dựng. | `langchain_app/agent.py`, `prompts.py`, `tools/` | Dùng `create_tool_calling_agent` và `AgentExecutor` |
| LLM Integration | Đã có | `get_llm()` là single source of truth để khởi tạo `ChatOpenAI` cho Agent và các AI services. `_GatewayChatOpenAI` hỗ trợ OpenAI-compatible gateway, tùy chọn SSL verification, random `seed` theo từng call để tránh stale semantic cache, `disable_streaming=True` để bảo đảm seed override đi qua `_generate`/`_agenerate`, và cache LLM instance theo `temperature`. Team xác nhận real-LLM smoke test đã được áp dụng. | `langchain_app/llm.py`: `_GatewayChatOpenAI`, `_generate()`, `_agenerate()`, `get_llm()` | Đã sẵn sàng trình bày real LLM integration và gateway workarounds; cần lưu execution evidence cho Hackathon |
| Prompt Templates | Đã có | `SYSTEM_PROMPT` thiết lập authority/scope, operating procedure, prompt-injection rules, bilingual response và few-shot examples. Prompt thay đổi theo `FIXED_TOOLS_ENABLED`: khi bật, Agent phân biệt exact fixed-tool match, shape mismatch, raw ID lookup và plain unranked listing để route sang `answer_with_sql`; khi tắt (không có fixed tool nào được đăng ký), mọi câu hỏi dữ liệu đều route sang `answer_with_sql`. Dynamic-SQL tools (`sql_db_schema`, `answer_with_sql`) luôn được đăng ký bất kể flag. Insight và recommendation dùng prompt riêng trên dữ liệu đã lấy, không đi lại qua Agent loop. | `langchain_app/prompts.py`: `SYSTEM_PROMPT`, `AGENT_PROMPT`, `_FIXED_AND_DYNAMIC_TOOL_RULE`, `_DYNAMIC_ONLY_TOOL_RULE`, `_BROAD_REQUEST_RULE_*`, `INSIGHT_PROMPT`, `RECOMMENDATION_PROMPT` | Đây là điểm mạnh về Prompt Engineering; cần test routing cho cả flag ON/OFF |
| Tool Calling | Đã có | Ngoài fixed business tools và RAG tool, Dynamic-SQL có hai tools: `sql_db_schema` để lấy column definitions theo table và `answer_with_sql` để nhận nguyên câu hỏi tự nhiên, chạy toàn bộ LangGraph generate–validate–execute–retry trong một outer tool call. Cả hai dùng `_safe()` để trả `{"error": ...}` thay vì làm crash Agent turn. | `tools/business_tools.py`, `retrieval_tool.py`, `sql_tools.py`: `sql_db_schema()`, `answer_with_sql()`, `get_sql_tools()` | Cần demo đúng nguyên tắc: fixed tool khi exact shape match, Dynamic-SQL khi không có fixed tool phù hợp |
| RAG | Đã có | Truy xuất các đoạn knowledge base liên quan trước khi trả lời câu hỏi về schema, metric hoặc SQL context. | `retrieval_tool.py`, `vectorstore/`, `embedding/` | RAG dùng chung knowledge base với Dynamic-SQL context |
| Embeddings | Đã có | Chuyển nội dung knowledge base thành vector để phục vụ semantic retrieval. | `vectorstore/embeddings.py` | Một nguồn embedding duy nhất, giảm dual-path risk |
| Vector Database | Đã có | FAISS lưu và tìm kiếm embedding cục bộ; index được rebuild khi hash của source content thay đổi. | `vectorstore/store.py` | Có thể demo Vector Search mà không phụ thuộc external Vector DB |
| Semantic Search | Đã có | Tìm context theo ý nghĩa câu hỏi thay vì chỉ so khớp keyword; được dùng cho cả RAG và SQL generation. | `sql_context.py`, `retrieval_tool.py` | Nên demo bằng câu hỏi dùng cách diễn đạt khác tài liệu gốc |
| Knowledge Base | Đã có | Chứa mô tả schema, metrics và SQL idioms được dùng để grounding câu trả lời và Dynamic-SQL. | `src/embedding/` | Cần kiểm tra coverage và business descriptions trước demo |
| LangGraph | Đã có | Quản lý Dynamic-SQL dưới dạng state graph gồm khám phá schema, sinh SQL, validation, execution và bounded retry. | `sql_graph.py` | Là điểm kỹ thuật nổi bật để trình bày workflow có trạng thái |
| Dynamic Text-to-SQL | Một phần | `answer_with_sql(question)` chỉ nhận câu hỏi tự nhiên; outer Agent không tự viết SQL. SQL được sinh trong LangGraph bằng dedicated LLM call có schema context, sau đó validate, execute và bounded retry. Kết quả tool gồm `rows` và `query`; lỗi được trả về có cấu trúc. `sql_db_schema(table_names)` hỗ trợ kiểm tra schema theo danh sách table. Hai tool này luôn được đăng ký trên Agent, không phụ thuộc feature flag. | `sql_db.py`, `sql_context.py`, `sql_graph.py`, `sql_tools.py` | Logic đã rõ và an toàn hơn direct SQL argument, nhưng vẫn phụ thuộc read-only DB role (`READONLY_DATABASE_URL`) đã được provision đúng cho môi trường demo — nếu chưa provision, execution fallback về connection full-privilege |
| SQL Guardrails | Đã có | Chỉ cho phép single-statement SELECT, bắt buộc LIMIT và thực thi bằng restricted read-only connection. | `sql_validation.py`, `readonly_pool.py` | Thể hiện defense-in-depth thay vì chỉ phụ thuộc prompt |
| OOS Guardrail | Đã có, cần bổ sung greeting handling | Decision engine kết hợp security-pattern detection, LLM intent classification, embedding similarity với reference questions EN/VI và phrase-based business keyword rescue. Theo docstring, classifier verdict là authoritative; similarity và keyword chỉ rescue low score khi classifier đã đồng ý câu hỏi IN_SCOPE. Kết quả chuẩn hóa thành `OOSResult`. Tuy nhiên greeting như `Hello`, `Hi`, `Xin chào` không nên nhận generic OOS rejection; chatbot cần trả lời chào mừng, tự giới thiệu ngắn và gợi ý các nhóm câu hỏi được hỗ trợ mà không gọi Agent hoặc Database. | `oos_guard.py`: `is_prompt_injection()`, `classify_intent()`, `semantic_relevance_score()`, `_has_business_keyword()`, `check_scope()`, `OOSResult`; cần bổ sung greeting intent/response | Bổ sung greeting branch trước OOS classification để cải thiện first-time user experience |
| Source Attribution | Đã có | Gắn câu trả lời với DB tables hoặc KB chunks đã được sử dụng để tăng khả năng kiểm chứng. | `table_sources.py`, message fields `source_tables`, `kb_chunks` | Có thể dùng làm evidence và tăng trust |
| Conversation Memory | Đã có ở mức session history | Lưu lịch sử hội thoại theo conversation để Agent xử lý follow-up dựa trên ngữ cảnh trước đó. | `conversation.py`, `chat_service.py`, `conversation_history.py` | Chưa thấy long-term hoặc persistent memory |
| Insight Generation | Đã có | Chuyển structured tool result thành nhận định nghiệp vụ và có thể dùng với fixed-tool hoặc Dynamic-SQL result. | `insight_service.py` | Giúp demo vượt qua mức chỉ trả về raw database rows |
| Recommendation | Đã có | Sinh đề xuất hành động dựa trên dữ liệu và insight của lượt hội thoại. | `recommendation_service.py` | Nên kiểm tra recommendation luôn grounded theo dữ liệu |
| Chart / Visualization | Đã có | Phân tích tool result bằng heuristic deterministic và tạo dữ liệu phù hợp cho line/bar chart mà không gọi thêm LLM. | `chart_data.py`, `response_display.render_data_chart()` | Tăng demo quality và giảm token/latency |
| TTS | Đã có | Người dùng bấm `Listen`; Frontend gọi API tổng hợp giọng nói, lưu audio bytes trong session state và phát WAV bằng `st.audio`. | `render_tts(text, key_prefix)`, `api_client.synthesize_speech(text)` | Cần verify API/backend TTS, model availability, tiếng Việt/Anh và fallback |
| Streaming Response | Chưa thấy | Chưa có evidence cho việc trả token hoặc nội dung từng phần từ Backend đến Frontend. | Không có evidence rõ trong project structure | Chỉ nên bổ sung nếu không ảnh hưởng demo stability |
| Multi-Agent | Chưa thấy | Project hiện dùng một unified LangChain Agent; LangGraph chỉ điều phối workflow Dynamic-SQL, chưa phải hệ thống nhiều Agent chuyên biệt. | Không có Supervisor Agent hoặc specialist agents trong structure | Không nên ưu tiên hơn evaluation và demo stability |
| STT | Chưa thấy | Chưa có luồng nhận microphone input và chuyển speech thành câu hỏi văn bản. | Không có module/service tương ứng | Bonus feature sau khi P0 ổn định |
| Local LLM | Chưa thấy | LLM factory hỗ trợ OpenAI-compatible endpoint nhưng structure chưa xác nhận local inference runtime hoặc model. | Không có evidence Ollama/local runtime | Có thể khảo sát sau khi core demo ổn định |
| Pinecone | Chưa có | Project đang dùng FAISS làm Vector Database và không có Pinecone integration. | Không có Pinecone module/config | Không cần migrate nếu không tạo thêm business value |
| Evaluation Framework | Chưa hoàn chỉnh | Có bộ câu hỏi nghiệp vụ và cấu trúc test, nhưng chưa có framework thực thi, metric và report được commit đầy đủ. | `docs/02_test_cases_database_query_assistant.md`, folder `tests/`; Phase 7 còn mở | Đây là gap quan trọng nhất trước Hackathon |
| Unit/Integration/E2E Tests | Chưa hoàn chỉnh | Đã định nghĩa các thư mục test nhưng tài liệu xác nhận chưa có committed pytest suite cho toàn bộ critical path. | `tests/{unit,integration,end_to_end}/` | P0 để chứng minh hệ thống thực sự hoạt động |
| Monitoring / Observability | Chưa thấy | Chưa có bằng chứng về tracing tập trung cho LLM call, tool call, retrieval, SQL workflow, latency và errors. | Không có evidence LangSmith/OpenTelemetry/dashboard | Nên bổ sung tracing cơ bản nếu còn thời gian |
| Authentication | Chưa thấy | Chưa có luồng đăng nhập, phân quyền hoặc bảo vệ API theo user role trong structure được cung cấp. | Không có module auth trong structure | Không thuộc trọng tâm demo hiện tại |
| Docker | Chưa thấy | Project structure chưa liệt kê container definition để đóng gói Backend, Frontend và dependencies. | Không có Dockerfile được liệt kê | Bổ sung nếu cần reproducible demo |
| CI/CD | Chưa thấy | Chưa có pipeline tự động chạy lint, tests hoặc deployment được thể hiện trong structure. | Không có pipeline được liệt kê | P2, không chặn live demo |

---

# 4. Kết luận xác minh

## 4.1 Năng lực đã đủ mạnh để demo

Project đã có nền tảng AI Engineering tốt:

- LangChain Agent và Tool Calling.
- RAG, FAISS, Embeddings và Semantic Search.
- LangGraph cho Dynamic Text-to-SQL.
- Hybrid OOS Guardrail.
- SQL validation và restricted read-only execution.
- Conversation context, insight, recommendation và chart visualization.
- Source attribution cho database table và KB chunks.

## 4.2 Các gap ảnh hưởng trực tiếp đến điểm Hackathon

1. Chưa có committed `pytest` suite và báo cáo evaluation.
2. Cần đóng gói execution evidence của real-LLM smoke test và real PostgreSQL/Neon workflow cho phần trình bày.
3. Dynamic-SQL đang bị tắt mặc định.
4. Chưa có evidence package gồm logs, screenshots, traces và benchmark.
5. Chưa có monitoring/tracing rõ ràng.
6. Chưa chuẩn hóa live-demo script và fallback plan.

---

# 5. Hackathon WBS theo Workstream

## Workstream A – Baseline và Environment Readiness

### HACK-A01: Chạy baseline toàn hệ thống

- **Priority:** P0
- **PIC gợi ý:** Tech Lead + Backend
- **Mục tiêu:** Xác minh project có thể chạy end-to-end trước khi bổ sung feature.

#### Tasks

- Thiết lập `.env` từ `.env.example`.
- Xác minh FastAPI khởi động thành công.
- Xác minh Streamlit kết nối được backend.
- Xác minh PostgreSQL/Neon connection và DAO queries.
- Xác minh FAISS index được load hoặc rebuild.
- Chạy tối thiểu một business-tool query và một KB retrieval query.
- Ghi lại lỗi cấu hình và hướng xử lý.

#### Deliverables

- Baseline checklist.
- Environment issue log.
- Screenshot hoặc recording cho luồng end-to-end.

#### Definition of Done

- UI gửi câu hỏi và nhận câu trả lời từ backend.
- Có evidence tool call và nguồn dữ liệu.

---

### HACK-A02: Chuẩn hóa evidence cho real-LLM smoke test

- **Priority:** P0
- **PIC gợi ý:** AI Engineer

#### Current Status

- Real-LLM integration và smoke test đã được team xác nhận.
- `llm.py` đã tập trung gateway compatibility và các workaround liên quan đến SSL, semantic response caching và Agent streaming behavior.

#### Tasks

- Ghi lại model và OpenAI-compatible endpoint configuration dùng trong demo nhưng không đưa secret vào tài liệu.
- Lưu log hoặc screenshot của một real-LLM invocation thành công.
- Chứng minh random `seed` được inject trên từng sync/async call.
- Chứng minh `disable_streaming=True` tránh stale tool-call loop qua gateway cache.
- Chạy smoke test cho business tool, RAG tool, OOS guard và Dynamic-SQL nếu được bật.
- Ghi nhận latency và error/fallback behavior trong môi trường demo.

#### Deliverables

- Real-LLM smoke-test evidence.
- LLM configuration summary đã loại bỏ secrets.
- Một trace hoặc log minh họa Agent gọi đúng tool.

---

## Workstream B – AI Core và Dynamic Text-to-SQL

### HACK-B01: Bật và harden Dynamic-SQL

- **Priority:** P0
- **PIC gợi ý:** AI Engineer + Database Engineer

#### Tasks

- Provision restricted read-only DB role (`READONLY_DATABASE_URL`) trước khi demo — Dynamic-SQL tools luôn được đăng ký nên role này bắt buộc, không còn tùy chọn qua feature flag.
- Xác minh schema reflection.
- Xác minh semantic context retrieval từ FAISS.
- Kiểm tra generate → validate → execute → retry workflow.
- Kiểm tra bắt buộc `LIMIT`, SELECT-only và single-statement.
- Chuẩn bị fallback khi SQL generation thất bại.

#### Deliverables

- Dynamic-SQL demo-ready configuration.
- Safety test evidence.
- Danh sách câu hỏi không được fixed tools hỗ trợ.

#### Definition of Done

- Dynamic-SQL chạy trên restricted connection.
- Harmful SQL bị chặn trước execution.

---

### HACK-B02: Trực quan hóa LangGraph workflow

- **Priority:** P0
- **PIC gợi ý:** AI Engineer + Presentation Team

#### Tasks

- Tạo diagram cho state graph.
- Thể hiện state, condition, retry và error feedback.
- Capture một execution trace thành công.
- Capture một execution trace có validation failure và retry.

#### Deliverables

- Mermaid diagram.
- Hình workflow dùng trong slide.
- Trace evidence cho live demo.

---

### HACK-B03: Prompt Engineering evidence

- **Priority:** P1
- **PIC gợi ý:** Prompt Engineer

#### Tasks

- Tách và mô tả system prompt, scope rules, refusal rules và few-shot examples.
- Tạo test cho tool-routing prompt khi `FIXED_TOOLS_ENABLED` bật và tắt (Dynamic-SQL tools luôn có mặt ở cả hai trạng thái).
- Test exact fixed-tool match, fixed-tool shape mismatch, raw ID lookup và plain unranked listing.
- Test broad request có ranking qualifier và không có ranking qualifier.
- Xác minh outer Agent truyền nguyên câu hỏi tự nhiên vào `answer_with_sql`, không sinh SQL trong tool argument.
- Test prompt-injection content xuất hiện trong user text, chat history, tool result và KB chunk.
- Test insight/recommendation reuse most recent relevant tool result mà không gọi lại tool không cần thiết.
- Tạo before/after example khi cải thiện prompt.

#### Deliverables

- Prompt inventory.
- Prompt test matrix.
- Hai ví dụ before/after có giải thích.

---

### HACK-B04: Verify Dynamic-SQL tool contract và routing matrix

- **Priority:** P0
- **PIC gợi ý:** AI Engineer + QA

#### Tasks

- Lập routing matrix giữa fixed business tools, `sql_db_schema`, `answer_with_sql` và `search_knowledge_base`.
- Xác minh `answer_with_sql` chỉ được dùng khi không có fixed tool nào match đúng entity, ranking/aggregation dimension và filters.
- Xác minh raw ID/name lookup và plain unranked listing route sang Dynamic-SQL khi feature flag bật.
- Xác minh exact fixed-tool match không bị route nhầm sang Dynamic-SQL.
- Test malformed table list và exception path của `_safe()`.
- Xác minh success response có `rows` và `query`; failure response có `error`.

#### Deliverables

- Tool-routing decision matrix.
- Automated tests cho tool contract.
- Demo evidence cho một exact fixed-tool case và một shape-mismatch Dynamic-SQL case.


## Workstream C – RAG, Embeddings và Knowledge Base

### HACK-C01: Audit và enrich Knowledge Base

- **Priority:** P0
- **PIC gợi ý:** RAG Engineer + Business Analyst

#### Tasks

- Kiểm tra mỗi table có description rõ ràng.
- Kiểm tra column description và relationship.
- Bổ sung metric formulas và business definitions còn thiếu.
- Bổ sung SQL idioms và sample queries cho các câu hỏi demo.
- Tránh lặp nội dung giữa KB và schema reference.

#### Deliverables

- KB coverage checklist.
- Danh sách tài liệu embedding đã cập nhật.
- Index rebuild evidence.

---

### HACK-C02: Đánh giá retrieval quality

- **Priority:** P0
- **PIC gợi ý:** RAG Engineer + QA

#### Tasks

- Chọn test questions từ bộ TC-01..58.
- Xác định expected top-k chunks.
- Đo hit rate và relevance thủ công hoặc tự động.
- Điều chỉnh chunking, metadata, top-k và threshold nếu cần.
- Kiểm tra OOS threshold không chặn nhầm câu hỏi hợp lệ.

#### Deliverables

- Retrieval evaluation report.
- Danh sách câu hỏi false-positive và false-negative.
- Config đề xuất cho demo.

---

### HACK-C03: Hiển thị source attribution rõ ràng

- **Priority:** P1
- **PIC gợi ý:** Frontend + RAG Engineer

#### Tasks

- Hiển thị `source_tables`.
- Hiển thị `kb_chunks` theo cách dễ đọc.
- Phân biệt answer từ live database và answer từ knowledge base.

#### Deliverables

- Source panel trên UI.
- Screenshot cho presentation.

---

## Workstream D – Guardrails và Responsible AI

### HACK-D01: OOS test suite

- **Priority:** P0
- **PIC gợi ý:** AI Engineer + QA

#### Tasks

- Test greeting bằng tiếng Anh và tiếng Việt: `Hello`, `Hi`, `Good morning`, `Xin chào`, `Chào bạn` và greeting kèm câu hỏi nghiệp vụ.
- Xác minh greeting-only trả welcome introduction, không trả generic OOS message và không gọi Agent/Database.
- Test câu hỏi business hợp lệ bằng tiếng Anh và tiếng Việt.
- Test lookup theo ID/name, business trend theo time window và data-driven recommendation là `IN_SCOPE`.
- Test general knowledge, coding, translation, weather và personal advice là `OUT_OF_SCOPE`.
- Test classifier `OUT_OF_SCOPE` dù similarity hoặc keyword cao để xác minh classifier verdict là authoritative.
- Test classifier `IN_SCOPE` nhưng similarity thấp, có và không có business keyword rescue.
- Test semantic similarity ở ngay dưới, bằng và trên threshold.
- Test prompt-injection patterns được chặn trước Agent.
- Ghi nhận false rejection và false acceptance.

#### Deliverables

- OOS test report.
- Threshold recommendation.
- Demo case cho accepted, clarification và rejected.

---

### HACK-D01A: Greeting Intent và Welcome Response

- **Priority:** P0
- **PIC gợi ý:** AI Engineer + Frontend + QA

#### Mục tiêu

Xử lý lời chào như một conversational intent riêng thay vì xem là `OUT_OF_SCOPE`. Điều này giúp người dùng mới hiểu chatbot là gì và có thể hỏi những nội dung nào.

#### Tasks

- Bổ sung deterministic greeting detection trước bước OOS classification.
- Hỗ trợ tối thiểu greeting tiếng Anh và tiếng Việt.
- Với greeting-only, trả welcome response gồm:
  - Tên và vai trò của Database Query Assistant.
  - Phạm vi hỗ trợ: customers, products, sales, revenue, regions, schema và business insights.
  - Hai hoặc ba câu hỏi mẫu ngắn.
- Không gọi LLM Agent, tools hoặc Database cho greeting-only.
- Với greeting kèm business question, bỏ phần greeting và tiếp tục xử lý câu hỏi nghiệp vụ bình thường.
- Không để greeting detection bypass prompt-injection detection khi input chứa cả lời chào và attack pattern.
- Chuẩn hóa response theo ngôn ngữ của user.

#### Expected Responses

**User:** `Hello`

**Expected:** Chào mừng, giới thiệu Database Query Assistant và gợi ý câu hỏi mẫu bằng tiếng Anh.

**User:** `Xin chào`

**Expected:** Chào mừng, giới thiệu phạm vi hỗ trợ và gợi ý câu hỏi mẫu bằng tiếng Việt.

**User:** `Hi, show me the top 5 products by revenue`

**Expected:** Tiếp tục business workflow và gọi đúng fixed tool, không dừng ở welcome response.

#### Deliverables

- Greeting intent rules và welcome-response template EN/VI.
- Unit tests cho greeting-only, greeting + business question và greeting + prompt injection.
- UI screenshot hoặc recording cho first-time user experience.

#### Definition of Done

- Greeting-only không bị trả generic OOS rejection.
- Greeting-only không tạo LLM/tool/database call.
- Greeting kèm câu hỏi nghiệp vụ vẫn route đúng.
- Greeting không làm giảm hiệu lực security guardrails.

---

### HACK-D02: Prompt injection và data leakage tests

- **Priority:** P0
- **PIC gợi ý:** Security + AI QA

#### Tasks

- Test các pattern: ignore instructions, jailbreak, system prompt, reveal prompt, hidden instructions và bypass security.
- Test yêu cầu hiển thị system prompt, tool schemas, credentials, configuration, stack traces hoặc private records.
- Test yêu cầu truy cập table/column ngoài phạm vi.
- Test instruction được chèn trong user text, conversation history, database field, tool result và retrieved KB context.
- Xác minh suspicious content không thay đổi role, policy, tool permissions hoặc output requirements.
- Chuẩn hóa và test exact safe refusal response khi không còn legitimate analysis.

#### Deliverables

- Adversarial test cases.
- Guardrail result matrix.
- Evidence cho blocked requests.

---

### HACK-D03: SQL safety demonstration

- **Priority:** P0
- **PIC gợi ý:** Backend + Database Engineer

#### Tasks

- Test `DELETE`, `UPDATE`, `DROP`, `ALTER`, multi-statement và query không có `LIMIT`.
- Xác minh validator chặn trước database execution.
- Xác minh read-only role là lớp bảo vệ độc lập.

#### Deliverables

- SQL safety demo script.
- Validator unit tests.
- Screenshot/log blocked query.

---

## Workstream E – Evaluation và Testing

### HACK-E01: Hoàn thiện committed pytest suite

- **Priority:** P0
- **PIC gợi ý:** QA + toàn team

#### Tasks

- Unit tests cho OOS guard, gồm classifier authority, similarity threshold, keyword rescue, EN/VI và security patterns.
- Unit tests cho prompt routing khi `FIXED_TOOLS_ENABLED` ON/OFF.
- Unit tests cho `sql_db_schema`, `answer_with_sql` và `_safe()` error contract.
- Unit tests cho SQL validator.
- Unit tests cho chart-data extraction.
- Unit tests cho business tools và error handling.
- Integration tests cho chat endpoint.
- Integration tests cho FAISS retrieval.
- E2E test cho Streamlit → FastAPI → Agent → Database.

#### Deliverables

- Committed `pytest` suite.
- Test execution report.
- Coverage report nếu có thể tạo ổn định.

#### Definition of Done

- Các critical paths có automated tests.
- Test chạy lại được trên máy demo.

---

### HACK-E02: AI evaluation dataset và scorecard

- **Priority:** P0
- **PIC gợi ý:** AI QA + Business Analyst

#### Tasks

- Chuẩn hóa test cases thành categories: fixed tool, RAG, dynamic SQL, follow-up, OOS, injection và error handling.
- Xác định expected tool hoặc expected route.
- Chấm answer correctness, source correctness và safety result.
- Ghi latency và failure reason.

#### Deliverables

- Evaluation dataset.
- Hackathon scorecard.
- Bảng pass/fail theo category.

---

### HACK-E03: Regression test cho demo cases

- **Priority:** P0
- **PIC gợi ý:** QA + Demo Team

#### Tasks

- Chạy lại toàn bộ demo questions trước buổi trình bày.
- Cố định dữ liệu demo hoặc seed data.
- Đánh dấu câu hỏi ổn định và câu hỏi có rủi ro.
- Chuẩn bị fallback answer/evidence cho lỗi external service.

#### Deliverables

- Demo regression checklist.
- Go/No-Go report.

---

## Workstream F – Frontend và Demo Experience

### HACK-F01: Hoàn thiện UI evidence

- **Priority:** P1
- **PIC gợi ý:** Frontend Engineer

#### Tasks

- Hiển thị tool route hoặc processing stage ở mức an toàn.
- Hiển thị source tables và KB chunks.
- Hiển thị chart khi `chart_data` hợp lệ.
- Hiển thị error/refusal rõ ràng.
- Kiểm tra conversation history và follow-up UX.

#### Deliverables

- Demo-ready Streamlit UI.
- Screenshots cho slide deck.

---

### HACK-F02: Streaming response

- **Priority:** P2
- **PIC gợi ý:** Frontend + Backend

#### Tasks

- Đánh giá khả năng bổ sung streaming mà không ảnh hưởng stability.
- Chỉ implement nếu không phá vỡ message metadata và tool results.

#### Deliverables

- Streaming prototype hoặc quyết định không triển khai kèm lý do.

---

### HACK-F03: Hoàn thiện và xác minh TTS; STT là Bonus

- **Priority:** P1 cho TTS verification; P3 Bonus cho STT
- **PIC gợi ý:** Frontend Engineer

#### Tasks

- Xác minh nút `🔊 Listen` hiển thị cho assistant response.
- Xác minh frontend gọi `api_client.synthesize_speech(text)`.
- Xác minh loading state, warning state và audio state hoạt động đúng.
- Xác minh API trả audio bytes định dạng WAV.
- Xác minh TTS model sẵn sàng trong môi trường demo.
- Kiểm tra text dài, ký tự đặc biệt, tiếng Anh và tiếng Việt.
- Đánh giá latency và chuẩn bị fallback khi model đang download hoặc unavailable.
- STT input chỉ thực hiện như bonus nếu các task P0 đã ổn định.

#### Deliverables

- TTS integration test evidence.
- Screenshot hoặc recording cho luồng `Listen` → synthesize → autoplay.
- TTS fallback message đã được kiểm thử.
- Optional STT prototype.

---

## Workstream G – Observability và Deployment

### HACK-G01: Agent tracing và monitoring

- **Priority:** P1
- **PIC gợi ý:** DevOps + AI Engineer

#### Tasks

- Ghi trace cho LLM calls, tool calls, retrieval và SQL workflow.
- Thu thập latency và error type.
- Che secrets và thông tin nhạy cảm trong logs.
- Chuẩn bị một trace thành công và một trace thất bại.

#### Deliverables

- Trace screenshots.
- Monitoring checklist.
- Demo evidence cho observability.

---

### HACK-G02: Reproducible demo environment

- **Priority:** P1
- **PIC gợi ý:** DevOps

#### Tasks

- Chuẩn hóa startup commands.
- Kiểm tra dependency lock/version.
- Cân nhắc Dockerfile hoặc startup script.
- Chuẩn bị fake backend/fake SQL engine làm fallback.

#### Deliverables

- One-page runbook.
- Primary và fallback startup flow.

---

### HACK-G03: CI pipeline

- **Priority:** P2
- **PIC gợi ý:** DevOps

#### Tasks

- Chạy lint và pytest khi push/merge.
- Lưu test report làm artifact nếu platform hỗ trợ.

#### Deliverables

- CI configuration.
- Successful pipeline evidence.

---

## Workstream H – Demo và Presentation

### HACK-H01: Chuẩn bị tối thiểu 11 demo scenarios

- **Priority:** P0
- **PIC gợi ý:** Business Analyst + Demo Team

| # | Scenario | Feature chính |
|---:|---|---|
| 1 | Top 5 products by revenue | LangChain, business tool, PostgreSQL |
| 2 | Follow-up: chỉ lấy khu vực Asia | Memory, multi-turn context |
| 3 | Product performance across regions | Tool Calling, chart |
| 4 | Một câu hỏi không được fixed tool hỗ trợ | Dynamic Text-to-SQL, LangGraph |
| 5 | Hỏi revenue formula hoặc table relationship | RAG, FAISS, Semantic Search |
| 6 | Yêu cầu business insight | Insight generation |
| 7 | Yêu cầu recommendation | Recommendation service |
| 8 | `Hello` / `Xin chào`, sau đó hỏi tiếp câu nghiệp vụ | Greeting Intent, welcome guidance, conversation routing |
| 9 | Câu hỏi ngoài business domain | OOS Guardrail |
| 10 | Prompt injection hoặc yêu cầu secrets | Safety Guardrail |
| 11 | Yêu cầu destructive SQL | SQL validation, read-only DB |

#### Deliverables

- Copy/paste demo script.
- Expected route/tool cho từng case.
- Expected answer characteristics.
- Fallback evidence cho từng case quan trọng.

---

### HACK-H02: Architecture story

- **Priority:** P0
- **PIC gợi ý:** Solution Architect

#### Tasks

- Chuẩn bị high-level architecture.
- Chuẩn bị LangGraph workflow.
- Chuẩn bị RAG pipeline.
- Giải thích vì sao fixed business tools và dynamic-SQL cùng tồn tại.
- Giải thích defense-in-depth cho OOS và SQL safety.

#### Deliverables

- Ba architecture diagrams.
- Talking points tối đa 60–90 giây cho mỗi diagram.

---

### HACK-H03: Hackathon evidence package

- **Priority:** P0
- **PIC gợi ý:** Presentation Team + QA

#### Tasks

- Thu thập test report.
- Thu thập evaluation scorecard.
- Thu thập screenshots và traces.
- Thu thập source file references cho từng feature.
- Chuẩn bị backup video hoặc screenshots nếu live demo lỗi.

#### Deliverables

- Evidence folder.
- Feature-to-evidence matrix.
- Backup demo package.

---

# 6. Phân công team đề xuất

| Nhóm | Phạm vi chính | Task IDs |
|---|---|---|
| Tech Lead / Architect | Baseline, architecture, integration decision | A01, H02 |
| AI Engineer | LLM, LangChain, LangGraph, prompt, OOS | A02, B01–B03, D01 |
| RAG Engineer | Embeddings, FAISS, KB, retrieval evaluation | C01–C03 |
| Backend / Database | API, DAO, SQL safety, read-only role | A01, B01, D03 |
| Frontend | Streamlit, source display, chart, optional streaming/voice | F01–F03 |
| QA / AI Evaluation | pytest, evaluation dataset, regression, adversarial tests | D01–D03, E01–E03 |
| DevOps | Tracing, runbook, fallback environment, CI | G01–G03 |
| Business / Presentation | Business story, demo script, evidence, slides | H01–H03 |

---

# 7. Thứ tự triển khai khuyến nghị

## P0 – Bắt buộc trước Hackathon

1. HACK-A01 – Baseline toàn hệ thống.
2. HACK-A02 – Chuẩn hóa real-LLM smoke-test evidence.
3. HACK-B01 – Enable và harden Dynamic-SQL.
4. HACK-C01 – Knowledge Base coverage.
5. HACK-D01/D01A/D02/D03 – OOS, greeting intent và security guardrail verification.
6. HACK-E01 – Committed pytest suite.
7. HACK-E02 – Evaluation dataset và scorecard.
8. HACK-E03 – Demo regression.
9. HACK-H01/H02/H03 – Demo, architecture story và evidence package.

## P1 – Tăng chất lượng và độ tin cậy

1. HACK-B03 – Prompt Engineering evidence.
2. HACK-C03 – Source attribution UI.
3. HACK-F01 – UI demo readiness.
4. HACK-G01 – Tracing/monitoring.
5. HACK-G02 – Reproducible environment.

## P2/P3 – Chỉ làm khi P0 ổn định

1. Streaming Response.
2. CI pipeline.
3. STT.
4. Local LLM hoặc Multi-Agent prototype.
5. Pinecone migration.

> TTS đã được triển khai và được chuyển thành task P1 để verify end-to-end, không còn là tính năng chưa có.

> **Khuyến nghị:** Không migrate từ FAISS sang Pinecone và không chuyển sang Multi-Agent chỉ để thêm tech keyword. Hai thay đổi này có integration risk cao, trong khi project hiện đã có kiến trúc Agent + LangGraph đủ mạnh. Nếu triển khai, cần chứng minh business value hoặc technical value rõ ràng.

---

# 8. Hackathon Definition of Done

Project sẵn sàng demo khi:

- End-to-end flow chạy với real LLM và database demo.
- Dynamic-SQL hoạt động qua restricted read-only role.
- OOS, prompt injection và destructive SQL đều bị chặn.
- Có automated tests cho critical paths.
- Có evaluation scorecard cho fixed tool, RAG, dynamic SQL và guardrails.
- Có 10 demo scenarios đã regression.
- Có source attribution, screenshots, logs hoặc traces làm evidence.
- TTS hoạt động end-to-end hoặc có fallback rõ ràng khi model unavailable.
- Có startup runbook và fallback demo.
- Thành viên thuyết trình giải thích được business problem, architecture, RAG pipeline, Agent workflow, safety và evaluation.

---

# 9. Deliverables cuối cùng

- `pytest` test suite và test report.
- AI evaluation dataset và scorecard.
- OOS, injection và SQL-safety evidence.
- Dynamic-SQL trace và LangGraph diagram.
- RAG retrieval report.
- Demo-ready Streamlit UI.
- Tối thiểu 11 copy/paste demo scenarios, gồm greeting flow.
- Architecture diagrams và slide talking points.
- Runbook cho primary/fallback environment.
- Hackathon evidence package.
