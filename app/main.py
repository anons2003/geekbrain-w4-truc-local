from __future__ import annotations

import json
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
import boto3

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


class RouteDecision(BaseModel):
    route: str
    reason: str
    rewritten_question: str
    service: str | None = None


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


def call_router_model(prompt: str) -> str:
    # Router chỉ chọn route, không được sinh câu trả lời cuối.
    session = boto3.Session(profile_name=DEFAULT_PROFILE, region_name=DEFAULT_REGION) if DEFAULT_PROFILE else boto3.Session(region_name=DEFAULT_REGION)
    client = session.client("bedrock-runtime")
    response = client.converse(
        modelId=DEFAULT_MODEL_ID,
        system=[{"text": "You are a routing controller. Return only compact JSON. Do not answer the user's question."}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.0},
    )
    return response["output"]["message"]["content"][0]["text"]


def parse_router_json(raw: str) -> dict[str, Any]:
    # Claude đôi khi bọc JSON bằng text; chỉ lấy object JSON đầu tiên.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ToolError("Router did not return JSON")
    return json.loads(match.group(0))


def ai_route(question: str, session: dict[str, Any], tools: GeekBrainTools) -> RouteDecision:
    # AI router thay cho hard match: model quyết định dùng RAG, DB tool, memory hay agent reasoning.
    services = tools.list_services()
    prompt = f"""
User question:
{question}

Compact session memory:
{json.dumps(compact_memory(session), ensure_ascii=False)}

Known services from database:
{json.dumps(services)}

Available routes:
- rag: simple or conflict-aware knowledge-base retrieval questions.
- l3_tools: questions requiring numeric, structured, cost, metric, SLA, incident, or database-backed answers.
- l4_memory: follow-up questions that depend on previous turns, pronouns, remembered service/month/team/incident, or conversation context.
- agent_reasoning: open-ended investigation or reliability assessment that needs a plan and multiple evidence sources.

Return only JSON with this schema:
{{"route":"rag|l3_tools|l4_memory|agent_reasoning","reason":"short reason","rewritten_question":"standalone question if useful, otherwise original","service":"service name if one is relevant, otherwise null"}}
"""
    try:
        data = parse_router_json(call_router_model(prompt))
    except Exception:
        data = {"route": "rag", "reason": "Router unavailable; defaulted to RAG.", "rewritten_question": question, "service": None}
    route = data.get("route", "rag")
    if route not in {"rag", "l3_tools", "l4_memory", "agent_reasoning"}:
        route = "rag"
    rewritten = data.get("rewritten_question") or question
    service = data.get("service")
    if service not in services:
        service = None
    return RouteDecision(route=route, reason=data.get("reason", ""), rewritten_question=rewritten, service=service)


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
        context = f"CURRENT DATE: {date.today().isoformat()}\nSESSION MEMORY:\n{compact_memory(session)}\n\n{context}"
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
    resolved, refs = resolve_followup(question, session)
    result = rag_answer(resolved, session)
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


def bonus_b(question: str, tools: GeekBrainTools, routed_service: str | None = None) -> dict[str, Any]:
    # Bonus B: agent reasoning dùng plan + evidence thật từ DB/KB, không trả answer cố định.
    service = routed_service or mentioned_service_from_tools(tools, question)
    if not service:
        raise ToolError("Agent reasoning route requires a service in the routed question")
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


def forced_route(mode: str, question: str) -> RouteDecision | None:
    # UI vẫn cho phép ép mode khi debug; auto thì để AI router quyết định.
    if mode == "rag":
        return RouteDecision(route="rag", reason="User selected RAG only mode.", rewritten_question=question)
    if mode == "tools":
        return RouteDecision(route="l3_tools", reason="User selected Tools only mode.", rewritten_question=question)
    return None


def execute_route(route: RouteDecision, session: dict[str, Any], tools: GeekBrainTools) -> tuple[str, dict[str, Any]]:
    # Sau khi router quyết định, executor chỉ chạy route tương ứng.
    question = route.rewritten_question
    if route.route == "agent_reasoning":
        result = bonus_b(question, tools, route.service)
        return "Bonus B agent reasoning", result
    if route.route == "l4_memory":
        result = l4_answer(question, session, tools)
        return "L4 retrieval/tools + memory", result
    if route.route == "l3_tools":
        result = answer_dynamic_l3(tools, question)
        return "L3 tools", result
    return "L1/L2 RAG", rag_answer(question, session)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # Một endpoint duy nhất cho UI. Auto mode để Claude route trước, rồi backend executor chạy route đó.
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    session_id, session = get_session(request.session_id)
    tools = GeekBrainTools(str(ROOT / DEFAULT_DB_PATH))
    route = forced_route(request.mode, question) or ai_route(question, session, tools)
    try:
        mode, result = execute_route(route, session, tools)
        routing_decision = f"AI router selected {route.route}: {route.reason}"
    except ToolError as error:
        route = RouteDecision(route="rag", reason=f"Selected route could not execute ({error}); fell back to RAG.", rewritten_question=question)
        mode, result = execute_route(route, session, tools)
        routing_decision = route.reason

    update_memory_from_result(session, question, result["answer"], result.get("evidence", {}))
    if result.get("updates"):
        session["state"].update(result["updates"])
    pipeline_steps = [
        {"step": "AI route request", "detail": route.model_dump()},
        *result.get("pipeline_steps", []),
    ]
    return ChatResponse(
        session_id=session_id,
        mode=f"{mode} ({result.get('intent', '')})".strip(),
        answer=result["answer"],
        tools=result.get("tools", []),
        routing_decision=routing_decision,
        pipeline_steps=pipeline_steps,
        sources=result.get("sources", []),
        evidence=result.get("evidence", {}),
        llm_input=result.get("llm_input", {}),
        memory=session,
    )
