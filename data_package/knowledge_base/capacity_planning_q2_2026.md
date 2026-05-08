---
doc_id: KB-033
title: Q2 2026 Capacity Planning
category: infrastructure
tags: [capacity-planning, q2-2026, scaling, paymentgw, frauddetector, authsvc, reportingsvc, notificationsvc, sagemaker, redis, redshift]
last_updated: 2026-04-05
status: draft
owner: Mark Sullivan
---

# Q2 2026 Capacity Planning

**Status:** Draft — pending team review  
**Owner:** Mark Sullivan (VP Engineering)  
**Planning horizon:** Q2 2026 (April – June)  
**Last updated:** April 5, 2026 (following Q1 review)

---

## Growth Assumptions

Transaction volume is projected to grow approximately **15% quarter-over-quarter** through 2026. This projection is based on merchant growth and increased transaction frequency from existing merchant integrations.

All service scaling decisions in this document are anchored to this growth projection. If actual transaction growth deviates significantly from this projection, this plan should be revisited in May.

---

## Service-by-Service Scaling Assessment

### PaymentGW

**Current state:** Single-instance architecture. The service has been running at elevated utilization following the Q1 transaction volume increase. The March incident highlighted that the current deployment model has limited fault tolerance.

**Q2 priority:** High

**Scaling need:** Evaluate horizontal scaling architecture. The current single-service model is approaching a throughput ceiling given projected transaction growth. Options under evaluation:
- Load-balanced multi-instance deployment behind an Application Load Balancer
- Service mesh for inter-service traffic management if other services also adopt horizontal scaling

**Planned action:** Alex Chen to lead architecture spike in April. Proposal due to Mark Sullivan by April 30.

**Risk:** If no architectural change is made by June, PaymentGW may not be able to sustain projected peak load without SLA breach.

---

### FraudDetector

**Current state:** SageMaker managed endpoint on `ml.m5.xlarge`. Comfortably handling current load with headroom. Latency p99 is well within the 150ms SLA target.

**Q2 priority:** Medium

**Scaling need:** At projected Q3 load (~15,000 req/min, up from ~12,000), the current endpoint configuration may begin to show latency degradation. The architecture review in February deferred this decision to Q2.

**Options:**
- Upgrade to `ml.g4dn.xlarge` — GPU-accelerated inference, better cost-per-inference at higher throughput. Estimated 15–20% latency improvement.
- Horizontal endpoint scaling — multiple `ml.m5.xlarge` instances behind SageMaker's built-in load balancer.

**Planned action:** Ryan Blake to benchmark both options against projected load by May 85. Decision to be made at May architecture review.

**Trigger for immediate action:** If p99 latency consistently approaches 140ms (early warning threshold set in CloudWatch), expedite the scaling decision.

---

### AuthSvc

**Current state:** Handling current request volume comfortably. Single Redis node remains a SPOF (flagged in February architecture review).

**Q2 priority:** High (reliability, not throughput)

**Scaling need:** Redis cluster migration is the primary Q2 deliverable for AuthSvc. The current single-node configuration presents an unacceptable availability risk for a service with a 99.99% SLA that is a dependency of all other authenticated services.

**Planned action:**
- Ben Torres to design and test Redis cluster migration (3-node: 1 primary, 2 replicas) in April
- Blue-green cutover planned for May to avoid session invalidation
- At projected ~35,000 req/min by end of Q2, monitor whether additional AuthSvc compute is needed

---

### ReportingSvc

**Current state:** Query performance has been degrading as dataset volume grows. The April 2 incident (INC-008) — ETL pipeline timeout on a large dataset query — was a direct consequence of insufficient query optimization for the current data scale.

**Q2 priority:** High

**Scaling need:** Redshift cluster resize planned for May.

**Planned migration:**
- Current: RA3.xlarge (2 nodes)
- Target: RA3.4xlarge (2 nodes)

This change increases compute and managed storage capacity significantly. Before migration, sort keys and distribution style optimizations (flagged in the INC-008 resolution) should be applied — some queries may no longer require a cluster resize after optimization.

**Owner:** Tom Hayes (Team Data). Resize window: second week of May (low-traffic period).

---

### NotificationSvc

**Current state:** SQS consumer count is fixed. Message volume growth is causing queue depth to increase during peak periods, degrading delivery confirmation latency. This is a known architectural gap (flagged in Q4 2025 planning, deferred in February architecture review, now urgent given merchant complaints).

**Q2 priority:** Critical

**Scaling need:** Implement auto-scaling SQS consumers based on queue depth. This is the top Q2 deliverable for Team Engagement.

**Planned approach:**
- Use SQS ApproximateNumberOfMessagesVisible CloudWatch metric to drive ECS task scaling
- Target: consumers scale from minimum 2 to maximum 10 based on queue depth thresholds
- Implement graceful shutdown for consumers on scale-in to avoid message processing interruption

**Owner:** Nina Shah (Team Engagement). Target: deployed to production by end of April.

**Note:** This is the only service where a capacity gap is currently causing active merchant-visible degradation. It takes priority over all other capacity work.

---

### OrderSvc

**Current state:** Stable. Utilization is well within comfortable headroom at current and projected transaction volumes.

**Q2 priority:** Low

**No immediate scaling action required.** Team Commerce should continue monitoring, but no infrastructure changes are planned for OrderSvc in Q2.

---

## Cross-Service Considerations

### Reserved Instance Coverage

As part of the cost optimization initiative (see `cost_optimization_initiative.md`), Q2 is the target window to purchase Reserved Instances for stable workloads. PaymentGW and AuthSvc are candidates for 1-year Reserved Instance coverage once the horizontal scaling architecture for PaymentGW is decided.

### Development Environment Consolidation

Currently each service maintains separate development, staging, and production environments — three environments per service, six services. Consolidating to a shared development environment for lower-traffic services (NotificationSvc, ReportingSvc, OrderSvc) is under consideration.

---

## Review Cadence

This plan will be reviewed at:
- May architecture review (update based on April benchmark results)
- Q2 mid-quarter check-in (early June) — assess whether scaling actions are on track
