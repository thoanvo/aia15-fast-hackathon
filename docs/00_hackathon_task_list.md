# Hackathon Task List

| Module | Task | PIC |
|----------|----------|----------|
| Dynamic-SQL Hardening | Provision và verify restricted read-only database role | |
| Dynamic-SQL Hardening | Verify schema reflection và semantic context retrieval từ FAISS | |
| Dynamic-SQL Hardening | Verify LangGraph workflow: Discover Schema → Generate SQL → Validate SQL → Execute SQL → Retry | |
| Dynamic-SQL Hardening | Verify SQL Safety (SELECT-only, Single Statement, Mandatory LIMIT, Block Destructive SQL) | |
| Dynamic-SQL Hardening | Verify success response trả về rows và query | |
| Dynamic-SQL Hardening | Verify failure response trả về structured error | |
| Dynamic-SQL Hardening | Thu thập successful trace và retry/error trace | |
| Feature Flag & Prompt Engineering | Điều chỉnh FIXED_TOOLS_ENABLED chỉ kiểm soát fixed business tools | |
| Feature Flag & Prompt Engineering | Đảm bảo Dynamic-SQL tools luôn được đăng ký | |
| Feature Flag & Prompt Engineering | Verify routing behavior khi flag ON/OFF | |
| Feature Flag & Prompt Engineering | Xây dựng và verify routing test matrix | |
| Feature Flag & Prompt Engineering | Hoàn thiện prompt inventory và routing instructions | |
| Feature Flag & Prompt Engineering | Chuẩn bị before/after prompt engineering evidence | |
| Tool Contract & Routing Validation | Verify contract của sql_db_schema | |
| Tool Contract & Routing Validation | Verify contract của answer_with_sql | |
| Tool Contract & Routing Validation | Verify _safe() error handling | |
| Tool Contract & Routing Validation | Xây dựng decision matrix giữa Fixed Tool, RAG và Dynamic-SQL | |
| Tool Contract & Routing Validation | Verify tool registration khi flag ON/OFF | |
| Tool Contract & Routing Validation | Tạo automated routing tests | |
| LangGraph Evidence | Export LangGraph workflow diagram | |
| LangGraph Evidence | Thu thập execution traces | |
| LangGraph Evidence | Chuẩn bị retry/error workflow evidence | |
| LangGraph Evidence | Cung cấp technical talking points cho architecture slide | |
| OOS Verification | Review và verify toàn bộ OOS decision flow | |
| OOS Verification | Test English và Vietnamese queries | |
| OOS Verification | Test threshold boundary cases | |
| OOS Verification | Verify classifier, similarity và keyword rescue behavior | |
| OOS Verification | Đánh giá false positive và false negative | |
| Welcome Branch | Implement greeting detection trước OOS | |
| Welcome Branch | Thiết kế welcome response EN/VI | |
| Welcome Branch | Hỗ trợ greeting-only và greeting + business question | |
| Welcome Branch | Verify không bypass security guardrails | |
| Welcome Branch | Viết unit tests và thu thập UI evidence | |
| Prompt Injection & SQL Safety | Test prompt injection attacks | |
| Prompt Injection & SQL Safety | Test hidden instructions từ tool result, KB và database fields | |
| Prompt Injection & SQL Safety | Test SQL safety rules | |
| Prompt Injection & SQL Safety | Verify read-only database role hoạt động đúng | |
| Prompt Injection & SQL Safety | Chuẩn bị blocked request evidence | |
| AI-Assisted Testing | Dùng AI review coverage của test suite hiện tại | |
| AI-Assisted Testing | Sinh thêm test variations EN/VI | |
| AI-Assisted Testing | Xác định expected route cho từng test case | |
| AI-Assisted Testing | Review business correctness | |
| AI-Assisted Testing | Chuyển critical cases thành automated tests | |
| AI-Assisted Testing | Gắn nhãn AI-generated / Human-reviewed / Execution-verified | |
| Evaluation Framework | Xây dựng evaluation dataset | |
| Evaluation Framework | Đánh giá Fixed Tool Routing | |
| Evaluation Framework | Đánh giá Dynamic-SQL Routing | |
| Evaluation Framework | Đánh giá Feature Flag ON/OFF | |
| Evaluation Framework | Đánh giá RAG Retrieval | |
| Evaluation Framework | Đánh giá Multi-turn Context | |
| Evaluation Framework | Đánh giá OOS, Welcome Branch, Prompt Injection, SQL Safety và TTS | |
| Evaluation Framework | Tổng hợp scorecard và failure analysis | |
| Demo Scenarios | Chuẩn bị tối thiểu 13 demo scenarios | |
| Demo Scenarios | Xây dựng demo script và expected results | |
| Demo Scenarios | Thực hiện demo regression | |
| Demo Scenarios | Chuẩn bị backup screenshots và videos | |
| Demo Scenarios | Chọn 6-8 demo cases ổn định cho live demo | |
| Slides & Architecture Story | Hoàn thiện slide deck hackathon | |
| Slides & Architecture Story | Thiết kế High-Level Architecture diagram | |
| Slides & Architecture Story | Thiết kế LangGraph workflow diagram | |
| Slides & Architecture Story | Thiết kế RAG pipeline diagram | |
| Slides & Architecture Story | Hoàn thiện speaker notes | |
| Slides & Architecture Story | Chuẩn bị backup slides | |
| Evidence Package | Thu thập test reports | |
| Evidence Package | Thu thập routing evidence ON/OFF | |
| Evidence Package | Thu thập OOS và Welcome evidence | |
| Evidence Package | Thu thập screenshots và traces | |
| Evidence Package | Chuẩn bị feature-to-evidence matrix | |
| Evidence Package | Chuẩn bị backup demo package | |
| Deployment (Optional) | Verify requirements và Python version | |
| Deployment (Optional) | Deploy FastAPI Backend lên Render | |
| Deployment (Optional) | Deploy Streamlit Frontend lên Community Cloud | |
| Deployment (Optional) | Cấu hình environment variables và secrets | |
| Deployment (Optional) | Thực hiện smoke tests sau deployment | |
| Deployment (Optional) | Chuẩn bị rollback/fallback plan | |