---
title: Deployment Policy
status: current
owner: VP Engineering (Mark Sullivan)
last_updated: 2026-01-10
tags: [policy, deployment, devops, release]
---

# Deployment Policy

This document defines GeekBrain's rules for deploying software changes to production.
All engineering teams must follow this policy. Exceptions require explicit VP Engineering approval.

---

## Deployment Windows

Production deployments are permitted **Monday through Thursday, 09:00–17:00 Vietnam time only**.

This window ensures:
- The full engineering team is available to respond to issues
- Sufficient time for post-deploy monitoring before end of business day
- No deploys happen over weekends when on-call coverage is reduced

---

## Deployment Freeze

**No deployments from Friday 18:00 to Monday 08:00 (Vietnam time).**

This freeze covers the full weekend. It exists because:
- On-call weekend coverage is reduced to one rotation engineer per team
- Rollback capability is slower without the full team available
- Merchant traffic peaks on weekends for many of GeekBrain's e-commerce customers

**Exceptions:** P1 hotfixes only. A P1 hotfix during freeze requires:
1. Incident declared as P1 per `incident_response_policy.md`
2. Written approval from **VP Engineering Mark Sullivan** via Slack DM (screenshot logged to #deployments)
3. Team lead present and monitoring throughout the deploy
4. Mandatory post-deploy retrospective within 48 hours

No other exception categories exist. If you think you have an urgent case that doesn't qualify
as P1, escalate to your team lead — the answer is still no until Monday.

---

## Pre-Deploy Requirements

Every production deployment must satisfy all of the following before proceeding:

1. **PR approved by two reviewers** — both reviewers must be on the same team as the code owner.
   Cross-team review may be added but does not substitute for the two required team reviewers.

2. **CI pipeline green** — all automated checks must pass: unit tests, integration tests,
   security scans, and linting. A failing pipeline blocks the deploy; there are no overrides.

3. **Canary deployment completed** — the new version is first deployed to 5% of production traffic
   and held for a minimum of 15 minutes. Engineers must actively monitor error rate and latency
   during the canary window. If metrics remain within normal bounds, the rollout proceeds to 100%.

---

## Canary Monitoring Criteria

During the 15-minute canary window, watch:

- Error rate must not exceed the service's SLA error threshold (see `sla_policy.md`)
- p99 latency must not increase more than 20% above the rolling baseline
- No new CloudWatch alarms triggered

If any of these are breached during canary, abort and roll back immediately.

---

## Rollback

**Automatic rollback:** If error rate exceeds 5% within 10 minutes of a completed deployment
(canary or full rollout), the system automatically rolls back to the previous version.
An alert fires to #deployments and the deploying engineer is notified.

**Manual rollback:** Engineers can trigger a rollback via the Slack command:

```
/rollback <service-name>
```

Run this in any channel. The bot confirms and initiates rollback. Manual rollback is available
at any time — it does not require VP approval. Use it when you see issues the automated system
hasn't caught.

---

## Deployment Log

All deployments are logged to the **#deployments** Slack channel automatically, including:
- Who deployed
- Service and version deployed
- Canary start/end timestamps
- Final rollout or rollback outcome
- Any alerts triggered

This log is the official record. Do not delete or edit bot messages in #deployments.

---

## Database Schema Changes

Schema changes require additional steps beyond the standard deployment checklist:

- DBA review required (contact Ryan Blake or the Platform team lead)
- Migration must be backward-compatible with the current running code for at least one release
- Schema migrations run before application deployment, not during
- Rollback plan must be documented in the change request before approval

---

## Questions and Escalation

Deployment policy questions → #deployments or your team lead.
Policy exceptions → VP Engineering Mark Sullivan directly.
