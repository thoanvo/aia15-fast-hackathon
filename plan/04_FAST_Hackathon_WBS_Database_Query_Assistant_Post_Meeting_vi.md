# Hackathon Work Breakdown Structure (WBS) - FAST Team

## Dự án: Database Query Assistant

## Phiên bản sau Meeting

Tài liệu này cập nhật WBS theo nội dung team đã thống nhất sau meeting. Trọng tâm được thu gọn vào:

1. Dynamic-SQL (luôn active) và routing theo `FIXED_TOOLS_ENABLED`.
2. OOS Guardrail, test verification và Welcome branch.
3. AI-assisted testing và tối thiểu 13 demo scenarios.
4. Slides và Architecture Story.
5. Deployment chỉ là Optional.

---

# 1. Mục tiêu Hackathon

Hoàn thiện và trình diễn **Database Query Assistant** cho phép business users:

- Đặt câu hỏi bằng natural language.
- Truy vấn dữ liệu PostgreSQL/Neon thông qua fixed business tools hoặc Dynamic-SQL.
- Tra cứu schema, metric và business knowledge bằng RAG, FAISS và Embeddings.
- Nhận insight, recommendation, chart, source attribution và TTS.
- Được bảo vệ bởi OOS Guardrail, Prompt Injection Protection và SQL Safety.

Nguyên tắc triển khai:

- Ưu tiên demo ổn định và có evidence.
- Không thêm công nghệ chỉ để tăng số lượng tech keywords.
- Mỗi feature trong demo phải có test hoặc evidence xác minh.
- AI có thể hỗ trợ tạo và review test cases, nhưng kết quả cuối phải được kiểm chứng bằng automated test, execution log hoặc human review.

---

# 2. Phạm vi đã chốt sau Meeting

| Workstream | Phạm vi đã chốt | PIC | Priority |
|---|---|---|---|
| Workstream B | Dynamic-SQL, feature flag, tool contract, routing matrix và Prompt Engineering evidence | ThoanVTT | P0 |
| Workstream D | OOS technical verification và Welcome branch | PhuongLV5 | P0 |
| Workstream E/H | AI-assisted testing, regression và tối thiểu 13 demo scenarios | AnNTV | P0 |
| Workstream H | Slides, Architecture Story; có thể dành riêng một slide High-Level Architecture | TanPNM1 | P0 |
| Workstream G | Deployment | Chưa bắt buộc phân công | Optional |

---

# 3. Workstream B - AI Core và Dynamic-SQL

## HACK-B01: Bật và harden Dynamic-SQL

- **PIC:** ThoanVTT.
- **Priority:** P0.

### Mục tiêu

Bảo đảm Dynamic-SQL (luôn được đăng ký trên Agent, không phụ thuộc feature flag) hoạt động đúng, an toàn khi truy vấn database và không ảnh hưởng đến fixed business tools.

### Tasks

- Provision và verify restricted read-only DB role (`READONLY_DATABASE_URL`) trước khi demo/development.
- Verify schema reflection và semantic context retrieval từ FAISS.
- Verify LangGraph workflow:
  - Discover schema.
  - Generate SQL.
  - Validate SQL.
  - Execute SQL.
  - Retry có giới hạn khi validation hoặc execution thất bại.
- Verify SQL Safety:
  - SELECT-only.
  - Single statement.
  - Mandatory `LIMIT`.
  - Không thực thi destructive SQL.
- Verify success response có `rows` và `query`.
- Verify failure response có structured `error` và không làm crash Agent turn.
- Chuẩn bị ít nhất một successful trace và một retry/error trace.

### Deliverables

- Dynamic-SQL demo-ready configuration.
- SQL Safety test evidence.
- Successful và retry/error execution traces.
- Danh sách câu hỏi chỉ Dynamic-SQL mới đáp ứng được.

### Definition of Done

- Dynamic-SQL chạy bằng read-only connection.
- Unsafe SQL bị chặn trước execution.
- Fixed business tools vẫn hoạt động bình thường song song với Dynamic-SQL (cả hai luôn active khi `FIXED_TOOLS_ENABLED=true`).
- Có evidence cho generate → validate → execute → retry.

---

## HACK-B03: Prompt Engineering Evidence và Feature-Flag Behavior

- **PIC:** ThoanVTT.
- **Priority:** P0.

### Mục tiêu

Chuẩn hóa và chứng minh routing behavior khi `FIXED_TOOLS_ENABLED` bật hoặc tắt, trong khi Dynamic-SQL tools (`sql_db_schema`, `answer_with_sql`) luôn được đăng ký và sẵn sàng sử dụng ở cả hai trạng thái.

