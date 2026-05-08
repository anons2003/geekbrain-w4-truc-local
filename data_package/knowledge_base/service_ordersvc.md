---
title: OrderSvc — Service Reference
last_updated: 2026-02-10
author: Jake Morgan
department: Engineering / Team Commerce
---

# OrderSvc — Service Reference

## Purpose

OrderSvc is GeekBrain's order management service. It governs the full lifecycle of an order from the moment of creation through inventory validation, payment processing, fulfillment handoff, and final completion. It is the backbone of the GeekCommerce product.

## Owner

**Team Commerce** — Lead: Jake Morgan

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Java |
| Framework | Spring Boot |
| Primary database | PostgreSQL |

## Order Lifecycle

OrderSvc manages a defined state machine for every order:

```
create → validate → payment → fulfill → complete
                          ↓
                      [cancelled]
```

- **create**: Order record is created with initial data (merchant, items, amounts, customer)
- **validate**: Inventory availability is confirmed before any payment is attempted. If inventory cannot be confirmed, the order is rejected.
- **payment**: OrderSvc calls PaymentGW to process payment. If payment fails with a transient error, retry logic applies. Non-retriable failures cancel the order.
- **fulfill**: On successful payment, the fulfillment integration is triggered. OrderSvc hands off to the relevant logistics connector.
- **complete**: Fulfillment is confirmed and the order is marked complete. A completion notification is dispatched via NotificationSvc.

## Retry Logic

Payment failures from PaymentGW are classified as retriable or non-retriable:
- **Retriable**: network timeouts, bank temporarily unavailable (503) — retried up to 3 times with exponential backoff
- **Non-retriable**: invalid payment method, fraud rejection, insufficient funds — order is immediately cancelled

## Dependencies

| Service | Why |
|---------|-----|
| **AuthSvc** | Token validation on all inbound API requests |
| **PaymentGW** | Payment processing in the payment state transition |
| **NotificationSvc** | Order status notifications to merchants and customers |

## SLA Targets

OrderSvc carries a 99.9% availability target. Latency requirements are less strict than PaymentGW — the order creation flow involves multiple internal service calls and some additional latency is expected. Full targets are in the SLA CSV.

## Known Issues and Recent History

- A P2 incident in January 2026 involved a memory leak in the order validation module that caused gradual memory exhaustion under sustained load. The validation logic was patched and memory monitoring was added. The issue has been stable since the fix.
- During high-traffic promotions, the inventory validation step has occasionally been a bottleneck. The team has open backlog items to improve caching for high-demand SKUs.

## Runbooks

- Runbook: Order stuck in payment state — manual resolution
- Runbook: Memory usage investigation
- Runbook: Database failover for OrderSvc
- Runbook: OrderSvc rollback procedure

## Contact

For incidents or questions: **Team Commerce** (#commerce in Slack, or page the on-call engineer via PagerDuty).
