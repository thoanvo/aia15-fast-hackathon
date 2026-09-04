# WBS Deployment – Option B: Streamlit Community Cloud + Render

## Mục tiêu

Triển khai nhanh môi trường Hackathon trực tiếp từ GitHub, không cần Docker:

```text
GitHub Repository
    ├── Streamlit Community Cloud
    │       └── Frontend: src/frontend/app.py
    │
    └── Render Web Service
            └── Backend: FastAPI + Uvicorn
                     │
                     ├── PostgreSQL / Neon
                     ├── OpenAI-compatible endpoint
                     └── FAISS / Embedding resources
```

---

## HACK-G02: Chuẩn bị source cho Native Deployment

- **Priority:** P1
- **PIC:** DevOps + Backend + Frontend

### Tasks

- Xác minh `requirements.txt` chứa đầy đủ dependencies cho Backend, Frontend, FAISS, Embeddings và TTS.
- Pin các package quan trọng để hạn chế khác biệt giữa local và cloud.
- Xác minh Python version tương thích với toàn bộ dependencies.
- Cập nhật Frontend để đọc `BACKEND_URL` từ environment hoặc Streamlit secrets.
- Đảm bảo Backend bind vào `0.0.0.0` và port từ biến môi trường của Render.
- Bổ sung health endpoint cho Backend.
- Xác định chiến lược tạo hoặc rebuild FAISS index khi Backend khởi động.
- Không commit `.env`, API key, database credentials hoặc certificates.

### Deliverables

- Deployment-ready `requirements.txt`.
- Backend health endpoint.
- Environment variable checklist.
- Local smoke-test report sử dụng cloud-like commands.

---

## HACK-G03: GitHub Actions CI

- **Priority:** P1
- **PIC:** DevOps + QA

### Tasks

- Tạo `.github/workflows/ci.yml`.
- Chạy trên `pull_request` và `push` vào main branch.
- Cấu hình Python 3.11 và pip cache.
- Cài dependencies từ `requirements.txt`.
- Chạy unit, integration và critical smoke tests.
- Kiểm tra import cho FastAPI, Streamlit, FAISS, Embeddings và TTS.
- Lưu test report làm workflow artifact nếu phù hợp.
- Cấu hình Render auto-deploy sau khi CI checks pass.

### Deliverables

- Passing GitHub Actions workflow.
- CI evidence cho slide/demo.
- Branch protection hoặc documented merge rule.

---

## HACK-G04: Deploy FastAPI Backend lên Render

- **Priority:** P1
- **PIC:** DevOps + Backend

### Render Configuration

```text
Service Type: Web Service
Runtime: Python 3
Root Directory: repository root hoặc cấu hình phù hợp với repository
Build Command: pip install -r requirements.txt
Start Command: cd src && uvicorn app:app --host 0.0.0.0 --port $PORT
Health Check Path: endpoint health của Backend
```

### Tasks

- Kết nối Render với GitHub repository và branch triển khai.
- Tạo Render Web Service sử dụng Python native runtime.
- Cấu hình Build Command và Start Command.
- Cấu hình environment variables và secrets trên Render.
- Provision restricted read-only PostgreSQL role (`READONLY_DATABASE_URL`) — bắt buộc vì Dynamic-SQL tools luôn được đăng ký trên Agent, không có feature flag để tắt.
- Xác minh kết nối Neon và OpenAI-compatible endpoint.
- Xác minh FAISS index load hoặc rebuild thành công.
- Xác minh TTS endpoint trả WAV audio.
- Cấu hình auto-deploy sau khi GitHub CI checks pass.
- Ghi lại Backend public HTTPS URL để cấu hình Frontend.

### Render Secrets

- `DATABASE_URL`.
- Read-only database connection nếu project dùng biến riêng.
- `OPENAI_API_KEY`.
- Các credentials hoặc certificates cần thiết khác.

### Render Non-secret Variables

- `OPENAI_BASE_URL`.
- `OPENAI_MODEL`.
- `OPENAI_VERIFY_SSL`.
- `VECTOR_STORE_DIR`.
- `EMBEDDING_MODEL_NAME`.
- `OOS_SIMILARITY_THRESHOLD`.
- `FIXED_TOOLS_ENABLED`.

### Deliverables

- Render Backend URL.
- Passing health check.
- Backend deployment log hoặc screenshot.
- Backend smoke-test report.

---

## HACK-G05: Deploy Streamlit Frontend lên Community Cloud

- **Priority:** P1
- **PIC:** DevOps + Frontend

### Streamlit Configuration

```text
Repository: GitHub repository hiện tại
Branch: deployment branch
Entrypoint: src/frontend/app.py
Python Version: phiên bản tương thích đã xác minh
Secret/Variable: BACKEND_URL=<Render Backend HTTPS URL>
```

### Tasks

- Kết nối Streamlit Community Cloud với GitHub repository.
- Chọn branch và entrypoint `src/frontend/app.py`.
- Chọn Python version phù hợp.
- Cấu hình `BACKEND_URL` bằng Render Backend HTTPS URL.
- Xác minh Frontend không sử dụng `localhost` trong môi trường cloud.
- Kiểm tra API timeout và friendly error khi Backend chưa sẵn sàng.
- Xác minh source attribution, charts và TTS audio playback.
- Ghi lại Streamlit public URL cho buổi Hackathon.

### Deliverables

- Streamlit public demo URL.
- Frontend deployment log hoặc screenshot.
- Frontend-to-Backend connectivity evidence.

---

## HACK-G06: Post-deployment Smoke Test

- **Priority:** P0 trước buổi demo
- **PIC:** QA + toàn team

### Test Cases

1. `Hello` và `Xin chào` trả welcome introduction.
2. Fixed business tool trả dữ liệu từ Neon.
3. Follow-up question giữ conversation context.
4. RAG retrieval trả KB context phù hợp.
5. Dynamic-SQL chạy bằng read-only role nếu được bật.
6. Destructive SQL bị chặn.
7. OOS question trả rejection phù hợp.
8. Prompt Injection bị chặn.
9. TTS trả và phát WAV audio.
10. Source attribution và chart hiển thị đúng.
11. Frontend xử lý Backend error/timeout thân thiện.

### Deliverables

- Post-deployment test report.
- Screenshot hoặc recording cho critical scenarios.
- Go/No-Go checklist.

---

## HACK-G07: Rollback và Demo Fallback

- **Priority:** P1
- **PIC:** DevOps + Demo Team

### Tasks

- Ghi lại commit ổn định dùng cho demo.
- Chuẩn bị rollback Render và Streamlit về commit ổn định.
- Giữ local deployment commands làm fallback.
- Chuẩn bị `dev_fake_backend.py` hoặc backup recording nếu external service lỗi.
- Không dùng fake backend như evidence cho real database workflow.

### Deliverables

- Rollback guide.
- Stable commit/tag.
- Backup demo package.

---

## Definition of Done

- GitHub Actions CI pass trước deployment.
- Render Backend health check thành công.
- Streamlit Frontend gọi được Render Backend qua HTTPS.
- Secrets không xuất hiện trong repository hoặc logs.
- Neon, OpenAI-compatible endpoint, FAISS và TTS hoạt động trên cloud.
- Critical Hackathon scenarios vượt qua post-deployment smoke test.
- Có rollback và fallback rõ ràng.
