// Cho phép mở UI bằng file:// nhưng vẫn gọi backend local FastAPI ở port 8080.
const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8080" : "";

const statusEl = document.querySelector("#status");
const messagesEl = document.querySelector("#messages");
const traceEl = document.querySelector("#trace");
const formEl = document.querySelector("#chat-form");
const modeEl = document.querySelector("#mode");
const questionEl = document.querySelector("#question");
const workspaceEl = document.querySelector(".workspace");
const traceResizerEl = document.querySelector("#trace-resizer");
const examplesToggleEl = document.querySelector("#examples-toggle");

// Lưu session_id ở browser để L4 memory nối được các câu follow-up qua nhiều lượt hỏi.
let sessionId = localStorage.getItem("geekbrain_w4_session_id");
const examplesCollapsed = localStorage.getItem("geekbrain_examples_collapsed") === "true";
const savedTraceWidth = localStorage.getItem("geekbrain_trace_width");
if (savedTraceWidth) {
  document.documentElement.style.setProperty("--trace-width", savedTraceWidth);
}

let resizeFrame = 0;
let pendingTraceWidth = null;
let activeTraceWidth = parseInt(savedTraceWidth, 10) || 460;

function setExamplesCollapsed(collapsed) {
  // Ẩn/hiện Examples để chat và Trace tự giãn theo không gian còn lại khi demo.
  if (!workspaceEl || !examplesToggleEl) return;
  workspaceEl.classList.toggle("examples-collapsed", collapsed);
  examplesToggleEl.textContent = collapsed ? "Show Examples" : "Hide Examples";
  examplesToggleEl.setAttribute("aria-pressed", String(collapsed));
  localStorage.setItem("geekbrain_examples_collapsed", String(collapsed));
  requestAnimationFrame(() => {
    const currentWidth = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--trace-width"), 10) || 460;
    setTraceWidth(currentWidth);
  });
}

setExamplesCollapsed(examplesCollapsed);

function setTraceWidth(width) {
  // Clamp width để Trace không đè lên chat và vẫn đủ rộng cho screenshot Bonus A.
  if (!workspaceEl) return;
  const bounds = workspaceEl.getBoundingClientRect();
  const minWidth = 360;
  const examplesVisible = !workspaceEl.classList.contains("examples-collapsed");
  const reservedWidth = examplesVisible ? 700 : 460;
  const maxWidth = Math.max(420, Math.min(860, bounds.width - reservedWidth));
  const clamped = Math.min(maxWidth, Math.max(minWidth, Math.round(width)));
  const value = `${clamped}px`;
  document.documentElement.style.setProperty("--trace-width", value);
  activeTraceWidth = clamped;
  if (traceResizerEl) {
    traceResizerEl.setAttribute("aria-valuemin", String(minWidth));
    traceResizerEl.setAttribute("aria-valuemax", String(maxWidth));
    traceResizerEl.setAttribute("aria-valuenow", String(clamped));
  }
}

function scheduleTraceWidth(width) {
  // Dùng requestAnimationFrame để kéo splitter mượt hơn, tránh update layout quá dày.
  pendingTraceWidth = width;
  if (resizeFrame) return;
  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = 0;
    setTraceWidth(pendingTraceWidth);
  });
}