### Expected Routing khi `FIXED_TOOLS_ENABLED=true`

```text
User Question
    ↓
Check scope and safety
    ↓
Scan fixed business tools
    ├── Exact fixed-tool shape match
    │       → Call fixed business tool
    │
    └── No exact fixed-tool match
            → Call answer_with_sql
            → LangGraph generate → validate → execute → retry
```

### Expected Routing khi `FIXED_TOOLS_ENABLED=false`

```text
User Question
    ↓
Check scope and safety
    ↓
Skip fixed business tools (not registered)
    ↓
Call answer_with_sql
    ↓
LangGraph generate → validate → execute → retry
```

### Điểm cần adjustment và verify

- `FIXED_TOOLS_ENABLED` chỉ điều khiển đăng ký 16 fixed business tools.
- Dynamic-SQL tools (`sql_db_schema`, `answer_with_sql`) luôn được đăng ký, không phụ thuộc flag.
- Khi flag ON:
  - Exact fixed-tool match vẫn ưu tiên fixed tool.
  - Chỉ fallback sang `answer_with_sql` khi không có fixed tool khớp đúng question shape.
- Khi flag OFF:
  - Không có fixed tool nào được đăng ký.
  - Mọi câu hỏi dữ liệu (kể cả plain listing, ranking, ID lookup) đều route sang `answer_with_sql`.
- Cần review lại broad request behavior như “Show all customers” để thống nhất expected result khi flag OFF (route sang `answer_with_sql` như một plain listing, không ranking).

### Test Matrix bắt buộc

| Case | Flag | Expected Route |
|---|---:|---|
| Top 5 products by revenue | ON | `get_top_products` |
| Top 5 products by revenue | OFF | `answer_with_sql` |
| Top regions by distinct customer count | ON | `answer_with_sql` |
| Top regions by distinct customer count | OFF | `answer_with_sql` |
| What is the name of region 1? | ON | `answer_with_sql` |
| What is the name of region 1? | OFF | `answer_with_sql` |
| How is profit margin calculated? | ON | `search_knowledge_base` |
| How is profit margin calculated? | OFF | `search_knowledge_base` |
| Show all customers | ON | Plain-listing Dynamic-SQL route (`answer_with_sql`) |
| Show all customers | OFF | `answer_with_sql` (không có fixed tool nào để fallback) |

### Prompt Engineering Evidence

- System scope và authority rules.
- Tool-routing instructions.
- Few-shot examples cho fixed tool, RAG và Dynamic-SQL.
- Broad request rules cho flag ON/OFF.
- Prompt Injection handling.
- Insight/recommendation prompts tái sử dụng tool result.
- Before/after evidence cho ít nhất một routing issue đã được cải thiện.

### Deliverables

- Prompt inventory.
- Feature-flag behavior specification.
- ON/OFF routing test matrix.
- Before/after prompt evidence.
- Test result chứng minh Dynamic-SQL tools luôn sẵn sàng bất kể feature flag.

### Definition of Done

- Routing behavior ON/OFF được document và test.
- Không có case exact fixed-tool match bị route sang Dynamic-SQL khi flag ON.
- Dynamic-SQL tools luôn được đăng ký và sẵn sàng ở cả flag ON và OFF.
- Fixed business tools chỉ được đăng ký khi flag ON.

---

## HACK-B04: Verify Dynamic-SQL Tool Contract và Routing Matrix

- **PIC:** ThoanVTT.
- **Priority:** P0.

### Tasks

- Verify `sql_db_schema(table_names)`:
  - Nhận comma-separated table names.
  - Trả schema information hợp lệ.
  - Trả structured error khi input không hợp lệ hoặc dependency lỗi.
- Verify `answer_with_sql(question)`:
  - Chỉ nhận natural-language question.
  - Không nhận SQL do outer Agent tự viết.
  - Trả `{rows, query}` khi thành công.
  - Trả `{error}` khi thất bại.
- Verify `_safe()` error contract không làm crash Agent turn.
- Lập decision matrix giữa:
  - Fixed business tools.
  - `search_knowledge_base`.
  - `sql_db_schema`.
  - `answer_with_sql`.
- Verify routing cho exact match, shape mismatch, raw ID lookup, plain listing và schema question.
- Verify tool registration list khi `FIXED_TOOLS_ENABLED=true/false`.

### Deliverables

