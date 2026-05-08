from __future__ import annotations

import re
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import các helper local thay vì để toàn bộ logic trong FastAPI.
# L2 file phụ trách retrieval/prompt, L3 file phụ trách tool query.
from scripts.l2_conflict_aware_rag_truc import (  # noqa: E402
    DEFAULT_KB_ID,
    DEFAULT_MODEL_ID,
    DEFAULT_PROFILE,
    DEFAULT_REGION,
    SYSTEM_PROMPT,
    ask_claude,
    build_context,
    classify_status,
    local_keyword_results,
    merge_results,
    retrieve_chunks,
    source_name,
)
from scripts.l3_tool_augmented_rag_truc import DEFAULT_DB_PATH, GeekBrainTools, ToolError, answer_dynamic_l3  # noqa: E402


KB_DIR = ROOT / "data_package" / "knowledge_base"
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def load_team_directory() -> dict[str, dict[str, str]]:
    # Team directory được đọc từ team_*.md, không viết cố định team/lead trong code.
    directory: dict[str, dict[str, str]] = {}
    for path in KB_DIR.glob("team_*.md"):
        text = path.read_text()
        team_match = re.search(r"^#\s+(Team .+)$", text, re.MULTILINE)
        lead_match = re.search(r"## Lead\s+\n+\*\*([^*]+)\*\*", text)
        services_section = re.search(r"## Services Owned\s+(.*?)(?:\n## |\Z)", text, re.DOTALL)
        if not (team_match and lead_match and services_section):
            continue
        team = team_match.group(1).strip()
        lead = lead_match.group(1).strip()
        for service in re.findall(r"-\s+\*\*([^*]+)\*\*", services_section.group(1)):
            directory[service.strip()] = {"team": team, "lead": lead, "source": path.name}
    return directory


SERVICE_TEAM = load_team_directory()

# Memory demo lưu trong RAM theo session_id. Đủ cho local demo; production nên chuyển sang DynamoDB/Redis.
SESSIONS: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    question: str
    mode: str = "auto"
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    mode: str
    answer: str
    tools: list[str]
    routing_decision: str = ""
    pipeline_steps: list[dict[str, Any]] = Field(default_factory=list)
    llm_input: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)


def get_session(session_id: str | None) -> tuple[str, dict[str, Any]]:
    # Nếu request chưa có session_id thì tạo session mới cho cuộc hội thoại L4.
    sid = session_id or str(uuid.uuid4())
    return sid, SESSIONS.setdefault(sid, {"turns": [], "state": {}})


def remember(session: dict[str, Any], question: str, answer: str, updates: dict[str, Any]) -> None:
    # Chỉ giữ compact memory và vài lượt gần nhất để tránh nhồi toàn bộ history vào prompt.
    session.setdefault("state", {}).update({k: v for k, v in updates.items() if v is not None})
    session.setdefault("turns", []).append({"user": question, "answer": answer, "updates": updates})
    session["turns"] = session["turns"][-6:]


def update_memory_from_result(session: dict[str, Any], question: str, answer: str, evidence: dict[str, Any] | None = None) -> None:
    # Rút entity quan trọng từ kết quả để follow-up có thể hiểu "that service", "that month".
    updates: dict[str, Any] = {}
    evidence = evidence or {}
    service = evidence.get("service")
    if not service:
        for name in SERVICE_TEAM:
            if name.lower() in question.lower() or name in answer:
                service = name
                break
    if service in SERVICE_TEAM:
        updates["last_service"] = service
        updates["last_team"] = SERVICE_TEAM[service]["team"]
        updates["last_team_lead"] = SERVICE_TEAM[service]["lead"]
    if evidence.get("month"):
        updates["last_month"] = evidence["month"]
    incident_match = re.search(r"\bINC-\d+\b", answer)
    if incident_match:
        incident_id = incident_match.group(0)
        updates["last_incident"] = incident_id
        incident_service = find_incident_service(incident_id)
        if incident_service:
            updates["last_service"] = incident_service
    remember(session, question, answer, updates)


def compact_memory(session: dict[str, Any]) -> dict[str, Any]:
    # Đây là phần memory thật sự được đưa vào prompt/trace, không phải toàn bộ session thô.
    state = session.get("state", {})
    keys = ["last_service", "last_month", "last_team", "last_team_lead", "last_incident", "last_deadline", "last_deadline_label"]
    return {"state": {key: state[key] for key in keys if key in state}, "recent_turns": session.get("turns", [])[-3:]}


