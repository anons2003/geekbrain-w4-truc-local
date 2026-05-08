from __future__ import annotations

import re
import sqlite3
from datetime import date
from typing import Any


# L3 không để LLM tự đoán số liệu; cost/metrics phải lấy từ SQLite database.
DEFAULT_DB_PATH = "data_package/scripts/geekbrain.db"
MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


class ToolError(RuntimeError):
    pass


class GeekBrainTools:
    # Tool wrapper tối giản: hiện tại chỉ có database query read-only và danh sách service.
    def __init__(self, db_path: str, api_base: str = "local") -> None:
        self.db_path = db_path

    def database_query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        # Mỗi query mở/đóng connection riêng để demo stateless và dễ gọi từ FastAPI.
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def list_services(self) -> list[str]:
        # Service list lấy từ database để không phải sửa code khi data package đổi.
        rows = self.database_query(
            """
            SELECT service FROM monthly_costs
            UNION
            SELECT service FROM daily_metrics
            UNION
            SELECT service FROM incidents
            ORDER BY service
            """
        )
        return [row["service"] for row in rows]


def money(value: float) -> str:
    # Format tiền nhất quán cho câu trả lời L3.
    return f"${value:,.0f}"


def parse_service(tools: GeekBrainTools, question: str) -> str | None:
    # Extract service name từ câu hỏi để route dynamic, không hardcode theo exact sentence.
    q = question.lower()
    for service in tools.list_services():
        if service.lower() in q:
            return service
    return None


def available_years(tools: GeekBrainTools) -> list[int]:
    rows = tools.database_query(
        """
        SELECT substr(month, 1, 4) AS year FROM monthly_costs
        UNION
        SELECT substr(date, 1, 4) AS year FROM daily_metrics
        ORDER BY year DESC
        """
    )
    return [int(row["year"]) for row in rows if row["year"]]


def default_year(tools: GeekBrainTools) -> int:
    years = available_years(tools)
    return years[0] if years else date.today().year


def parse_month(tools: GeekBrainTools, question: str) -> str | None:
    # Chuẩn hóa tháng tự nhiên sang format trong database.
    q = question.lower()
    iso_match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", q)
    if iso_match:
        return iso_match.group(0)
    year_match = re.search(r"\b(20\d{2})\b", q)
    year = int(year_match.group(1)) if year_match else default_year(tools)
    for name, month in MONTH_NAMES.items():
        if re.search(rf"\b{name}\b", q):
            return f"{year}-{month:02d}"
    return None


def parse_quarter(tools: GeekBrainTools, question: str) -> tuple[str, str] | None:
    # Q1/Q4 được chuyển thành khoảng tháng để query SQL.
    q = question.lower()
    match = re.search(r"\bq([1-4])(?:\s*(20\d{2}))?\b", q)
    if match:
        quarter = int(match.group(1))
        year = int(match.group(2)) if match.group(2) else default_year(tools)
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        return (f"{year}-{start_month:02d}", f"{year}-{end_month:02d}")
    return None


def latest_metric_window(tools: GeekBrainTools, month: str | None) -> tuple[str, str, str]:
    if month:
        return f"{month}-01", f"{month}-31", month
    rows = tools.database_query("SELECT MAX(date) AS latest_date FROM daily_metrics")
    latest_date = rows[0]["latest_date"]
    if not latest_date:
        raise ToolError("No daily metrics available")
    latest_month = latest_date[:7]
    return f"{latest_month}-01", latest_date, latest_month


def answer_dynamic_l3(tools: GeekBrainTools, question: str) -> dict[str, Any]:
    # Dynamic L3 planner: parse intent rồi gọi DB, trả answer + evidence + pipeline trace.
    q = question.lower()
    service = parse_service(tools, question)
    month = parse_month(tools, question)
    quarter = parse_quarter(tools, question)

    if "cost" in q and quarter:
        # Câu hỏi total cost theo quarter: có thể hỏi toàn hệ thống hoặc một service cụ thể.
        start, end = quarter
        if service:
            rows = tools.database_query(
                "SELECT SUM(total_cost) AS total FROM monthly_costs WHERE service = ? AND month BETWEEN ? AND ?",
                (service, start, end),
            )
            return {
                "intent": "service_quarter_total_cost",
                "answer": f"{service}'s total cost from {start} through {end} was {money(rows[0]['total'])}.",
                "tools": ["Database Query"],
                "evidence": {"sql_result": rows, "service": service, "window": [start, end]},
                "pipeline_steps": [
                    {"step": "Parse intent", "detail": "service quarter total cost"},
                    {"step": "Execute database query", "detail": "SUM(total_cost)"},
                    {"step": "Format answer", "detail": "No LLM numeric inference used."},
                ],
            }
        rows = tools.database_query("SELECT SUM(total_cost) AS total FROM monthly_costs WHERE month BETWEEN ? AND ?", (start, end))
        return {
            "intent": "quarter_total_cost",
            "answer": f"GeekBrain's total infrastructure cost from {start} through {end} was {money(rows[0]['total'])}.",
            "tools": ["Database Query"],
            "evidence": {"sql_result": rows, "window": [start, end]},
        }

    if "cost" in q and month and ("highest" in q or "most" in q):
        # Câu hỏi ranking cost theo tháng: dùng ORDER BY trong SQL để tránh LLM suy luận sai số.
        rows = tools.database_query(
            "SELECT service, total_cost FROM monthly_costs WHERE month = ? ORDER BY total_cost DESC LIMIT 1",
            (month,),
        )
        row = rows[0]
        return {
            "intent": "highest_monthly_cost",
            "answer": f"{row['service']} had the highest total cost in {month} at {money(row['total_cost'])}.",
            "tools": ["Database Query"],
            "evidence": {"sql_result": rows, "service": row["service"], "month": month},
            "pipeline_steps": [
                {"step": "Parse intent", "detail": "highest monthly cost"},
                {"step": "Execute database query", "detail": "ORDER BY total_cost DESC LIMIT 1"},
                {"step": "Format answer", "detail": "No LLM numeric inference used."},
            ],
        }

    if "requests per minute" in q or "rpm" in q:
        # Câu hỏi live/metric: nếu không nêu tháng thì dùng tháng mới nhất có trong daily_metrics.
        start_date, end_date, label = latest_metric_window(tools, month)
        rows = tools.database_query(
            """
            SELECT service, AVG(requests_per_minute) AS rpm
            FROM daily_metrics
            WHERE date BETWEEN ? AND ?
            GROUP BY service
            ORDER BY rpm DESC
            LIMIT 1
            """,
            (start_date, end_date),
        )
        row = rows[0]
        return {
            "intent": "highest_rpm",
            "answer": f"{row['service']} had the highest average request volume for {label} at about {row['rpm']:,.0f} rpm.",
            "tools": ["Database Query"],
            "evidence": {"sql_result": rows, "window": [start_date, end_date]},
        }

    raise ToolError(f"No L3 template matched: {question}")


def infer_route(question: str) -> str:
    # Giữ hàm legacy để không phá import cũ; route thật nằm ở answer_dynamic_l3.
    raise ToolError(f"No legacy route matched: {question}")
