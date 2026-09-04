import sys
import os
import time
import json
from unittest.mock import patch

# Ensure src is in Python path
sys.path.insert(0, os.path.abspath("../src"))

from langchain_app import agent
from langchain_app.tools.business_tools import get_business_tools
from langchain_app.tools.retrieval_tool import get_retrieval_tool
from langchain_app.tools.sql_tools import get_sql_tools
from config import settings

def call_agent(question, chat_history=None):
    start_t = time.time()
    executor = agent.build_agent_executor()
    res = agent.run_turn(executor, question, chat_history=chat_history)
    elapsed = time.time() - start_t
    return {
        "elapsed": round(elapsed, 2),
        "answer": res.get("answer", ""),
        "source_tables": res.get("source_tables", []),
        "tool_results": res.get("tool_results", []),
        "kb_chunks": res.get("kb_chunks", []),
        "chart_data": res.get("chart_data")
    }

def main():
    print("=== STARTING BATCH 2 (TC-59..TC-94 & DEMO QUESTIONS) ===")
    results = []

    # -------------------------------------------------------------
    # 11. FIXED TOOL COVERAGE (TC-59..TC-80)
    # -------------------------------------------------------------
    fixed_tool_tcs = [
        ("TC-59", "What are the top 5 products by revenue?", "get_top_products", {"limit": 5}),
        ("TC-60", "What are the top 3 products by revenue in Europe?", "get_top_products", {"limit": 3, "region": "Europe"}),
        ("TC-61", "Who are our top 5 customers by revenue?", "get_top_customers", {"limit": 5}),
        ("TC-62", "How is each region performing in revenue and profit?", "get_region_performance", {}),
        ("TC-63", "Show the monthly sales trend.", "get_sales_trend", {"period": "month"}),
        ("TC-64", "Show the yearly sales trend for Asia.", "get_sales_trend", {"period": "year", "region": "Asia"}),
        ("TC-65", "Give me a profit analysis broken down by customer.", "get_profit_analysis", {"dimension": "customer"}),
        ("TC-66", "What are our key business metrics?", "get_summary_kpi", {}),
        ("TC-67", "What was our KPI summary between 2025-01-01 and 2025-03-31?", "get_summary_kpi", {"date_from": "2025-01-01", "date_to": "2025-03-31"}),
        ("TC-68", "Which products sold the most units?", "get_top_products_by_quantity", {"limit": 5}),
        ("TC-69", "Which products are the most profitable?", "get_top_products_by_profit", {"limit": 5}),
        ("TC-70", "How do our product categories compare in revenue and profit?", "get_category_performance", {}),
        ("TC-71", "Which customer segment generates the most revenue?", "get_segment_performance", {}),
        ("TC-72", "How does the Laptop perform across different regions?", "get_product_region_performance", {"product_name": "Laptop"}),
        ("TC-73", "What has Acme Corp purchased?", "get_customer_purchase_history", {"customer_name": "Acme Corp"}),
        ("TC-74", "Which products have the weakest profit margins?", "get_low_margin_products", {"limit": 5}),
        ("TC-75", "Summarize sales between 2025-01-01 and 2025-03-31.", "get_sales_by_date_range", {"date_from": "2025-01-01", "date_to": "2025-03-31"}),
        ("TC-76", "What is our month-over-month revenue growth?", "get_month_over_month_growth", {}),
        ("TC-77", "Summarize repeat customers by region.", "get_repeat_customer_summary", {}),
        ("TC-78", "Show the top 150 products by revenue.", "get_top_products", {"limit": 100}), # validation path
        ("TC-79", "Show the top -5 products by revenue.", "get_top_products", {}), # validation path
        ("TC-80", "What has NonexistentCustomerXYZ purchased?", "get_customer_purchase_history", {"customer_name": "NonexistentCustomerXYZ"}),
    ]

    for tc_id, question, expected_tool, expected_args in fixed_tool_tcs:
        print(f"Running {tc_id}: {question}")
        res = call_agent(question)
        tools_called = [t["tool"] for t in res["tool_results"]]
        passed = expected_tool in tools_called if expected_tool else len(res["answer"]) > 0
        actual_args = {}
        for t in res["tool_results"]:
            if t["tool"] == expected_tool:
                actual_args = t["args"]

        results.append({
            "id": tc_id,
            "category": "11. Fixed Tool Coverage",
            "question": question,
            "expected_tool": expected_tool,
            "expected_args": expected_args,
            "actual_tools": tools_called,
            "actual_args": actual_args,
            "elapsed": res["elapsed"],
            "passed": passed,
            "answer_snippet": res["answer"][:150] + "..." if len(res["answer"]) > 150 else res["answer"]
        })

    # -------------------------------------------------------------
    # 12. FIXED TOOL FEATURE FLAG (TC-81..TC-94)
    # -------------------------------------------------------------
    print("Running TC-81 & TC-82: Tool registration inspection...")
    # TC-81: FIXED_TOOLS_ENABLED=True
    with patch("langchain_app.agent.FIXED_TOOLS_ENABLED", True):
        tools_on = agent.get_tools()
        count_on = len(tools_on)
        passed_81 = (count_on == 19)
        results.append({
            "id": "TC-81",
            "category": "12. Fixed Tool Feature Flag",
            "scenario": "FIXED_TOOLS_ENABLED=true tool count",
            "expected_count": 19,
            "actual_count": count_on,
            "passed": passed_81,
            "tools_list": [t.name for t in tools_on]
        })

    # TC-82: FIXED_TOOLS_ENABLED=False
    with patch("langchain_app.agent.FIXED_TOOLS_ENABLED", False):
        tools_off = agent.get_tools()
        count_off = len(tools_off)
        passed_82 = (count_off == 3)
        results.append({
            "id": "TC-82",
            "category": "12. Fixed Tool Feature Flag",
            "scenario": "FIXED_TOOLS_ENABLED=false tool count",
            "expected_count": 3,
            "actual_count": count_off,
            "passed": passed_82,
            "tools_list": [t.name for t in tools_off]
        })

    # Routing behavior per flag state (TC-83..TC-92)
    routing_tcs = [
        ("TC-83", "Top 5 products by revenue.", True, "get_top_products"),
        ("TC-84", "Top 5 products by revenue.", False, "answer_with_sql"),
        ("TC-85", "Top regions by distinct customer count.", True, "answer_with_sql"),
        ("TC-86", "Top regions by distinct customer count.", False, "answer_with_sql"),
        ("TC-87", "What is the name of region 1?", True, "answer_with_sql"),
        ("TC-88", "What is the name of region 1?", False, "answer_with_sql"),
        ("TC-89", "Show all customers.", True, "answer_with_sql"),
        ("TC-90", "Show all customers.", False, "answer_with_sql"),
        ("TC-91", "What columns are available in the Customers table?", True, "sql_db_schema"),
        ("TC-92", "What columns are available in the Customers table?", False, "sql_db_schema"),
        ("TC-93", "Top 10 products by profit.", True, "get_top_products_by_profit"),
        ("TC-94", "Products ranked by quantity.", True, "get_top_products_by_quantity"),
    ]

    for tc_id, question, flag_state, expected_tool in routing_tcs:
        print(f"Running {tc_id} (Flag={flag_state}): {question}")
        with patch("langchain_app.agent.FIXED_TOOLS_ENABLED", flag_state):
            res = call_agent(question)
            tools_called = [t["tool"] for t in res["tool_results"]]
            passed = (expected_tool in tools_called)
            results.append({
                "id": tc_id,
                "category": "12. Fixed Tool Feature Flag",
                "question": question,
                "flag_state": "ON" if flag_state else "OFF",
                "expected_tool": expected_tool,
                "actual_tools": tools_called,
                "elapsed": res["elapsed"],
                "passed": passed,
                "answer_snippet": res["answer"][:150] + "..." if len(res["answer"]) > 150 else res["answer"]
            })

    # -------------------------------------------------------------
    # DEMO QUESTIONS (Demo-01..Demo-10)
    # -------------------------------------------------------------
    demo_qs = [
        ("Demo-01", "What were the top-selling products last quarter?"),
        ("Demo-02", "Which region generated the highest revenue?"),
        ("Demo-03", "Who are our top 5 customers?"),
        ("Demo-04", "Give me insights about sales performance."),
        ("Demo-05", "Compare revenue by region."),
        ("Demo-06", "Suggest actions to improve sales."),
        ("Demo-07", "Which product should we promote next month?"),
        ("Demo-08", "Explain how customer spending is calculated."),
        ("Demo-09", "Show a revenue trend chart."),
        ("Demo-10", "Why do you think the North region is outperforming others?"),
    ]

    for demo_id, question in demo_qs:
        print(f"Running {demo_id}: {question}")
        res = call_agent(question)
        passed = len(res["answer"].strip()) > 0
        results.append({
            "id": demo_id,
            "category": "13. Demo Questions",
            "question": question,
            "elapsed": res["elapsed"],
            "passed": passed,
            "chart_data_present": res["chart_data"] is not None,
            "answer_snippet": res["answer"][:150] + "..." if len(res["answer"]) > 150 else res["answer"]
        })

    # Save batch 2
    with open("e2e_batch2_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Batch 2 finished. Completed {len(results)} test cases.")

if __name__ == "__main__":
    main()
