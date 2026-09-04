# frontend/components/

Reusable Streamlit rendering functions used by `../pages/`.

| File | Purpose |
|---|---|
| `chat_interface.py` | `render_message_thread(messages)`, `render_chat_input()`, `render_suggested_questions()`. |
| `response_display.py` | `render_answer()`, `render_insights()`, `render_recommendations()`, and a `render_chart()` hook (currently a no-op — no chart generation exists in the backend yet). |
| `conversation_history.py` | `render_history_sidebar(questions)` — past user questions + a "Clear chat" button. |