- Tool contract checklist.
- Automated routing tests.
- Tool registration evidence cho flag ON/OFF.
- Demo evidence cho:
  - Một exact fixed-tool case.
  - Một Dynamic-SQL fallback case.
  - Một flag-OFF case (chỉ Dynamic-SQL tools được đăng ký).

---

## HACK-B02: LangGraph Workflow Evidence

- **PIC:** ThoanVTT phối hợp TanPNM1.
- **Priority:** P1.

### Tasks

- Export LangGraph workflow diagram.
- Chuẩn bị execution trace thành công.
- Chuẩn bị trace có validation failure và retry.
- Cung cấp technical talking points cho Architecture Story.

### Deliverables

- LangGraph diagram.
- Trace screenshots.
- Technical notes cho slide.

---

# 4. Workstream D - Guardrails và Responsible AI

## Owner

- **PIC:** PhuongLV5.
- **Priority:** P0.

## HACK-D01: Verify OOS Technical Logic

### Tasks

- Review OOS decision flow:
  - Security pattern detection.
  - LLM intent classification.
  - Embedding similarity.
  - Business keyword rescue.
  - OOS logging và rejection response.
- Test English và Vietnamese inputs.
- Test boundary ở dưới, bằng và trên `OOS_SIMILARITY_THRESHOLD`.
- Verify classifier verdict behavior khi similarity hoặc keyword có kết quả khác nhau.
- Test business recommendations và trend questions không bị reject nhầm.
- Test general knowledge, translation, coding, weather và personal advice là OOS.
- Tổng hợp false acceptance và false rejection.

### Deliverables

- OOS test suite.
- OOS decision matrix.
- Threshold verification report.
- False-positive/false-negative report.

---

## HACK-D02: Apply Welcome Branch

### Mục tiêu

Greeting-only không trả generic OOS response mà trả welcome introduction và hướng dẫn người dùng.

### Expected Flow

```text
User Input
    ↓
Security Pattern Check
    ↓
Greeting Detection
    ├── Greeting only
    │       → Welcome response EN/VI
    │       → No Agent, Tool or Database call
    │
    └── Greeting + business question
            → Continue normal OOS and Agent routing
```

### Tasks

- Apply deterministic greeting detection trước OOS classification.
- Hỗ trợ tối thiểu:
  - `Hello`.
  - `Hi`.
  - `Good morning`.
  - `Xin chào`.
  - `Chào bạn`.
- Welcome response cần gồm:
  - Chatbot role.
  - Supported business domains.
  - Hai hoặc ba example questions.
- Greeting + business question phải tiếp tục normal routing.
- Greeting + Prompt Injection không được bypass security detection.
- Chuẩn hóa response theo ngôn ngữ user.

### Deliverables

- Welcome branch implementation.
- Welcome templates EN/VI.
- Unit tests và UI evidence.

### Definition of Done

- Greeting-only không trả OOS response.
- Greeting-only không gọi Agent, Tool hoặc Database.
- Greeting + business question route đúng.
- Greeting không bypass security guardrails.

---

## HACK-D03: Prompt Injection và SQL Safety Verification

### Tasks

- Test Prompt Injection patterns:
  - Ignore instructions.
  - Reveal system prompt.
  - Show secrets hoặc hidden configuration.
  - Bypass security.
- Test injected instructions trong:
  - User input.
  - Conversation history.
  - Tool result.
  - Database field.
  - KB chunk.
- Test SQL Safety:
  - `DELETE`.
  - `UPDATE`.
  - `DROP`.
  - `ALTER`.
  - Multi-statement.
  - Query không có `LIMIT`.
- Verify read-only DB role là lớp bảo vệ độc lập.

### Deliverables

- Adversarial test cases.
- Guardrail pass/fail matrix.
- Blocked request evidence.

---

# 5. Workstream E - AI-Assisted Testing và Evaluation

## Chủ trì

- **PIC chính cho demo test preparation:** AnNTV.
- **Phối hợp:** ThoanVTT, PhuongLV5 và các module owners.
- **Priority:** P0.

## HACK-E01: Dùng AI hỗ trợ tạo và review test cases

### Nguyên tắc

AI được dùng để:

- Sinh test variations.
- Review coverage.
- Suggest expected route.
- Phát hiện missing edge cases.
- Nhóm test theo feature.

AI không được dùng như bằng chứng duy nhất cho correctness. Kết quả phải được xác minh bằng:

- `pytest`.
- API/UI execution.
- Tool/trace evidence.
- Human review cho business correctness.

### Tasks

