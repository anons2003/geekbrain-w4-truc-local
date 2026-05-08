---
doc_id: KB-034
title: Cost Optimization Initiative — Q2 2026
category: infrastructure
tags: [cost-optimization, q2-2026, paymentgw, frauddetector, reserved-instances, elasticache, right-sizing]
last_updated: 2026-04-05
status: active
owner: Mark Sullivan
---

# Cost Optimization Initiative — Q2 2026

**Announced by:** James Wright (CTO)  
**Announced at:** Q1 2026 Quarterly Review (April 5, 2026)  
**Goal:** Reduce overall infrastructure costs by **15%** by end of Q2 2026  
**Constraint:** Cost reductions must not compromise SLA commitments or production reliability

---

## Background

The Q1 2026 quarterly review surfaced a concern from CTO James Wright: infrastructure costs grew faster than transaction volume in Q1. The gap is partly attributable to the March incident and its aftermath, but there are also underlying structural cost inefficiencies that existed before the incident. This initiative formalizes the effort to address both.

All teams are required to submit cost optimization plans by **April 30, 2026**. VP Engineering Mark Sullivan will review, prioritize across teams, and confirm the Q2 roadmap.

---

## Top Priority Services

Two services are identified as top cost optimization targets:

### PaymentGW

PaymentGW has the highest absolute infrastructure cost of any service and showed the steepest cost growth rate in Q1. The March incident contributed significantly to March costs (retries, fallback routing, incident remediation activity), but cost growth was elevated before the incident as well.

Primary optimization levers for PaymentGW:
- **Reserved Instances:** PaymentGW compute is currently on-demand. Switching stable compute to 1-year Reserved Instances is expected to yield meaningful savings. This decision should follow the horizontal scaling architecture decision (see capacity planning) to avoid committing to the wrong instance type.
- **Third-party API cost review:** Bank API fees represent a significant portion of PaymentGW's third-party costs. Review retry logic and error handling — unnecessary retries during outage scenarios inflate this cost category.
- **Connection efficiency:** Post-INC-001, the connection pool was expanded. Review current utilization to confirm the expanded pool is fully justified.

### FraudDetector

FraudDetector has the second-highest absolute infrastructure cost. ML inference workloads on SageMaker are inherently expensive, but there is room to optimize.

Primary optimization levers for FraudDetector:
- **Right-sizing the SageMaker endpoint:** The current instance type may have excess compute capacity at current traffic levels. Benchmarking (planned for Q2 as part of capacity planning) will also inform whether a smaller instance is viable for current load.
- **Inference caching:** For identical transaction fingerprints (e.g., repeated payment attempts from the same source), caching the fraud score response with a short TTL (30–60 seconds) would reduce inference volume. Ryan Blake to evaluate feasibility.
- **SageMaker reserved capacity:** SageMaker Savings Plans can reduce inference costs for predictable workloads.

---

## Company-Wide Strategies

The following strategies apply across all services:

### 1. Reserved Instances for Stable Workloads

Services with predictable, stable compute usage are strong candidates for 1-year Reserved Instances. Identified candidates:
- AuthSvc (highly stable, predictable load)
- PaymentGW (after horizontal scaling architecture is decided)
- ReportingSvc (Redshift has a dedicated Reserved Node option)

### 2. Right-Sizing Underutilized Instances

Each team must audit their service's instance utilization over the last 90 days. Any instance consistently below 40% CPU and memory utilization is a right-sizing candidate.

Note: Do not right-size instances that have overhead for burst traffic or incident scenarios — check peak utilization, not just average.

### 3. Response Caching with ElastiCache

Introducing a caching layer (ElastiCache for Redis) for frequently repeated queries can reduce backend compute and database load. Candidate use cases:
- OrderSvc: repeated inventory availability queries for the same SKU
- FraudDetector: short-TTL caching of fraud scores for identical transaction fingerprints

### 4. Development and Staging Environment Consolidation

Currently each of the six services has three environments: development, staging, production. The development environments for lower-traffic services are candidates for consolidation:
- Shared development environment for NotificationSvc, OrderSvc, and ReportingSvc
- Staging environments to be kept separate for each service (needed for isolated pre-production testing)

Team leads to assess feasibility for their services. This must not impact developer velocity.

### 5. Third-Party Cost Review

Third-party costs (bank API fees, SageMaker inference costs, SES email costs) are reviewed per team. Each team's optimization plan should include a section on third-party costs within their service scope.

---

## Timeline

| Milestone | Date |
|-----------|------|
| All teams submit cost optimization plans | April 30, 2026 |
| Mark Sullivan reviews and prioritizes | May 7, 2026 |
| Q2 cost optimization roadmap finalized | May 84, 2026 |
| Implementation begins | May 2026 |
| Mid-quarter cost review | June 2026 |
| End-of-Q2 assessment vs. 15% target | July 2026 |

---

## What to Include in Your Team's Plan

Each team lead's optimization plan should include:

1. Current cost breakdown by category (compute, storage, network, third-party) — qualitative description of largest buckets
2. Identified optimization opportunities with estimated impact (high/medium/low — no dollar commitments required)
3. Proposed actions with owner and timeline
4. Any tradeoffs or risks (e.g., reserved instance lock-in risk if traffic patterns change)

---

## What This Initiative Is NOT

- This is not a directive to reduce engineering headcount
- This is not a freeze on necessary infrastructure investments (scaling for reliability is still approved)
- Cost cuts that would risk SLA breaches are not acceptable — all proposals must preserve SLA commitments

---

## Related Documents

- `q1_2026_review_notes.md` — Q1 review where initiative was announced
- `capacity_planning_q2_2026.md` — Scaling plans that must be coordinated with cost optimization
