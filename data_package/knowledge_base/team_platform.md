---
title: Team Platform — Team Reference
last_updated: 2026-02-15
author: Alex Chen
department: Engineering
---

# Team Platform

## Overview

Team Platform owns the core payment and authentication infrastructure. This is the highest-stakes team at GeekBrain — the services we own are in the critical path of every transaction and every authenticated request across the platform.

## Lead

**Alex Chen** — Engineering Lead, Team Platform

## Members

| Name | Primary Focus |
|------|--------------|
| Alex Chen | Lead, architecture, PaymentGW reliability |
| Ben Torres | AuthSvc, security, JWT/OAuth2 |
| Chris Park | PaymentGW, bank API integrations |
| David Kim | PaymentGW, performance and capacity |
| Emily Ward | AuthSvc, session management, Redis |
| Frank Liu | PaymentGW, circuit breaker and resilience patterns |
| Grace Lin | Observability, alerting, incident response |
| Hannah Cole | Full-stack platform, internal tooling |

## Services Owned

- **PaymentGW** — payment gateway processing credit cards and bank transfers
- **AuthSvc** — OAuth2/JWT authentication serving all other services

## On-Call Rotation

- **Schedule**: Weekly rotation
- **Handoff**: Every Monday at 09:00 ICT
- **Rotation members**: All 8 team members rotate in sequence
- **Coverage**: 24/7 PagerDuty escalation for P1/P2 alerts
- **Primary contact during business hours**: Current on-call engineer or team lead

## Focus Areas

### Payment Reliability
PaymentGW must maintain high availability and low latency at all times. Bank API integrations are inherently unreliable and require careful circuit breaker management. The team prioritizes graceful degradation over hard failures.

### Authentication
AuthSvc is a single point of authentication for every service. Downtime on AuthSvc cascades to all services immediately. The team treats AuthSvc availability as the highest internal priority.

### Security
Ben Torres leads security practices including JWT signing key rotation (every 30 days), API key management, and coordination with compliance on PCI-DSS requirements. Any security-sensitive change requires two-engineer review.

## Escalation

For P1 incidents involving PaymentGW or AuthSvc:
1. On-call engineer responds immediately
2. If not resolved within 15 minutes: page Alex Chen (team lead)
3. If not resolved within 30 minutes: escalate to VP Engineering Mark Sullivan
4. If not resolved within 1 hour: CTO James Wright is notified

## Recent Context

The team has been focused on improving resilience following incidents earlier in the year. Circuit breaker configuration and bank API failover have been areas of active improvement. JWT key rotation automation was also hardened after a near-miss incident.

## Team Norms

- Code reviews: minimum one approval, two for security-related changes
- Runbooks are required before any new alert is added to PagerDuty
- Post-mortems are written for all P1 and P2 incidents within 48 hours
- Team standup: weekdays 09:30 ICT