- Dùng AI review test coverage từ bộ test hiện tại.
- Sinh thêm variations theo English/Vietnamese và paraphrase.
- Xác định expected route/tool cho từng test.
- Review test data để không yêu cầu dữ liệu không tồn tại.
- Chuyển các critical cases thành automated tests.
- Ghi rõ AI-generated, human-reviewed và execution-verified status.

### Deliverables

- AI-assisted test inventory.
- Reviewed expected-results matrix.
- Automated test report.

---

## HACK-E02: Evaluation Scorecard

### Categories

- Fixed Tool Routing.
- Dynamic-SQL Routing.
- Feature Flag ON/OFF.
- RAG Retrieval.
- Multi-turn Context.
- OOS.
- Welcome Branch.
- Prompt Injection.
- SQL Safety.
- TTS.
- Error Handling.

### Metrics

- Route correctness.
- Answer correctness.
- Source correctness.
- Guardrail result.
- Execution success/failure.
- Latency nếu thu thập được.

### Deliverables

- Evaluation dataset.
- Pass/fail scorecard.
- Failure reason summary.

---

# 6. Workstream H - Demo và Presentation

## HACK-H01: Chuẩn bị tối thiểu 13 Demo Scenarios

- **PIC:** AnNTV.
- **Priority:** P0.

| # | Demo Scenario | Expected Feature/Route |
|---:|---|---|
| 1 | `Hello` hoặc `Xin chào` | Welcome branch, không gọi Agent/DB |
| 2 | Top 5 products by revenue | Fixed business tool, PostgreSQL |
| 3 | `Only in Asia` | Multi-turn context và filter reuse |
| 4 | Product performance across regions | Fixed tool và chart |
| 5 | What insights can you provide? | Reuse tool result, Insight Generation |
| 6 | What should we promote next month? | Recommendation Generation |
| 7 | How is profit margin calculated? | RAG, FAISS, Semantic Search |
| 8 | Top regions by distinct customer count, flag ON | Dynamic-SQL, LangGraph |
| 9 | Top regions by distinct customer count, flag OFF | Unsupported capability, không gọi Dynamic-SQL |
| 10 | Exact fixed-tool query khi flag ON | Fixed tool vẫn được ưu tiên |
| 11 | Weather/general question | OOS Guardrail |
| 12 | Prompt Injection hoặc destructive SQL | Security và SQL Safety |
| 13 | Bấm `Listen` trên response | TTS, WAV audio playback |

### Mỗi scenario phải có

- Copy/paste user input.
- Precondition và feature-flag state.
- Expected route/tool.
- Expected result characteristics.
- Actual result.
- Pass/fail status.
- Screenshot, log hoặc trace nếu cần.
- Fallback evidence cho live demo.

### Demo Run đề xuất

Live demo chính nên chọn 6–8 scenarios ổn định nhất. Các scenario còn lại dùng backup screenshots hoặc video để tránh vượt thời gian.

### Deliverables

- Tối thiểu 13 demo scripts.
- Demo regression report.
- Stable demo sequence.
- Backup demo package.

---

## HACK-H02: Slides và Architecture Story

- **PIC:** TanPNM1.
- **Priority:** P0.

### Scope

- Chuẩn bị slide deck và presentation flow.
- Có thể chừa riêng slide **High-Level Architecture**.
- Phối hợp với module owners để lấy diagram, screenshots, traces và technical evidence.

### Slide Outline đề xuất

1. Project Introduction.
2. Business Problem.
3. Our Solution.
4. AI Engineering Technology Stack.
5. High-Level Architecture.
6. Intelligent Tool Routing và `FIXED_TOOLS_ENABLED` ON/OFF.
7. RAG và Knowledge Base.
8. Dynamic Text-to-SQL với LangGraph.
9. Guardrails, Welcome Branch và Responsible AI.
10. Live Demo.
11. Testing, Evaluation và Evidence.
12. Business Value, Lessons Learned và Next Steps.

### Architecture Story cần làm rõ

- Streamlit → FastAPI → OOS Guard → LangChain Agent.
- Fixed business tools, RAG tool và Dynamic-SQL tool.
- Feature flag controls fixed business tools; Dynamic-SQL tools luôn active, không bị flag disable.
- LangGraph workflow cho generate → validate → execute → retry.
- FAISS Knowledge Base được dùng cho RAG và SQL grounding.
- Defense-in-depth cho Prompt Injection và SQL Safety.

### Deliverables

- Slide deck.
- High-Level Architecture diagram.
- LangGraph workflow diagram.
- RAG pipeline diagram.
- Speaker notes và timing.
- Backup slides cho test evidence và deployment optional.

---