function escapeHtml(value) {
  // Escape mọi dữ liệu từ API trước khi render HTML trong trace.
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function addMessage(role, text) {
  // Thêm bubble chat và auto-scroll xuống câu mới nhất.
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function pre(value) {
  return `<pre>${escapeHtml(JSON.stringify(value ?? {}, null, 2))}</pre>`;
}

function section(title, body) {
  return `
    <section class="trace-card">
      <h3>${escapeHtml(title)}</h3>
      ${body}
    </section>
  `;
}

function pillList(items, emptyText) {
  if (!items || items.length === 0) {
    return `<div class="trace-empty">${escapeHtml(emptyText)}</div>`;
  }
  return items.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("");
}

function compactJson(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return escapeHtml(value);
  }
  return escapeHtml(JSON.stringify(value));
}

function pipelineList(steps) {
  // Render các bước pipeline để người chấm thấy hệ thống route/retrieve/tool/generate như thế nào.
  if (!steps || steps.length === 0) {
    return `<div class="trace-empty">No pipeline steps returned.</div>`;
  }
  return `
    <ol class="trace-timeline">
      ${steps.map((step, index) => `
        <li class="trace-step">
          <span class="step-index">${index + 1}</span>
          <div>
            <strong>${escapeHtml(step.step || "Step")}</strong>
            ${step.detail === undefined ? "" : `<p>${compactJson(step.detail)}</p>`}
          </div>
        </li>
      `).join("")}
    </ol>
  `;
}

function sourceList(sources) {
  // Danh sách source/chunk được retrieve, gồm score và status để kiểm tra citation/conflict.
  if (!sources || sources.length === 0) {
    return `<div class="trace-empty">No retrieved sources returned.</div>`;
  }
  return sources.map((source) => `
    <div class="source">
      <div>
        <strong>${escapeHtml(source.source || "unknown source")}</strong>
        <span>status=${escapeHtml(source.status || "unknown")}</span>
      </div>
      <b>${escapeHtml(source.score ?? "n/a")}</b>
    </div>
  `).join("");
}

function evidenceSummary(evidence) {
  // Evidence là dữ liệu có cấu trúc từ tool hoặc lookup, giúp chứng minh câu trả lời không bị bịa.
  if (!evidence || Object.keys(evidence).length === 0) {
    return `<div class="trace-empty">No structured evidence returned.</div>`;
  }
  return `
    <div class="kv-list">
      ${Object.entries(evidence).map(([key, value]) => `
        <div class="kv-row">
          <span>${escapeHtml(key)}</span>
          <strong>${compactJson(value)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function llmInputSummary(llmInput) {
  // Với L1/L2, show prompt/context preview để Bonus A thấy LLM nhận gì trước khi trả lời.
  if (!llmInput || Object.keys(llmInput).length === 0) {
    return `<div class="trace-empty">No LLM input for this route; answer came directly from tools or memory.</div>`;
  }
  return `
    <div class="kv-list">
      <div class="kv-row">
        <span>question</span>
        <strong>${escapeHtml(llmInput.user_question || "n/a")}</strong>
      </div>
      <div class="kv-row">
        <span>system prompt</span>
        <strong>${escapeHtml((llmInput.system_prompt || "").split("\n")[0] || "n/a")}</strong>
      </div>
      <div class="trace-preview">${escapeHtml(llmInput.context_preview || "")}</div>
    </div>
  `;
}

function memorySummary(memoryState) {
  // Hiển thị compact memory của L4: service/month/team/incident đã nhớ từ các turn trước.
  if (!memoryState || Object.keys(memoryState).length === 0) {
    return `<div class="trace-empty">No memory state yet.</div>`;
  }
  return `
    <div class="kv-list">
      ${Object.entries(memoryState).map(([key, value]) => `
        <div class="kv-row">
          <span>${escapeHtml(key)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function renderTrace(data) {
  // Render toàn bộ observability dashboard bên phải sau mỗi request.
  const memory = data.memory || {};
  const memoryState = memory.state || memory;
  traceEl.className = "";
  traceEl.innerHTML = [
    `<div class="trace-hero">
      <div>
        <span>Mode</span>
        <strong>${escapeHtml(data.mode || "unknown")}</strong>
      </div>
      <div>
        <span>Session</span>
        <strong>${escapeHtml((data.session_id || "none").slice(0, 8))}</strong>
      </div>
    </div>`,
    section("Routing Decision", `<p class="trace-decision">${escapeHtml(data.routing_decision || "No routing detail returned.")}</p>`),
    section("Pipeline Steps", pipelineList(data.pipeline_steps)),
    section("Tools Called", pillList(data.tools, "No tools called.")),
    section("Retrieved Sources", sourceList(data.sources)),
    section("Evidence / Tool Result", evidenceSummary(data.evidence)),
    section("LLM Input", llmInputSummary(data.llm_input)),
    section("Session Memory", memorySummary(memoryState)),
  ].join("");
}

async function checkHealth() {
  // Health check chỉ xác nhận backend đang chạy để user biết có thể demo.
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    const data = await response.json();
    statusEl.textContent = data.status === "ok" ? "API ready" : "API issue";
    statusEl.classList.toggle("ok", data.status === "ok");
    statusEl.classList.toggle("fail", data.status !== "ok");
  } catch (error) {
    statusEl.textContent = "API offline";
    statusEl.classList.add("fail");
  }
}

document.querySelectorAll(".examples button").forEach((button) => {
  // Click example chỉ đổ câu hỏi vào ô nhập; user vẫn bấm Send để chạy pipeline.
  button.addEventListener("click", () => {
    questionEl.value = button.dataset.question || button.textContent.trim();
    questionEl.focus();
  });
});

if (examplesToggleEl) {
  examplesToggleEl.addEventListener("click", () => {
    setExamplesCollapsed(!workspaceEl.classList.contains("examples-collapsed"));
  });
}

if (traceResizerEl && workspaceEl) {
  // Splitter/resizable divider cho Trace: hỗ trợ mouse, touch và keyboard.
  traceResizerEl.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    if (resizeFrame) {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = 0;
    }
    traceResizerEl.setPointerCapture(event.pointerId);
    document.body.classList.add("resizing-trace");
  });

  traceResizerEl.addEventListener("pointermove", (event) => {
    if (!document.body.classList.contains("resizing-trace")) return;
    const bounds = workspaceEl.getBoundingClientRect();
    scheduleTraceWidth(bounds.right - event.clientX);
  });

  traceResizerEl.addEventListener("pointerup", (event) => {
    traceResizerEl.releasePointerCapture(event.pointerId);
    document.body.classList.remove("resizing-trace");
    localStorage.setItem("geekbrain_trace_width", `${activeTraceWidth}px`);
  });

  traceResizerEl.addEventListener("pointercancel", () => {
    document.body.classList.remove("resizing-trace");
    localStorage.setItem("geekbrain_trace_width", `${activeTraceWidth}px`);
  });

  traceResizerEl.addEventListener("dblclick", () => {
    setTraceWidth(460);
  });

  traceResizerEl.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const currentWidth = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--trace-width"), 10) || 460;
    if (event.key === "ArrowLeft") setTraceWidth(currentWidth + 32);
    if (event.key === "ArrowRight") setTraceWidth(currentWidth - 32);
    if (event.key === "Home") setTraceWidth(360);
    if (event.key === "End") setTraceWidth(760);
  });
}

formEl.addEventListener("submit", async (event) => {
  // Gửi câu hỏi tới /api/chat, giữ session_id để backend dùng cho L4 memory.
  event.preventDefault();

  const question = questionEl.value.trim();
  if (!question) return;

  const submitButton = formEl.querySelector("button");
  submitButton.disabled = true;
  questionEl.value = "";
  addMessage("user", question);
  traceEl.className = "trace-empty";
  traceEl.textContent = "Running pipeline...";

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        question,
        mode: modeEl.value,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    sessionId = data.session_id;
    localStorage.setItem("geekbrain_w4_session_id", sessionId);
    addMessage("assistant", data.answer || "No answer returned.");
    renderTrace(data);
  } catch (error) {
    addMessage("assistant", `Request failed: ${error.message}`);
    traceEl.className = "trace-empty";
    traceEl.textContent = "API request failed. Start the local server and try again.";
  } finally {
    submitButton.disabled = false;
  }
});

checkHealth();
