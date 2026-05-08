---
title: Team Commerce — Team Reference
last_updated: 2026-02-01
author: Jake Morgan
department: Engineering
---

# Team Commerce

## Overview

Team Commerce owns the order management service (OrderSvc) and is responsible for the full order lifecycle — from the moment a merchant or customer creates an order through inventory validation, payment handoff, fulfillment coordination, and final completion. The team works closely with Team Platform (PaymentGW dependency) and Team Engagement (notifications on order events).

## Lead

**Jake Morgan** — Engineering Lead, Team Commerce

## Members

| Name | Primary Focus |
|------|--------------|
| Jake Morgan | Lead, order lifecycle architecture |
| Kyle Reed | Order validation logic, inventory integration |
| Leo Brooks | Payment integration (OrderSvc ↔ PaymentGW) |
| Maya Scott | Fulfillment integrations, third-party logistics connectors |
| Nick Foster | Database, query optimization, PostgreSQL |
| Oscar Grant | API design, merchant-facing endpoints, testing |

## Services Owned

- **OrderSvc** — Java/Spring Boot service managing the full order lifecycle

## On-Call Rotation

- **Schedule**: Biweekly rotation (each engineer is on-call for two weeks at a time)
- **Coverage**: PagerDuty escalation for P1/P2 alerts; P3 issues handled during business hours
- **Handoff**: Biweekly on Mondays
- **Point of contact**: Current on-call engineer; Jake Morgan for escalations

## Focus Areas

### Order Lifecycle
OrderSvc owns the state machine that governs order progression: create → validate → payment → fulfill → complete. Every state transition has defined business rules, and the team maintains strict consistency guarantees across transitions.

### Inventory Validation
Before an order is committed, OrderSvc checks inventory availability. This integration is critical to prevent overselling, particularly during high-traffic promotional periods.

### Fulfillment Integration
Maya Scott leads integrations with third-party logistics and fulfillment providers. These are external HTTP integrations with variable reliability, so the team maintains retry logic and fallback states.

### Payment Failure Handling
OrderSvc has retry logic for payment failures (transient errors from PaymentGW or upstream banks). Non-retriable failures result in order cancellation with appropriate merchant and customer notification.

## Dependencies

OrderSvc depends on:
- **AuthSvc** (Team Platform) — token validation on all requests
- **PaymentGW** (Team Platform) — payment processing
- **NotificationSvc** (Team Engagement) — sending order status notifications to merchants and customers

## Escalation

For P1/P2 incidents involving OrderSvc:
1. On-call engineer responds
2. If not resolved within 30 minutes: Jake Morgan (team lead) is paged
3. Further escalation follows the standard escalation policy

## Team Norms

- Standup: weekdays 09:45 ICT
- Code reviews: one approval required; two for any change touching the order state machine
- Database migrations require Nick Foster review before merging
- Integration changes with Team Platform are coordinated via the #platform-commerce Slack channel
- Incident post-mortems written for P1/P2 within 48 hours
