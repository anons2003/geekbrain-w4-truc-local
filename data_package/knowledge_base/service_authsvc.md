---
title: AuthSvc — Service Reference
last_updated: 2026-03-01
author: Ben Torres
department: Engineering / Team Platform
---

# AuthSvc — Service Reference

## Purpose

AuthSvc is GeekBrain's centralized authentication and authorization service. It issues and validates OAuth2 access tokens (JWT format) for all other internal services and for external API consumers (merchants). Every service in the GeekBrain stack calls AuthSvc to validate tokens — meaning AuthSvc availability directly determines the availability of all other services.

## Owner

**Team Platform** — Lead: Alex Chen. Ben Torres is the primary engineer for AuthSvc.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Go |
| Session cache | Redis |
| Auth protocol | OAuth2 |
| Token format | JWT (signed) |

## Key Design Properties

### Single Point of Authentication
AuthSvc is intentionally centralized. Every inbound request to every service passes through AuthSvc token validation. This simplifies the security model — there is one place to enforce auth policy — but it means AuthSvc is a critical dependency for the entire platform.

### JWT Signing Key Rotation
JWT tokens are signed with a private key. This key is rotated every 30 days to limit the exposure window in the event of a key compromise. The rotation process is scripted and monitored with alerts; a silent rotation failure is a security risk and has been a focus of hardening efforts after an incident in early 2026.

### Redis Session Cache
Active sessions are cached in Redis with a 24-hour TTL. This allows AuthSvc to serve token validation at very low latency without a database lookup on every request. If Redis becomes unavailable, AuthSvc falls back to the backing store but with significantly higher latency.

### Token Lifetime
Access tokens are short-lived. Refresh tokens are longer-lived and stored in the backing store. The specific TTL values are configured via environment variable and reviewed periodically by the security team.

## SLA Targets

AuthSvc has the highest availability target of any GeekBrain service, reflecting that it is the single point of failure for authentication. The latency target is the most aggressive of any service — it must add minimal overhead to every request. Full targets are in the SLA CSV.

## Availability Impact

If AuthSvc is unavailable or significantly degraded:
- All services stop accepting new requests (token validation fails)
- Merchants cannot transact, create orders, or access any authenticated endpoint
- The entire platform is effectively down from a merchant perspective

For this reason, AuthSvc is deployed with redundancy and its alerts are treated at the highest urgency.

## Known Issues and Recent History

- A P2 incident in February 2026 involved the JWT signing key rotation script failing silently. Keys were not rotated on schedule, which would have eventually caused all tokens signed with the old key to fail. The script was fixed, a pre-rotation validation step was added, and alerting on rotation failure was implemented. The issue was caught before causing merchant impact.
- Redis eviction policy is reviewed quarterly to ensure session cache behavior under memory pressure is predictable.

## Security Notes

- JWT signing key material is stored in AWS Secrets Manager. Application retrieves it at startup and on scheduled rotation.
- OAuth2 client credentials for internal services are managed separately from merchant API keys.
- Any change to AuthSvc that touches key management or token validation logic requires a two-engineer review.

## Runbooks

- Runbook: JWT signing key emergency rotation
- Runbook: Redis cache flush and recovery
- Runbook: AuthSvc failover procedure
- Runbook: Investigating elevated auth error rates

## Contact

For incidents: **Team Platform** (#platform in Slack, PagerDuty on-call). For security questions: Ben Torres directly.
