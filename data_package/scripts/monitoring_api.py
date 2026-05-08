"""
GeekBrain Monitoring API
FastAPI app exposing live service status, metrics, and incident history.
Run: uvicorn monitoring_api:app --reload --port 8000
"""

import random
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="GeekBrain Monitoring API",
    description="Live service health, metrics, and incident history for GeekBrain platform services.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = [
    "PaymentGW",
    "OrderSvc",
    "AuthSvc",
    "NotificationSvc",
    "ReportingSvc",
    "FraudDetector",
]

# Static status data from universe spec
SERVICE_STATUS = {
    "PaymentGW": {
        "service": "PaymentGW",
        "status": "healthy",
        "uptime_percent_24h": 99.98,
        "uptime_percent_7d": 99.91,
        "uptime_percent_30d": 99.87,
        "last_incident": "2026-03-05",
        "active_alerts": [],
    },
    "OrderSvc": {
        "service": "OrderSvc",
        "status": "healthy",
        "uptime_percent_24h": 100.0,
        "uptime_percent_7d": 99.95,
        "uptime_percent_30d": 99.92,
        "last_incident": "2026-01-28",
        "active_alerts": [],
    },
    "AuthSvc": {
        "service": "AuthSvc",
        "status": "healthy",
        "uptime_percent_24h": 100.0,
        "uptime_percent_7d": 99.99,
        "uptime_percent_30d": 99.97,
        "last_incident": "2026-02-22",
        "active_alerts": [],
    },
    "NotificationSvc": {
        "service": "NotificationSvc",
        "status": "degraded",
        "uptime_percent_24h": 98.5,
        "uptime_percent_7d": 99.1,
        "uptime_percent_30d": 99.3,
        "last_incident": "2026-03-20",
        "active_alerts": ["HIGH_LATENCY", "ELEVATED_ERROR_RATE"],
    },
    "ReportingSvc": {
        "service": "ReportingSvc",
        "status": "healthy",
        "uptime_percent_24h": 99.9,
        "uptime_percent_7d": 99.6,
        "uptime_percent_30d": 99.2,
        "last_incident": "2026-04-02",
        "active_alerts": [],
    },
    "FraudDetector": {
        "service": "FraudDetector",
        "status": "healthy",
        "uptime_percent_24h": 100.0,
        "uptime_percent_7d": 99.97,
        "uptime_percent_30d": 99.93,
        "last_incident": "2026-03-12",
        "active_alerts": [],
    },
}

# Base metrics from universe spec — ±5% jitter applied at request time
BASE_METRICS = {
    "PaymentGW": {
        "latency_ms": {"p50": 45, "p95": 120, "p99": 185},
        "error_rate_percent": 0.08,
        "requests_per_minute": 12500,
        "cpu_utilization_percent": 62,
        "memory_utilization_percent": 71,
    },
    "OrderSvc": {
        "latency_ms": {"p50": 85, "p95": 210, "p99": 320},
        "error_rate_percent": 0.2,
        "requests_per_minute": 4200,
        "cpu_utilization_percent": 38,
        "memory_utilization_percent": 55,
    },
    "AuthSvc": {
        "latency_ms": {"p50": 12, "p95": 30, "p99": 45},
        "error_rate_percent": 0.005,
        "requests_per_minute": 28000,
        "cpu_utilization_percent": 45,
        "memory_utilization_percent": 40,
    },
    "NotificationSvc": {
        "latency_ms": {"p50": 800, "p95": 2100, "p99": 3200},
        "error_rate_percent": 2.1,
        "requests_per_minute": 1800,
        "cpu_utilization_percent": 88,
        "memory_utilization_percent": 92,
    },
    "ReportingSvc": {
        "latency_ms": {"p50": 450, "p95": 1200, "p99": 2100},
        "error_rate_percent": 0.5,
        "requests_per_minute": 350,
        "cpu_utilization_percent": 55,
        "memory_utilization_percent": 68,
    },
    "FraudDetector": {
        "latency_ms": {"p50": 35, "p95": 85, "p99": 120},
        "error_rate_percent": 0.03,
        "requests_per_minute": 12500,
        "cpu_utilization_percent": 72,
        "memory_utilization_percent": 65,
    },
}

