---
title: PaymentGW External API — Reference v2.0
last_updated: 2026-03-01
author: Chris Park
department: Engineering / Team Platform
version: "2.0"
status: CURRENT
---

# PaymentGW External API — v2.0 Reference

> **This is the current API version.** Effective March 2025. If you are using v1 endpoints, migrate to v2. The v1 reference is archived at `api_reference_v1_archived.md`.

## Overview

The PaymentGW API allows merchants to initiate payment transactions, retrieve transaction status, and issue refunds programmatically. It is the primary integration point for external merchant systems connecting to GeekBrain's payment infrastructure.

All API access requires merchant registration and API key issuance via the GeekBrain merchant portal.

## Base URL

```
https://api.geekbrain.io/v2
```

## Authentication

All requests must include two headers:

| Header | Description |
|--------|-------------|
| `X-API-Key` | Your merchant API key |
| `X-Signature` | HMAC-SHA256 signature of the request body |

### Signature Generation

The `X-Signature` is computed as:

```
HMAC-SHA256(secret_key, request_body_as_string)
```

The `secret_key` is your merchant API secret, available from the merchant portal. The signature must be recomputed for every request — it is not reusable.

## Rate Limiting

**Rate limit: 1,000 requests per minute per merchant API key.**

When the rate limit is exceeded, the API returns HTTP 429. The response includes a `Retry-After` header indicating the number of seconds to wait before retrying.

Rate limits are enforced per merchant API key, not per IP address. If you need a higher limit for a specific integration, contact merchant support.

## Endpoints

### POST /payments

Create a new payment transaction.

**Request body:**

```json
{
  "merchant_id": "string",
  "amount": "number (in VND, integer)",
  "currency": "string (VND)",
  "payment_method": "card | bank_transfer",
  "customer_ref": "string (your internal customer ID)",
  "order_ref": "string (your internal order ID)",
  "callback_url": "string (HTTPS URL for webhook delivery)"
}
```

**Response (201 Created):**

```json
{
  "transaction_id": "string",
  "status": "pending",
  "created_at": "ISO8601 timestamp"
}
```

**Notes:**
- The transaction is created in `pending` state. Final status (completed, failed) is delivered via webhook to `callback_url`.
- FraudDetector scoring happens synchronously before this response is returned. If the fraud score exceeds the configured threshold, a 422 is returned with `reason: fraud_score_exceeded`.

---

### GET /payments/{transaction_id}

Retrieve the current status of a transaction.

**Path parameter:** `transaction_id` — the ID returned by POST /payments.

**Response (200 OK):**

```json
{
  "transaction_id": "string",
  "status": "pending | completed | failed | refunded",
  "amount": "number",
  "currency": "string",
  "created_at": "ISO8601 timestamp",
  "updated_at": "ISO8601 timestamp",
  "failure_reason": "string (present if status is failed)"
}
```

---

### POST /refunds

Initiate a refund for a completed transaction. **New in v2.0** — not available in v1.

**Request body:**

```json
{
  "transaction_id": "string",
  "amount": "number (partial or full refund, in VND)",
  "reason": "string (optional)"
}
```

**Response (202 Accepted):**

```json
{
  "refund_id": "string",
  "status": "pending",
  "transaction_id": "string",
  "amount": "number"
}
```

Refunds are processed asynchronously. Status is delivered via webhook.

---

### GET /health

Service health check endpoint. No authentication required.

**Response (200 OK):**

```json
{
  "status": "ok | degraded",
  "timestamp": "ISO8601"
}
```

---

## Webhooks

When a transaction status changes, GeekBrain will POST to the `callback_url` you provided in the payment request.

**Webhook payload:**

```json
{
  "event": "payment.completed | payment.failed | refund.completed",
  "transaction_id": "string",
  "status": "string",
  "timestamp": "ISO8601"
}
```

Webhooks are retried up to 3 times with exponential backoff if your endpoint does not return HTTP 200. Failed webhooks after 3 retries are logged and can be retrieved via the merchant portal.

## Error Codes

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Bad request — invalid request body or missing required fields |
| 401 | Unauthorized — invalid or missing API key, or invalid HMAC signature |
| 422 | Unprocessable — transaction rejected (e.g., fraud score exceeded threshold) |
| 429 | Too many requests — rate limit exceeded; see `Retry-After` header |
| 500 | Internal server error — unexpected error on GeekBrain's side |
| 503 | Service unavailable — upstream bank API is unreachable; retry after a short delay |

## Changelog from v1

- Rate limit increased from 500 to **1,000 requests/min** per merchant key
- `POST /refunds` endpoint added (not available in v1)
- HMAC-SHA256 signature required (replaces simple API key in request header)
- Webhook retry logic improved (3 retries with backoff, up from 1)

## Support

For API integration questions: developer-support@geekbrain.io
For rate limit increase requests: merchant-success@geekbrain.io
