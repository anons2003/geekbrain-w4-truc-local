---
title: SLA Policy
status: current
owner: VP Engineering (Mark Sullivan)
last_updated: 2026-01-10
tags: [policy, sla, reliability, availability]
---

# SLA Policy

This document describes GeekBrain's internal SLA framework: how targets are defined,
how they are measured, and what happens when they are breached.
Exact target numbers for each service are maintained in the operational spreadsheet
and `sla_targets.csv` — this document covers framework and principles.

---

## SLA Framework

Each service has three measured metrics:

1. **Availability** — percentage of time the service is reachable and responding correctly.
   Measured on a rolling monthly window.

2. **Latency (p99)** — the 99th-percentile response time. The slowest 1% of requests
   must still be within the target. Measured on rolling 5-minute windows.

3. **Error rate** — percentage of requests resulting in a server-side error (5xx).
   Measured on rolling 5-minute windows.

---

## Service Tiers and Priorities

Services have different SLA targets based on their business criticality:

**PaymentGW** — strictest targets across all three metrics. Revenue-critical, real-time.
Any degradation here has immediate financial impact on merchants and end users.

**AuthSvc** — near-zero downtime target for availability. Every other service depends on
AuthSvc for token validation; an AuthSvc outage cascades to all services simultaneously.
Latency target is also strict — token validation adds to every request's critical path.

**FraudDetector** — strict latency target (sub-200ms requirement). Runs inline in the
PaymentGW transaction flow; slow fraud scoring directly increases payment latency.
Availability target mirrors PaymentGW since it is a hard dependency for payment commits.

**OrderSvc** — moderate targets. Latency spikes are less customer-visible than PaymentGW,
but availability matters for the order creation flow.

**NotificationSvc** — moderate targets, with some flexibility because notifications are
async. Delays are irritating but not immediately revenue-impacting. Under increasing pressure
as merchant expectations for real-time notifications grow.

**ReportingSvc** — most relaxed targets. Batch-oriented; delays in reports are acceptable.
Availability requirement is lower because brief outages only delay analytics, not transactions.

---

## Measurement Windows

- **Availability**: Rolling monthly. Calculated as (total minutes in month − downtime minutes) / total minutes.
- **Latency and error rate**: Rolling 5-minute window. Breach declared when the metric exceeds
  the target in a given 5-minute window.

---

## Breach Consequences

**Sustained breach (>15 minutes):**
An incident ticket is automatically created. The on-call engineer is paged per
`incident_response_policy.md` severity rules.

**Repeated breaches (>3 per month for the same service):**
Engineering review required. Team lead presents analysis and remediation plan to VP Engineering
within 5 business days.

**Availability SLA missed (monthly):**
Merchant credits may be issued per the merchant agreement. The Platform team coordinates
credit calculation with the business team. Not all merchants have availability SLA guarantees
in their contracts — eligibility depends on merchant tier.

---

## Quarterly SLA Review

Every quarter, VP Engineering convenes a review with all team leads. Agenda:
- Prior quarter performance vs. targets (using data from `daily_metrics.csv` and incident records)
- Any targets that need adjustment due to infrastructure changes or new business requirements
- Action items for services approaching their SLA limits

Teams are expected to come prepared with their own analysis — do not arrive at the quarterly
review without knowing how your service performed.

---

## Relationship to Incident Policy

SLA monitoring is what triggers many incidents. When a rolling 5-minute window shows
a latency or error rate breach sustained beyond the threshold, the alerting system
creates an incident automatically. See `incident_response_policy.md` for how incidents
are then classified and handled.

P1 incidents always imply an SLA breach. P2 incidents may or may not breach SLA targets
depending on severity and duration.

---

## Questions

SLA target values → `sla_targets.csv` or the operational spreadsheet (ask your team lead).
SLA policy questions → VP Engineering Mark Sullivan or #platform-reliability Slack channel.