INCIDENTS = [
    {
        "incident_id": "INC-001",
        "service": "PaymentGW",
        "date": "2026-01-15",
        "severity": "P2",
        "duration_minutes": 45,
        "root_cause": "Database connection pool exhaustion under peak load",
        "resolution": "Increased pool size from 20 to 50, added connection monitoring",
        "team_responsible": "Team Platform",
        "reported_by": "Automated alert",
    },
    {
        "incident_id": "INC-002",
        "service": "OrderSvc",
        "date": "2026-01-28",
        "severity": "P3",
        "duration_minutes": 120,
        "root_cause": "Memory leak in order validation module",
        "resolution": "Patched validation logic, added memory usage monitoring",
        "team_responsible": "Team Commerce",
        "reported_by": "Kyle Reed",
    },
    {
        "incident_id": "INC-003",
        "service": "PaymentGW",
        "date": "2026-02-10",
        "severity": "P3",
        "duration_minutes": 30,
        "root_cause": "SSL certificate approaching expiry triggered alert",
        "resolution": "Renewed certificate, implemented auto-renewal via ACM",
        "team_responsible": "Team Platform",
        "reported_by": "Automated alert",
    },
    {
        "incident_id": "INC-004",
        "service": "AuthSvc",
        "date": "2026-02-22",
        "severity": "P2",
        "duration_minutes": 60,
        "root_cause": "JWT signing key rotation script failed silently",
        "resolution": "Fixed rotation script, added pre-rotation validation step, alert on failure",
        "team_responsible": "Team Platform",
        "reported_by": "Ben Torres",
    },
    {
        "incident_id": "INC-005",
        "service": "PaymentGW",
        "date": "2026-03-05",
        "severity": "P1",
        "duration_minutes": 180,
        "root_cause": "Circuit breaker stuck open after upstream bank API timeout cascade",
        "resolution": "Manual circuit breaker reset, added fallback routing to secondary bank, implemented health check ping",
        "team_responsible": "Team Platform",
        "reported_by": "Automated alert",
    },
    {
        "incident_id": "INC-006",
        "service": "FraudDetector",
        "date": "2026-03-12",
        "severity": "P2",
        "duration_minutes": 90,
        "root_cause": "Model drift — false positive rate spiked from 2% to 15%",
        "resolution": "Retrained model with Feb-Mar data, adjusted decision threshold from 0.7 to 0.75",
        "team_responsible": "Team Data",
        "reported_by": "Sarah Wells",
    },
    {
        "incident_id": "INC-007",
        "service": "NotificationSvc",
        "date": "2026-03-20",
        "severity": "P3",
        "duration_minutes": 45,
        "root_cause": "SQS dead letter queue overflow — 50k+ unprocessable messages",
        "resolution": "Increased DLQ retention to 14 days, added CloudWatch alarm at 10k messages, deployed consumer fix",
        "team_responsible": "Team Engagement",
        "reported_by": "Owen Clark",
    },
    {
        "incident_id": "INC-008",
        "service": "ReportingSvc",
        "date": "2026-04-02",
        "severity": "P2",
        "duration_minutes": 120,
        "root_cause": "ETL pipeline timeout — daily report query exceeded 30-min limit on grown dataset",
        "resolution": "Optimized Redshift query with sort keys, added pagination for large result sets",
        "team_responsible": "Team Data",
        "reported_by": "Tom Hayes",
    },
]


def _jitter(value: float, pct: float = 0.05) -> float:
    """Apply ±pct random jitter to a float value."""
    return round(value * (1.0 + random.uniform(-pct, pct)), 4)


def _jitter_int(value: int, pct: float = 0.05) -> int:
    return int(round(value * (1.0 + random.uniform(-pct, pct))))


@app.get("/", summary="API index")
def index():
    return {
        "service": "GeekBrain Monitoring API",
        "version": "1.0.0",
        "endpoints": [
            {"method": "GET", "path": "/services", "description": "List all monitored services"},
            {"method": "GET", "path": "/status/{service_name}", "description": "Current status and uptime for a service"},
            {"method": "GET", "path": "/metrics/{service_name}", "description": "Live performance metrics for a service"},
            {"method": "GET", "path": "/incidents", "description": "All incident records"},
            {"method": "GET", "path": "/incidents/{service_name}", "description": "Incidents filtered by service"},
        ],
    }


@app.get("/services", summary="List services")
def list_services():
    return SERVICES


@app.get("/status/{service_name}", summary="Service status")
def get_status(service_name: str):
    if service_name not in SERVICE_STATUS:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found. Available: {SERVICES}")
    return SERVICE_STATUS[service_name]


@app.get("/metrics/{service_name}", summary="Service metrics")
def get_metrics(service_name: str):
    if service_name not in BASE_METRICS:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found. Available: {SERVICES}")
    base = BASE_METRICS[service_name]
    return {
        "service": service_name,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latency_ms": {
            "p50": _jitter_int(base["latency_ms"]["p50"]),
            "p95": _jitter_int(base["latency_ms"]["p95"]),
            "p99": _jitter_int(base["latency_ms"]["p99"]),
        },
        "error_rate_percent": _jitter(base["error_rate_percent"]),
        "requests_per_minute": _jitter_int(base["requests_per_minute"]),
        "cpu_utilization_percent": _jitter(base["cpu_utilization_percent"]),
        "memory_utilization_percent": _jitter(base["memory_utilization_percent"]),
    }


@app.get("/incidents", summary="All incidents")
def get_all_incidents():
    return INCIDENTS


@app.get("/incidents/{service_name}", summary="Incidents by service")
def get_incidents_by_service(service_name: str):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found. Available: {SERVICES}")
    return [inc for inc in INCIDENTS if inc["service"] == service_name]
