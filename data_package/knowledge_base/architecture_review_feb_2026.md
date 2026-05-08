---
doc_id: KB-028
title: Architecture Review — February 2026
category: architecture
tags: [architecture-review, frauddetector, authsvc, paymentgw, notificationsvc, sagemaker, redis, circuit-breaker, sqs]
last_updated: 2026-02-20
status: final
---

# Architecture Review — February 2026

**Date:** February 20, 2026
**Frequency:** Quarterly
**Facilitator:** Mark Sullivan (VP Engineering)
**Participants:** Alex Chen, Ryan Blake, Nina Shah, Jake Morgan, Ben Torres, Sarah Wells

---

## Purpose

Quarterly deep-dive into architecture health across all six services. Goal: identify technical debt, scaling risks, and design gaps before they become incidents. Decisions made here feed into capacity planning and quarterly team priorities.

---

## Agenda Topics

1. FraudDetector — SageMaker endpoint scaling
2. AuthSvc — Redis single-node risk
3. PaymentGW — Circuit breaker health check configuration
4. NotificationSvc — SQS consumer architecture
5. Cross-service: observability gaps

---

## Topic 1: FraudDetector — SageMaker Endpoint Scaling

**Current state:** FraudDetector runs on a single SageMaker managed endpoint configured on `ml.m5.xlarge`. Sarah Wells presented throughput measurements showing the endpoint handles approximately 12,000 requests per minute comfortably under current load, with p99 latency well within the 150ms SLA target.

**Projected need:** Based on Q2 2026 transaction growth projections (15% quarter-over-quarter), the service will need to sustain approximately 15,000 requests per minute by Q3 2026.

**Options evaluated:**
- Option A: Upgrade to a larger instance type (e.g., `ml.m5.2xlarge`) — simpler operationally, no architectural change required, but linear cost increase.
- Option B: Horizontal endpoint scaling (multiple instances behind SageMaker load balancer) — more resilient, better cost-per-request at scale, but adds operational complexity and requires testing the load balancer behavior under fraud scoring patterns.

**Decision:** Defer to Q2 2026. Both options are viable. Team Data to continue monitoring latency as volume grows and initiate the evaluation in Q2. If p99 approaches 140ms sustained, escalate before scheduled Q2 review.

---

## Topic 2: AuthSvc — Redis Single-Node Risk

**Current state:** AuthSvc uses a single Redis node for session cache and JWT validation caching. This is a single point of failure (SPOF) — if the Redis node goes down, AuthSvc loses its cache layer entirely, which may force fall-through to full database validation for every request, significantly increasing latency and database load.

**Risk assessment:** High. AuthSvc has a 99.99% availability SLA and is a dependency of PaymentGW, OrderSvc, and all other authenticated services. A Redis failure would cascade.

**Recommendation:** Migrate to Redis cluster with minimum 3 nodes (1 primary, 2 replicas) with automatic failover. This provides availability during a single node failure without application-level changes.

**Timeline:** Q2 2026. Ben Torres to lead the migration design and rollout plan. Blue-green migration approach recommended to avoid session invalidation for live users.

**Owner:** Ben Torres (Team Platform)

---

## Topic 3: PaymentGW — Circuit Breaker Health Check Configuration

**Current state:** PaymentGW has circuit breaker logic implemented for upstream bank API calls. During review, a configuration issue was flagged: the health check endpoint used to determine whether an upstream bank is available is not correctly parsing all upstream response codes. Specifically, certain non-200 success codes (e.g., 206, 207) from bank APIs are being treated as failure signals, which could cause the circuit breaker to trip incorrectly under some conditions.

**Risk:** False positive circuit breaker trips under non-error conditions. The current configuration is conservative enough that this hasn't caused a production issue, but it is an incorrect implementation.

**Recommendation:** Update health check parsing to correctly interpret upstream response codes per each bank's API specification. Add test coverage for each bank API integration's response code behavior.

**Status:** Flagged as "needs improvement." Not blocking, but should be addressed before any future circuit breaker incidents are investigated, as the incorrect configuration may complicate root cause analysis.

**Owner:** Alex Chen (Team Platform). Target: March 2026.

---

## Topic 4: NotificationSvc — SQS Consumer Architecture

**Current state:** NotificationSvc processes messages via a fixed number of SQS consumers. The consumer count is set statically at service startup and does not adjust based on queue depth or backlog.

**Observed pattern:** As message volume grows (particularly during peak order periods), the queue depth increases and messages take longer to process. Delivery confirmation latency for merchants degrades as a result.

**Recommendation:** Implement auto-scaling of SQS consumers based on queue depth metrics. This can be achieved via SQS queue depth CloudWatch metrics + Lambda-based or ECS task-based consumer scaling. Nina Shah confirmed this work was in the Q4 2025 plan but was not completed.

**Status:** Not yet implemented. Nina Shah noted Team Engagement is at capacity and this was deprioritized. Mark Sullivan noted this needs to move up — merchant-visible latency issues cannot be deferred indefinitely.

**Owner:** Nina Shah (Team Engagement). Q2 2026 must-do.

---

## Topic 5: Observability Gaps (Cross-Cutting)

Brief discussion of monitoring gaps across services:

- FraudDetector lacks automated alerting on false positive / false negative rate degradation (relies on manual review). Action: Ryan Blake to add CloudWatch metric filters and alarms.
- PaymentGW circuit breaker state is not currently surfaced in the shared Grafana Service Health Overview dashboard. Action: Alex Chen to add circuit breaker state widget.
- ReportingSvc ETL pipeline duration is not tracked as a metric. Action: Tom Hayes to instrument query duration and add a >25 min alarm.

---

## Next Architecture Review

Scheduled for May 2026. Key topics to carry forward:
- FraudDetector scaling decision (evaluate if traffic projections are tracking)
- AuthSvc Redis cluster migration status
- NotificationSvc auto-scaling implementation review
