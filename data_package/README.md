# GeekBrain Data Package

Dữ liệu và công cụ cho hệ thống AI chatbot GeekBrain (dùng cho đánh giá tuần 4).

## Cấu trúc thư mục

```
data_package/
├── structured_data/          # Dữ liệu có cấu trúc (CSV) — dùng cho L3 tool queries
│   ├── monthly_costs.csv     # Chi phí AWS theo service, Oct 2025 – Mar 2026
│   ├── incidents.csv         # 8 bản ghi incident (INC-001 → INC-008)
│   ├── sla_targets.csv       # SLA targets: availability, latency p99, error rate
│   └── daily_metrics.csv     # Metrics hàng ngày Jan–Mar 2026 (540 rows, 6 services)
├── scripts/                  # Scripts hỗ trợ
│   ├── monitoring_api.py     # FastAPI — trả live status, metrics, incidents
│   ├── seed_data.py          # Load CSV → SQLite hoặc PostgreSQL
│   └── pyproject.toml        # Python dependencies (dùng uv sync)
└── knowledge_base/           # 36 tài liệu markdown — dùng cho RAG (L1, L2)
```

## Mô tả CSV

| File | Số dòng | Cột chính |
|------|---------|-----------|
| monthly_costs.csv | 36 (6 services × 6 tháng) | service, month, compute/storage/network/third_party/total cost |
| incidents.csv | 8 | incident_id, service, date, severity, duration_minutes, root_cause, resolution |
| sla_targets.csv | 18 (6 services × 3 metrics) | service, metric, target, measurement_window |
| daily_metrics.csv | 540 (6 services × 90 ngày) | date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent |

## Chạy Monitoring API

```bash
cd scripts/
uv sync
uv run uvicorn monitoring_api:app --reload --port 8000
```

API root tại http://localhost:8000 — liệt kê tất cả endpoints.

Các endpoint chính:
- `GET /services` — danh sách 6 services
- `GET /status/{service_name}` — uptime và active alerts
- `GET /metrics/{service_name}` — latency, error rate, CPU/memory hiện tại (±5% jitter mỗi lần gọi)
- `GET /incidents` — toàn bộ 8 incidents
- `GET /incidents/{service_name}` — lọc theo service

## Seed Database

SQLite (không cần setup thêm):
```bash
cd scripts/
uv run python seed_data.py --db-type sqlite --sqlite-path geekbrain.db
```

PostgreSQL:
```bash
uv run python seed_data.py --db-type postgres --db-url postgresql://user:pass@localhost/geekbrain
```

In tổng số rows đã load khi hoàn thành.

## Knowledge Base

Thư mục `knowledge_base/` chứa 36 tài liệu markdown cho hệ thống RAG, bao gồm: company overview, team structure, service architecture, API reference, deployment policy, incident response policy, postmortems, security policy, SLA policy, Q1 review notes, onboarding guide, capacity planning, cost optimization.

**Ranh giới dữ liệu:** Tài liệu chỉ chứa mô tả định tính và chính sách — KHÔNG có số tiền cụ thể hoặc giá trị metrics hàng ngày. Các con số chính xác nằm trong CSV files và monitoring API.
