---
title: PaymentGW — Service Reference
last_updated: 2026-03-15
author: Alex Chen
department: Engineering / Team Platform
---

# PaymentGW — Service Reference

## Purpose

PaymentGW is GeekBrain's payment gateway. It processes credit card transactions and bank transfers on behalf of merchants, connecting upstream to Vietnamese bank APIs and downstream to the fraud detection and authentication layers.

## Owner

**Team Platform** — Lead: Alex Chen

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Node.js |
| Framework | Express |
| Primary database | PostgreSQL |
| Bank connectivity | HTTP integrations (VCB, Techcombank, BIDV) |
| Resilience | Circuit breaker per bank API |
| Auth | AuthSvc (token validation on all inbound requests) |
| Fraud check | FraudDetector (inline scoring before commit) |

## Upstream Bank Integrations

PaymentGW connects to three Vietnamese bank APIs:

- **VCB** (Vietcombank) — primary high-volume bank route
- **Techcombank** — secondary route
- **BIDV** — tertiary route

Each bank API integration has an independent circuit breaker. If a bank API becomes unresponsive or returns a high rate of errors, the circuit breaker opens and requests are routed to an alternate bank where possible. The circuit breaker state is monitored and alerts fire when a breaker opens.

## Request Flow

For each incoming payment:
1. AuthSvc validates the inbound API token
2. FraudDetector scores the transaction (must return within latency SLA)
3. If fraud score is below the configured threshold, PaymentGW proceeds
4. PaymentGW selects a bank route and submits the transaction
5. Result is returned to the caller; async webhook callback is queued for status updates

## Capacity and Performance Characteristics

PaymentGW is the highest-throughput service in the stack. It is designed to handle a large volume of concurrent transactions per minute. Latency is a critical concern — payment requests that time out result in poor merchant and customer experience and can cause duplicate submission problems.

The service has been scaling to meet growing transaction volume. Compute costs have risen materially over the past two quarters as throughput has increased, which has drawn attention in planning discussions.

## SLA Targets

PaymentGW carries the second-highest availability target at GeekBrain (after AuthSvc), reflecting its role as the revenue-generating service. Latency and error rate are monitored on a rolling basis. Full target values are maintained in the SLA target CSV.

## Known Issues and Recent History

- A P1 incident in March 2026 involved the circuit breaker becoming stuck in the open state following a cascade of upstream bank API timeouts. The incident resulted in an extended outage. A post-mortem was written (see `postmortem_INC005_paymentgw.md`). Circuit breaker configuration and fallback routing were improved as a result.
- Operating costs have been rising faster than revenue growth, flagged during the Q1 review. Cost optimization for PaymentGW is a priority initiative.

## Runbooks

- Runbook: Circuit breaker manual reset
- Runbook: Bank API failover procedure
- Runbook: Database connection pool emergency scaling
- Runbook: PaymentGW rollback procedure

All runbooks are maintained in the internal wiki and linked from PagerDuty alerts.

## Contact

For incidents or questions: **Team Platform** (#platform in Slack, or page the on-call engineer via PagerDuty).
