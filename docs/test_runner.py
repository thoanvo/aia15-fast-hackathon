import urllib.request
import json
import time
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.abspath("../src"))

from backend.services import chat_service
from langchain_app import agent
from config import settings

def send_chat(conv_id, question):
    url = "http://127.0.0.1:8000/api/v1/chat"
    payload = json.dumps({"conversation_id": conv_id, "question": question}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            elapsed = time.time() - start_time
            data = json.loads(res.read())
            conv = chat_service.get_conversation(conv_id)
            tool_results = []
            if conv.messages:
                last_msg = conv.messages[-1]
                tool_results = last_msg.tool_results
            return {
                "status_code": 200,
                "elapsed": round(elapsed, 2),
                "answer": data.get("answer", ""),
                "source_tables": data.get("source_tables", []),
                "kb_chunks": data.get("kb_chunks", []),
                "chart_data": data.get("chart_data"),
                "tool_results": tool_results
            }
    except Exception as e:
        return {
            "status_code": getattr(e, "code", 500),
            "elapsed": round(time.time() - start_time, 2),
            "error": str(e),
            "answer": "",
            "tool_results": []
        }

print("Testing send_chat with TC-01...")
res = send_chat("tc-01-test", "Show all products.")
print(json.dumps(res, indent=2))
