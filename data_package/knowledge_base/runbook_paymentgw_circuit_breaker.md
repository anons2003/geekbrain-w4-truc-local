---
doc_id: KB-029
title: Runbook — PaymentGW Circuit Breaker Management
category: runbook
tags: [runbook, paymentgw, circuit-breaker, on-call, incident-response, team-platform]
last_updated: 2026-03-08
status: active
owner: Team Platform
---

# Runbook: PaymentGW Circuit Breaker Management

**Purpose:** Step-by-step guide for on-call engineers to diagnose and manage PaymentGW circuit breaker state during incidents or anomalies.

**Last updated:** March 8, 2026 (post INC-005 review)

**Owner:** Team Platform / Alex Chen

---

## Background

PaymentGW uses the circuit breaker pattern to protect against cascading failures from upstream bank API outages. Each configured bank API integration has its own circuit breaker instance. When a bank API times out or returns errors above a configured threshold, the breaker trips open to stop sending requests to the failing upstream.

The March 5, 2026 incident (INC-005) exposed a bug in the circuit breaker reset flow that caused the breaker to remain stuck in OPEN state even after the upstream bank recovered. This runbook incorporates lessons learned from that incident.

---

## Circuit Breaker States

| State | Description | Behavior |
|-------|-------------|----------|
| **CLOSED** | Normal operation | All requests flow to upstream bank API |
| **OPEN** | Tripped — upstream assumed unhealthy | Requests fail fast (no upstream call made) |
| **HALF_OPEN** | Recovery probe mode | Limited traffic (configurable %) sent to upstream to test recovery |

State transitions:
- CLOSED → OPEN: error rate exceeds threshold within a rolling window
- OPEN → HALF_OPEN: after configured timeout period
- HALF_OPEN → CLOSED: probe requests succeed
- HALF_OPEN → OPEN: probe requests fail

---

## Diagnostic Commands

### Check current circuit breaker state

```bash
# Check all circuit breakers
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://paymentgw.internal/admin/circuit-breaker/status

# Check specific bank integration
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://paymentgw.internal/admin/circuit-breaker/status?bank=BankAPI-1
```

Expected healthy response:
```json
{
  "BankAPI-1": {"state": "CLOSED", "error_rate": 0.2, "last_trip": null},
  "BankAPI-2": {"state": "CLOSED", "error_rate": 0.1, "last_trip": null},
  "BankAPI-3": {"state": "CLOSED", "error_rate": 0.4, "last_trip": null}
}
```

---

## Manual Operations

### (a) Force Reset an Open Circuit Breaker

Use when: automated reset failed, or breaker is stuck in OPEN state after upstream has confirmed recovery.

```bash
# Reset a specific bank's circuit breaker
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bank": "BankAPI-1"}' \
  https://paymentgw.internal/admin/circuit-breaker/reset
```

**Requires:** ADMIN role. Check IAM if your token lacks this permission.

**Important (post-INC-005 update):** As of March 8, 2026, the reset endpoint directly sets the breaker to HALF_OPEN state without performing an upstream health check first. Previously, the reset endpoint called the bank's health check before resetting — this caused the stuck-open issue during INC-005, where the health check itself was returning the same error codes as the outage. The new behavior: reset always proceeds, and the HALF_OPEN probe traffic determines if the upstream is truly recovered.

### (b) Force Open a Circuit Breaker (Emergency Stop)

Use when: upstream bank has confirmed a major outage and you want to prevent retry storm before the breaker trips automatically.

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bank": "BankAPI-1", "reason": "Confirmed bank maintenance window"}' \
  https://paymentgw.internal/admin/circuit-breaker/open
```

---

## When to Use Manual Intervention

1. Automated reset failed and breaker has been in OPEN state for more than 10 minutes after upstream recovery
2. Upstream bank proactively notifies of outage — manually OPEN the breaker to skip the error accumulation period
3. False positive trip detected (verified that upstream is healthy, but breaker tripped due to misclassified errors)

---

## Post-March 5 Health Check Addition

A dedicated ping endpoint was added to each bank API integration after INC-005. On-call engineers can check bank API reachability without triggering circuit breaker logic:

```bash
curl https://paymentgw.internal/admin/bank-health/BankAPI-1
```

This runs a lightweight connectivity check that is isolated from the circuit breaker error counting. Use this to verify upstream health before forcing a reset.

---

## Escalation

If the breaker cannot be reset within 10 minutes using this runbook, escalate to **Alex Chen (Team Platform Lead)**.

P1 escalation path:
1. On-call engineer (immediate)
2. Alex Chen — 15 minutes
3. Mark Sullivan (VP Engineering) — 30 minutes
4. James Wright (CTO) — 1 hour

---

## Related Documents

- `postmortem_INC005_paymentgw.md` — Root cause and timeline of the March 5 P1
- `incident_response_policy.md` — Severity definitions and escalation matrix
- `on_call_handbook.md` — General on-call procedures
