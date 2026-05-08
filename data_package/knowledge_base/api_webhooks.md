---
title: PaymentGW Webhook Documentation
status: current
owner: Team Platform
last_updated: 2026-02-01
tags: [api, paymentgw, webhooks, events]
---

# PaymentGW Webhook Documentation

Webhooks allow your system to receive real-time notifications when payment events occur.
Instead of polling the API, GeekBrain pushes event data to a URL you configure.

---

## Overview

When a payment transitions state, PaymentGW dispatches an HTTP POST to your registered
webhook URL. Your endpoint must respond with HTTP 200 within 5 seconds or the delivery
is considered failed and enters the retry cycle.

---

## Configuration

Webhook URLs are registered through the merchant portal or via the Platform team for
enterprise integrations. Requirements:

- URL must use **HTTPS** — plain HTTP is rejected
- URL must be reachable from GeekBrain's egress IP range (see `security_policy.md` for network details)
- Only one webhook URL per merchant API key in v2

---

## Event Types

| Event | Trigger |
|-------|---------|
| `payment.completed` | Payment successfully processed by upstream bank |
| `payment.failed` | Payment rejected by bank, fraud check, or timeout |
| `payment.refunded` | Refund successfully processed (v2+ only) |
| `payment.disputed` | Merchant or cardholder raised a dispute |

---

## Payload Format

All events share the same envelope structure:

```json
{
  "event_type": "payment.completed",
  "payment_id": "pay_abc123",
  "amount": 150000,
  "currency": "VND",
  "timestamp": "2026-02-14T08:30:00Z",
  "merchant_id": "merchant_xyz",
  "metadata": {}
}
```

**Field descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | One of the event types listed above |
| `payment_id` | string | Unique payment identifier |
| `amount` | integer | Amount in minor currency units |
| `currency` | string | ISO 4217 code |
| `timestamp` | string | ISO 8601 UTC timestamp when event occurred |
| `merchant_id` | string | Your merchant identifier |
| `metadata` | object | Key-value pairs passed in the original payment request |

---

## Signature Verification

Each webhook delivery includes an `X-GeekBrain-Signature` header. This is an
HMAC-SHA256 signature computed over the raw request body using your webhook signing secret.

**Verification (Python example):**

```python
import hmac
import hashlib

def verify_signature(payload_bytes: bytes, header: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    received = header.split("sha256=")[-1]
    return hmac.compare_digest(expected, received)
```

**Always verify the signature before processing.** Reject requests that fail verification
with HTTP 401.

---

## Retry Policy

If your endpoint does not return HTTP 200 within 5 seconds, or returns any non-2xx status,
GeekBrain retries with exponential backoff:

| Attempt | Delay |
|---------|-------|
| 1st retry | 1 second after initial failure |
| 2nd retry | 5 seconds after 1st retry |
| 3rd retry | 25 seconds after 2nd retry |

After 3 failed attempts the event is marked `undelivered`. Undelivered events are logged
and visible in the merchant portal for manual inspection. We do not retry beyond 3 attempts.

**Make your endpoint idempotent.** In rare cases, network issues may cause duplicate
deliveries even on successful attempts. Use `payment_id` + `event_type` as the idempotency key.

---

## Best Practices

- Respond with HTTP 200 immediately, then process asynchronously (queue the event internally)
- Log all received webhook payloads for debugging
- Monitor your endpoint response times — exceeding 5s causes unnecessary retries
- Rotate your webhook signing secret the same cycle as your API key (every 90 days)

---

## Testing

Use the merchant portal sandbox environment to trigger test events. Sandbox payments
use the prefix `pay_test_` and are never routed to real bank APIs.

For questions, contact #paymentgw-integrations on Slack.