def resolve_followup(question: str, session: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    # Biến câu follow-up mơ hồ thành câu có ngữ cảnh rõ hơn trước khi retrieve/gọi tool.
    state = session.get("state", {})
    refs: dict[str, Any] = {}
    parts = [question]
    if state.get("last_service"):
        refs["that service"] = state["last_service"]
        parts.append(f"Service: {state['last_service']}.")
    if state.get("last_month"):
        refs["that month"] = state["last_month"]
        parts.append(f"Month: {state['last_month']}.")
    if state.get("last_incident"):
        refs["same issue"] = state["last_incident"]
        parts.append(f"Incident: {state['last_incident']}.")
    return " ".join(parts), refs


def is_followup(question: str) -> bool:
    # Heuristic đơn giản để nhận diện câu hỏi phụ thuộc lượt trước.
    q = question.lower()
    return bool(re.search(r"\b(it|its|that|this|their|they|same issue|that month|that service)\b", q) or "which team" in q or "overdue" in q)


def find_incident_service(incident_id: str) -> str | None:
    # Resolve incident -> service từ database trước, fallback sang metadata trong postmortem markdown.
    db_path = ROOT / DEFAULT_DB_PATH
    if db_path.exists():
        rows = GeekBrainTools(str(db_path)).database_query("SELECT service FROM incidents WHERE incident_id = ?", (incident_id,))
        if rows:
            return rows[0]["service"]
    for path in KB_DIR.glob(f"postmortem_{incident_id.replace('-', '')}*.md"):
        text = path.read_text()
        match = re.search(r"^service:\s*(.+)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def infer_year_from_text(text: str) -> int:
    match = re.search(r"\b(20\d{2})\b", text)
    return int(match.group(1)) if match else date.today().year


def parse_due_date(raw_due: str, text: str) -> str | None:
    # Chuyển due date trong markdown từ dạng chữ hoặc ISO sang ISO date.
    clean = raw_due.strip()
    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", clean)
    if iso_match:
        return iso_match.group(0)
    match = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:,\s*(20\d{2}))?\b", clean)
    if not match:
        return None
    month = MONTHS.get(match.group(1).lower())
    if not month:
        return None
    year = int(match.group(3)) if match.group(3) else infer_year_from_text(text)
    return date(year, month, int(match.group(2))).isoformat()


def postmortem_deadline(incident_id: str) -> dict[str, Any] | None:
    # Lookup deadline trong postmortem markdown; không khóa vào một incident/date cụ thể.
    for path in KB_DIR.glob(f"postmortem_{incident_id.replace('-', '')}*.md"):
        text = path.read_text()
        for line in text.splitlines():
            if line.startswith("|") and "review" in line.lower():
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if len(cells) < 5 or cells[0] in {"#", "---"}:
                    continue
                due = parse_due_date(cells[3], text)
                if due:
                    return {"source": path.name, "action": cells[1], "owner": cells[2], "due": due, "status": cells[4]}
    return None


def rag_answer(question: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    vector_results: list[dict[str, Any]] = []
    try:
        # L1/L2 path chính: Bedrock Knowledge Base Retrieve trả về raw chunks.
        vector_results = retrieve_chunks(DEFAULT_KB_ID, question, DEFAULT_PROFILE, DEFAULT_REGION, 10)
    except Exception:
        # Nếu AWS retrieval lỗi, vẫn dùng BM25 local để trả về evidence thay vì câu trả lời cố định.
        vector_results = []
    # BM25 supplement giúp kéo các file có exact keyword như service name, incident id, version.
    bm25_results = local_keyword_results(question, str(ROOT / "data_package" / "knowledge_base"), 8)
    results = merge_results(vector_results, bm25_results)
    context = build_context(results)
    if session:
        # Với L4, compact memory được prepend vào context để resolve đại từ/follow-up.
        context = f"SESSION MEMORY:\n{compact_memory(session)}\n\n{context}"
    try:
        # Prompt được tự build để kiểm soát citation/conflict rules thay vì dùng RetrieveAndGenerate.
        answer = ask_claude(question, context, DEFAULT_PROFILE, DEFAULT_REGION, DEFAULT_MODEL_ID)
    except Exception:
        answer = extractive_fallback_answer(results)
    return {
        "answer": answer,
        "tools": ["Bedrock Knowledge Base Retrieve", "Local BM25 Supplement", "Claude Sonnet 4"],
        "sources": [{"source": source_name(r), "status": classify_status(source_name(r), r.get("content", {}).get("text", "")), "score": round(float(r.get("score", 0)), 4)} for r in results[:12]],
        "llm_input": {"system_prompt": SYSTEM_PROMPT, "user_question": question, "context_preview": context[:5000]},
        "pipeline_steps": [
            {"step": "Retrieve from Bedrock KB", "detail": "top_k=10"},
            {"step": "Add BM25 supplement", "detail": "Local BM25 over markdown docs."},
            {"step": "Merge/rerank", "detail": "Archived sources demoted."},
            {"step": "Generate answer", "detail": "Claude or extractive retrieval fallback."},
        ],
    }


def extractive_fallback_answer(results: list[dict[str, Any]]) -> str:
    # Không hardcode fact. Nếu Claude lỗi, chỉ báo top evidence để user/trainer thấy dữ liệu đã retrieve.
    if not results:
        return "Bedrock generation is unavailable and no local evidence was retrieved for this question."
    source_lines = []
    for result in results[:3]:
        source = source_name(result)
        text = " ".join(result.get("content", {}).get("text", "").split())
        source_lines.append(f"- {source}: {text[:360]}")
    return "Bedrock generation is unavailable. Retrieved evidence:\n" + "\n".join(source_lines)


def l4_answer(question: str, session: dict[str, Any], tools: GeekBrainTools) -> dict[str, Any]:
    # L4 xử lý multi-turn: đọc memory trước, resolve reference, rồi mới chọn retrieval/tool.
    if not is_followup(question):
        raise ToolError("Not a follow-up")
    state = session.get("state", {})
    resolved, refs = resolve_followup(question, session)
    q = question.lower()
    if "which team" in q and state.get("last_service"):
        # Câu "Which team is responsible?" dùng last_service trong memory và team_*.md đã parse.
        service = state["last_service"]
        info = SERVICE_TEAM.get(service)
        if not info:
            raise ToolError("No team metadata for remembered service")
        return {
            "answer": f"{service} is owned by {info['team']}, led by {info['lead']}.",
            "tools": ["Memory", "Team Directory"],
            "sources": [{"source": info["source"], "status": "unknown", "score": 1.0}],
            "evidence": {"resolved_question": resolved, "references": refs, "team_directory": info},
            "updates": {"last_team": info["team"], "last_team_lead": info["lead"]},
            "pipeline_steps": [{"step": "Read compact memory", "detail": compact_memory(session)}, {"step": "Resolve references", "detail": refs}, {"step": "Use team directory", "detail": info}],
        }
    if "overdue" in q and state.get("last_incident"):
        # Câu deadline dùng incident đã nhớ từ lượt trước để tìm đúng postmortem.
        deadline = postmortem_deadline(state["last_incident"])
        if not deadline:
            raise ToolError("No postmortem deadline")
        due = date.fromisoformat(deadline["due"])
        today = date.today()
        days = (today - due).days
        overdue_text = "past due" if days > 0 else "not overdue"
        return {
            "answer": f"Based on the postmortem action item, {deadline['action']} was due on {deadline['due']}. Its status is {deadline['status']}, so it is {overdue_text} as of {today.isoformat()} ({abs(days)} days {'after' if days > 0 else 'before'} the due date).",
            "tools": ["Memory", "Postmortem File Lookup", "Date Reasoning"],
            "sources": [{"source": deadline["source"], "status": "unknown", "score": 1.0}],
            "evidence": {"resolved_question": resolved, "references": refs, "deadline": deadline, "days_overdue": days},
            "updates": {"last_deadline": deadline["due"], "last_deadline_label": deadline["action"]},
            "pipeline_steps": [{"step": "Read compact memory", "detail": compact_memory(session)}, {"step": "Find postmortem deadline", "detail": deadline}, {"step": "Compare deadline to date", "detail": today.isoformat()}],
        }
    result = rag_answer(resolved, session)
    # Nếu không match rule đặc biệt, dùng RAG nhưng vẫn truyền câu đã resolve + memory.
    result["tools"] = ["Memory", *result["tools"]]
    result["evidence"] = {"resolved_question": resolved, "references": refs}
    result["pipeline_steps"] = [{"step": "Read compact memory", "detail": compact_memory(session)}, {"step": "Resolve references", "detail": refs}, *result["pipeline_steps"]]
    return result


def mentioned_service_from_tools(tools: GeekBrainTools, question: str) -> str | None:
    # Dùng danh sách service từ SQLite, không viết route theo một câu mẫu duy nhất.
    q = question.lower()
    for service in tools.list_services():
        if service.lower() in q:
            return service
    return None


def service_operational_evidence(tools: GeekBrainTools, service: str) -> dict[str, Any]:
    # Thu thập evidence có cấu trúc cho câu điều tra sức khỏe dịch vụ.
    metrics = tools.database_query(
        """
        SELECT date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent
        FROM daily_metrics
        WHERE service = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (service,),
    )
    targets = tools.database_query(
        "SELECT metric, target, measurement_window FROM sla_targets WHERE service = ? ORDER BY metric",
        (service,),
    )
    incidents = tools.database_query(
        "SELECT incident_id, date, severity, root_cause, resolution, team_responsible FROM incidents WHERE service = ? ORDER BY date DESC LIMIT 3",
        (service,),
    )
    return {"service": service, "latest_metrics": metrics, "sla_targets": targets, "recent_incidents": incidents}


def bonus_b(question: str, tools: GeekBrainTools) -> dict[str, Any]:
    # Bonus B: agent reasoning dùng plan + evidence thật từ DB/KB, không trả answer cố định.
    service = mentioned_service_from_tools(tools, question)
    if not service or not re.search(r"\b(healthy|health|reliability|assess|investigate)\b", question.lower()):
        raise ToolError("Not Bonus B")
    evidence = service_operational_evidence(tools, service)
    retrieval = rag_answer(f"{question}\nFocus service: {service}. Include source citations.", None)
    investigation_context = (
        f"Structured evidence:\n{evidence}\n\n"
        f"Retrieved context preview:\n{retrieval['llm_input'].get('context_preview', '')}"
    )
    investigation_prompt = (
        f"{question}\n\n"
        "Produce a concise structured reliability assessment. "
        "Use only the structured evidence and retrieved context. Cite source document names when using documents."
    )
    try:
        answer = ask_claude(investigation_prompt, investigation_context, DEFAULT_PROFILE, DEFAULT_REGION, DEFAULT_MODEL_ID)
    except Exception:
        answer = extractive_fallback_answer([
            {"localSource": "structured_operational_evidence", "content": {"text": str(evidence)}, "score": 1.0},
            *local_keyword_results(question, str(KB_DIR), 2),
        ])
    return {
        "answer": answer,
        "tools": ["Agent Plan", "Service Metrics", "Database Query", *retrieval["tools"]],
        "sources": retrieval["sources"],
        "evidence": evidence,
        "llm_input": {"system_prompt": SYSTEM_PROMPT, "user_question": investigation_prompt, "context_preview": investigation_context[:5000]},
        "pipeline_steps": [
            {"step": "Plan investigation", "detail": f"Assess {service} using metrics, SLA targets, incidents, and KB docs."},
            {"step": "Collect evidence", "detail": "Query SQLite metrics/incidents and retrieve KB context."},
            {"step": "Assess health", "detail": "Compare latest metrics with targets and incident context."},
            {"step": "Produce report", "detail": "Claude generates a structured reliability assessment from evidence."},
        ],
    }


app = FastAPI(title="W4 GeekBrain AI Q&A")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
static_dir = ROOT / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "kb_id": DEFAULT_KB_ID, "model_id": DEFAULT_MODEL_ID, "database": str(ROOT / DEFAULT_DB_PATH)}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Một endpoint duy nhất cho UI. Auto mode thử route theo thứ tự: Bonus B -> L4 -> L3 -> L1/L2 RAG.
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    session_id, session = get_session(request.session_id)
    tools = GeekBrainTools(str(ROOT / DEFAULT_DB_PATH))

    for handler, mode, routing in (
        # Thứ tự này cố ý: câu điều tra/memory/tool nên được xử lý trước RAG mặc định.
        (lambda q: bonus_b(q, tools), "Bonus B agent reasoning", "Matched open-ended investigation route."),
        (lambda q: l4_answer(q, session, tools), "L4 retrieval/tools + memory", "Resolved follow-up references from compact session memory."),
        (lambda q: answer_dynamic_l3(tools, q), "L3 tools", "Matched dynamic L3 tool planner."),
    ):
        try:
            result = handler(question)
            update_memory_from_result(session, question, result["answer"], result.get("evidence", {}))
            if result.get("updates"):
                session["state"].update(result["updates"])
            return ChatResponse(session_id=session_id, mode=f"{mode} ({result.get('intent', '')})".strip(), answer=result["answer"], tools=result.get("tools", []), routing_decision=routing, pipeline_steps=result.get("pipeline_steps", []), sources=result.get("sources", []), evidence=result.get("evidence", {}), llm_input=result.get("llm_input", {}), memory=session)
        except ToolError:
            pass

    result = rag_answer(question, session)
    update_memory_from_result(session, question, result["answer"])
    return ChatResponse(session_id=session_id, mode="L1/L2 RAG", answer=result["answer"], tools=result["tools"], routing_decision="Used Bedrock KB vector retrieval plus local BM25 supplement.", pipeline_steps=result["pipeline_steps"], sources=result["sources"], evidence={}, llm_input=result["llm_input"], memory=session)
