---
doc_id: KB-031
title: Monitoring Dashboard Guide
category: operations
tags: [monitoring, grafana, cloudwatch, dashboards, on-call, observability]
last_updated: 2026-03-20
status: active
---

# Monitoring Dashboard Guide

**Purpose:** Reference guide for all GeekBrain engineering monitoring dashboards. Covers where to find them, what they show, and how to use them during incidents.

**Access requirement:** All Grafana dashboards require VPN connection. CloudWatch dashboards are accessible via AWS Console (IAM role required — see onboarding guide for access request).

---

## Dashboard Locations

### Grafana (Primary)

URL: `https://grafana.internal` (VPN required)

All real-time service monitoring is in Grafana. Dashboards are organized by service and by cross-service view.

### CloudWatch (Secondary)

Access via AWS Console → CloudWatch → Dashboards. Used primarily for alarm management, raw metric inspection, and log queries.

---

## Key Dashboards

### 1. Service Health Overview

**Location:** Grafana → Home → Service Health Overview

**What it shows:**
- Current status (healthy / degraded / down) for all 6 services
- Active alerts per service
- Last incident timestamp per service
- Uptime percentage (24h, 7d, 30d)

**When to use:** First stop during any incident. Gives a fast read on which services are affected and whether there are active alerts. Check this before diving into individual service dashboards.

Note: As of March 2026, the PaymentGW circuit breaker state is also shown on this dashboard (added post-INC-005). If a circuit breaker is in OPEN or HALF_OPEN state, it displays as a yellow indicator alongside the service status.

---

### 2. PaymentGW Transaction Dashboard

**Location:** Grafana → PaymentGW → Transaction Dashboard

**What it shows:**
- Transactions processed per minute (rolling window)
- Transaction success rate (%)
- Latency percentiles: p50, p95, p99
- Error rate breakdown by error type
- Circuit breaker state per bank API integration
- Database connection pool utilization

**When to use:** During PaymentGW incidents, or when investigating latency or error rate alerts. The circuit breaker panel is the first thing to check during upstream bank issues.

**Key thresholds to watch:**
- p99 latency: SLA target is 200ms. Alert fires at sustained breach.
- Error rate: SLA target is 0.1%. Alert fires at 0.15%.
- Connection pool: Alert fires when utilization exceeds 80%.

---

### 3. FraudDetector Model Dashboard

**Location:** Grafana → FraudDetector → Model Dashboard

**What it shows:**
- Prediction score distribution (histogram)
- False positive rate (rolling 30-min window)
- False negative rate (rolling 30-min window)
- Feature drift indicators (per-feature z-score from baseline)
- SageMaker endpoint latency (p50, p95, p99)
- Inference error rate

**When to use:** When investigating model drift alerts or validating a newly promoted model. Feature drift panel shows which input features are deviating from training distribution — useful for early drift detection before it affects prediction quality.

**Key thresholds to watch (CloudWatch alarms also set on these):**
- False positive rate: alert at > 5% sustained for 30 min
- False negative rate: alert at > 1% sustained for 30 min
- p99 latency: alert at > 140ms (SLA is 150ms, early warning)

---

### 4. Cost Overview Dashboard

**Location:** Grafana → Cost → Monthly Overview

**What it shows:**
- Monthly infrastructure spend by service
- Cost trend over last 6 months (per service, stacked bar)
- Breakdown by cost category: compute, storage, network, third-party

**Update frequency:** Daily (cost data is not real-time — refreshed once per day from AWS Cost Explorer).

**When to use:** During cost review meetings or when investigating cost anomalies. Not used during live incidents.

---

### 5. Incident Timeline Dashboard

**Location:** Grafana → Operations → Incident Timeline

**What it shows:**
- Chronological list of incidents with severity markers overlaid on key metric charts
- Allows correlating service metrics with incident events
- Filterable by service, severity, and date range

**When to use:** Post-incident analysis. Useful for identifying patterns across incidents or understanding how a metric trend led to a specific incident.

---

## CloudWatch Alarms

Each service has a standard set of CloudWatch alarms. All alarms route to PagerDuty via SNS.

### Standard Alarms (all services)

| Alarm | Condition |
|-------|-----------|
| High p99 latency | p99 exceeds SLA threshold for >5 min |
| High error rate | Error rate exceeds SLA threshold for >5 min |
| Low availability | Availability drops below SLA target |

### PaymentGW Additional Alarms

| Alarm | Condition |
|-------|-----------|
| Circuit breaker open | Any bank circuit breaker enters OPEN state |
| Connection pool high | Pool utilization > 80% |

### FraudDetector Additional Alarms

| Alarm | Condition |
|-------|-----------|
| High false positive rate | FP rate > 5% for > 30 min |
| High false negative rate | FN rate > 1% for > 30 min |

### NotificationSvc Additional Alarms

| Alarm | Condition |
|-------|-----------|
| DLQ depth high | Dead letter queue depth > 10,000 messages |
| Queue drain latency | Messages waiting > 5 min in SQS queue |

---

## On-Call First Steps

During any alert, the recommended dashboard sequence is:

1. **Service Health Overview** — assess scope and active alerts
2. **Affected service dashboard** — drill into the specific service
3. **CloudWatch** — check raw alarm state and log streams if needed

Do not skip the Service Health Overview step. A problem that looks like an isolated service issue often has upstream or downstream components also affected.

---

## Related Documents

- `on_call_handbook.md` — Full on-call procedures
- `incident_response_policy.md` — Severity definitions and response requirements
- `runbook_paymentgw_circuit_breaker.md` — PaymentGW circuit breaker procedures
- `runbook_frauddetector_model_retraining.md` — FraudDetector retraining procedures