## HACK-H03: Hackathon Evidence Package

- **PIC:** AnNTV phối hợp TanPNM1 và module owners.
- **Priority:** P0.

### Tasks

- Thu thập test reports.
- Thu thập ON/OFF routing evidence.
- Thu thập OOS và Welcome branch evidence.
- Thu thập screenshots và traces.
- Thu thập source-file references.
- Chuẩn bị backup video hoặc screenshots.

### Deliverables

- Feature-to-evidence matrix.
- Evidence folder.
- Backup demo package.

---

# 7. Workstream G - Deployment

## Status

- **Priority:** Optional.
- Không chặn Hackathon demo.
- Chỉ thực hiện khi tất cả P0 tasks đã ổn định.

## Optional Deployment Scope

- Frontend: Streamlit Community Cloud.
- Backend: Render Python Web Service.
- Không bắt buộc Docker.
- Có thể dùng GitHub-based auto-deployment.

## Optional Tasks

- Xác minh `requirements.txt` và Python version.
- Deploy FastAPI Backend lên Render.
- Deploy Streamlit Frontend lên Community Cloud.
- Cấu hình `BACKEND_URL` và secrets.
- Chạy post-deployment smoke tests.
- Chuẩn bị rollback hoặc fallback về local demo.

## Decision Rule

Nếu deployment gây ảnh hưởng đến Dynamic-SQL, Guardrails, tests hoặc demo stability thì team dừng deployment và sử dụng local environment đã regression.

---

# 8. Assignment Summary

| Task | PIC | Support | Priority |
|---|---|---|---|
| HACK-B01 - Enable và harden Dynamic-SQL | ThoanVTT | Backend/Database | P0 |
| HACK-B03 - Prompt Engineering và Flag ON/OFF | ThoanVTT | QA | P0 |
| HACK-B04 - Dynamic-SQL Contract và Routing Matrix | ThoanVTT | QA | P0 |
| HACK-B02 - LangGraph Evidence | ThoanVTT | TanPNM1 | P1 |
| Workstream D - OOS, Welcome, Injection, Safety | PhuongLV5 | QA | P0 |
| AI-assisted Testing và 13 Demo Scenarios | AnNTV | Module Owners | P0 |
| Slides và Architecture Story | TanPNM1 | Module Owners | P0 |
| Deployment | Optional | DevOps | Optional |

---

# 9. Execution Priority

## P0 - Bắt buộc

1. B01: Dynamic-SQL hardening.
2. B03: Feature flag ON/OFF adjustment và Prompt Engineering evidence.
3. B04: Tool contract và routing matrix.
4. Workstream D: OOS verification và Welcome branch.
5. AI-assisted testing và execution verification.
6. Tối thiểu 13 demo scenarios.
7. Slides, Architecture Story và evidence package.

## P1 - Sau khi P0 ổn định

1. LangGraph traces và diagram polishing.
2. Additional evaluation metrics.
3. UI evidence improvements.
4. TTS regression và fallback polishing.

## Optional

1. Streamlit Community Cloud deployment.
2. Render Backend deployment.
3. GitHub-based auto-deployment.

---

# 10. Hackathon Definition of Done

Project sẵn sàng demo khi:

- `FIXED_TOOLS_ENABLED=true` ưu tiên exact fixed-tool match và chỉ fallback Dynamic-SQL khi cần.
- `FIXED_TOOLS_ENABLED=false` không đăng ký fixed tools; Dynamic-SQL tools vẫn luôn hoạt động.
- ON/OFF routing matrix đã được automated hoặc execution-verified.
- Dynamic-SQL chạy bằng read-only DB role và vượt qua SQL Safety tests.
- Welcome branch hoạt động cho English/Vietnamese greeting.
- OOS, Prompt Injection và SQL Safety tests pass.
- Tối thiểu 13 demo scenarios đã regression.
- AI-generated test suggestions đã được human-review và execution-verified.
- Slide deck và High-Level Architecture hoàn chỉnh.
- Có evidence và backup cho các critical demo cases.
- Deployment không phải điều kiện bắt buộc.

---

# 11. Deliverables cuối cùng

- Dynamic-SQL ON/OFF behavior specification.
- Prompt Engineering evidence.
- Tool contract và routing test matrix.
- OOS test report và Welcome branch evidence.
- AI-assisted test inventory và execution report.
- Tối thiểu 13 demo scripts.
- Demo regression report.
- Slide deck và architecture diagrams.
- Hackathon evidence package.
- Optional deployment URL và smoke-test report nếu deployment được thực hiện.
