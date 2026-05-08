---
title: NotificationSvc — Service Reference
last_updated: 2026-04-01
author: Nina Shah
department: Engineering / Team Engagement
---

# NotificationSvc — Service Reference

## Purpose

NotificationSvc is GeekBrain's asynchronous notification service. It delivers order confirmations, delivery updates, merchant alerts, and marketing messages via email (SES), SMS (SNS), and push notification channels. It operates fully asynchronously — callers publish events to a queue and NotificationSvc processes them independently.

## Owner

**Team Engagement** — Lead: Nina Shah

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python |
| Message queue | AWS SQS |
| Email delivery | AWS SES |
| SMS / push | AWS SNS |

## Architecture

NotificationSvc is queue-driven. Upstream services (primarily OrderSvc) publish notification events to SQS. Consumer workers pull messages from the queue and dispatch them via the appropriate channel (email, SMS, push). This decouples notification delivery from the request path of upstream services.

### Dead Letter Queue (DLQ)
Messages that cannot be processed after a configured number of retries are moved to a dead letter queue. The DLQ is monitored with a CloudWatch alarm that fires when the message count exceeds a threshold. DLQ contents are reviewed weekly and processed manually or via re-drive as appropriate.

### Message Types

| Type | Channel | Trigger |
|------|---------|---------|
| Order confirmation | Email | Order moves to payment-complete state |
| Delivery update | Email / SMS | Fulfillment status change |
| Merchant alert | Email / SMS | Account event (payout, unusual activity) |
| Marketing | Email | Campaign-driven, scheduled |

## Current Status and Known Issues

NotificationSvc is the service most visibly under strain at GeekBrain's current scale. Two issues are active:

**1. Notification delivery latency**
As transaction volume has grown, the consumer workers have not scaled proportionally. Messages are spending more time in the queue before being processed. Merchants have reported that order confirmation emails are arriving later than expected. This is a known issue being tracked by Team Engagement and leadership.

**2. Resource utilization**
The service is running at elevated CPU and memory utilization relative to its provisioned capacity. The team has been allocated additional capacity planning time in Q2 2026.

A DLQ overflow incident in March 2026 (see INC-007) revealed that the DLQ retention period was too short and the alerting threshold was set too high. Both have been corrected, but the root cause — insufficient consumer throughput — remains an open item.

## SLA Targets

NotificationSvc has a more lenient availability target than the payment and auth services, reflecting that notification delays are disruptive but not payment-blocking. The error rate and latency targets are also set to account for the asynchronous nature of the service. Full targets are in the SLA CSV.

## Dependencies

- **SQS** — AWS managed queue; messages persist if consumers are slow
- **SES** — email delivery; subject to SES sending limits and reputation management
- **SNS** — SMS and push; subject to SNS quotas per region

## Runbooks

- Runbook: DLQ re-drive — processing stuck messages
- Runbook: SES sending quota investigation
- Runbook: Consumer worker scaling
- Runbook: NotificationSvc deployment and rollback

## Contact

For incidents: **Team Engagement** (#engagement in Slack, PagerDuty). For sustained merchant complaints about notification delays, also loop in Merchant Success.
