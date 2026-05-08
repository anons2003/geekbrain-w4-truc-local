---
title: PaymentGW External API Reference v1.0
status: ARCHIVED
superseded_by: api_reference_v2.md
archived_date: 2025-03-01
owner: Team Platform
tags: [api, paymentgw, archived, v1]
---

# PaymentGW API Reference — v1.0

> **ARCHIVED — This document is superseded by api_reference_v2.md (current as of March 2025).**
> Kept for reference only. Do NOT use v1 endpoints for new integrations.
> Some legacy merchant integrations may still reference this document.

---

## Overview

Version 1.0 of the PaymentGW external API. Released January 2025. This version has been retired
and replaced by v2.0, which adds the `/refunds` endpoint, improved error codes, and a higher
rate limit. If you are starting a new integration, refer to `api_reference_v2.md`.

---

## Authentication

All requests must include an `Authorization` header:

```
Authorization: Bearer <api_key>
```

API keys are issued by the Platform team and must be rotated every 90 days per security policy.

---

## Base URL

```
https://api.geekbrain.internal/v1
```

---

## Rate Limits

**Rate limit: 500 requests per minute** per API key.

Requests exceeding this limit receive HTTP 429 with a `Retry-After` header indicating
when the client may resume.

> Note: v2.0 raises this limit. See `api_reference_v2.md` for current limits.

---

## Endpoints

### POST /payments

Initiates a new payment transaction.

**Request body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant_id` | string | yes | Your merchant identifier |
| `amount` | integer | yes | Amount in minor currency units (e.g., VND đồng) |
| `currency` | string | yes | ISO 4217 currency code (e.g., `VND`) |
| `payment_method` | string | yes | `card` or `bank_transfer` |
| `reference_id` | string | yes | Idempotency key — unique per transaction attempt |
| `metadata` | object | no | Arbitrary key-value pairs, max 10 keys |

**Response (201 Created):**

```json
{
  "payment_id": "pay_abc123",
  "status": "pending",
  "amount": 150000,
  "currency": "VND",
  "created_at": "2025-01-20T09:45:00Z"
}
```

**Status values:** `pending`, `completed`, `failed`

---

### GET /payments/{id}

Retrieves the current status and details of a payment.

**Path parameter:** `id` — payment ID returned from POST /payments

**Response (200 OK):**

```json
{
  "payment_id": "pay_abc123",
  "status": "completed",
  "amount": 150000,
  "currency": "VND",
  "merchant_id": "merchant_xyz",
  "created_at": "2025-01-20T09:45:00Z",
  "completed_at": "2025-01-20T09:45:02Z"
}
```

---

### GET /health

Returns API health status. Useful for uptime checks.

**Response (200 OK):**

```json
{
  "status": "ok",
  "version": "1.0"
}
```

---

## Error Codes

| HTTP Status | Code | Meaning |
|------------|------|---------|
| 400 | `invalid_request` | Missing or malformed fields |
| 401 | `unauthorized` | Invalid or missing API key |
| 404 | `not_found` | Payment ID does not exist |
| 422 | `unprocessable` | Payment declined by upstream bank |
| 429 | `rate_limited` | Exceeded 500 requests/min |
| 500 | `internal_error` | Unexpected server error |

---

## What's Missing in v1

The following capabilities do NOT exist in v1. Use v2 for these:

- `/refunds` endpoint — refunds must be initiated manually via merchant support in v1
- Webhook event `payment.refunded` — not available in v1
- Idempotency guarantees on retries — v1 does not de-duplicate on `reference_id` on all paths

---

## Migration

Merchants on v1 should migrate to v2 at their earliest convenience. Contact Platform team
via #paymentgw-integrations Slack channel for migration support.
