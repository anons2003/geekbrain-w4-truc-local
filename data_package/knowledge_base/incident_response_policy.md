---
title: Incident Response Policy
status: current
owner: VP Engineering (Mark Sullivan)
last_updated: 2026-01-15
tags: [policy, incident, oncall, escalation, sre]
---

# Incident Response Policy

This document defines how GeekBrain responds to production incidents. All engineering teams
are responsible for knowing and following this policy.

---

## Severity Definitions

### P1 — Critical

**Criteria:** Any of the following:
- Revenue-impacting outage (payment processing unavailable or significantly degraded)
- Multiple services simultaneously affected
- Risk of data loss or data corruption
- Security breach or suspected breach

**Initial response time:** 15 minutes from detection to first response.

**Escalation path:**
1. On-call engineer responds within 15 minutes
2. Team lead notified within 15 minutes of incident declaration
3. VP Engineering **Mark Sullivan** notified within 30 minutes
4. CTO **James Wright** notified within 1 hour if not resolved

**Communication requirements:**
- Public status page updated within 30 minutes of P1 declaration
- Customer-facing communication drafted and reviewed before sending
- #incidents Slack channel used as the primary war room
- Bridge call opened for incidents lasting more than 30 minutes

---

### P2 — High

**Criteria:** Any of the following:
- Single service degraded (not fully down)
- Workaround is available for affected customers
- No risk of data loss
- SLA breach sustained for more than 15 minutes

**Initial response time:** 30 minutes from detection to first response.

**Escalation path:**
1. On-call engineer responds within 30 minutes
2. Team lead notified within 30 minutes of incident declaration

**Communication requirements:**
- #incidents Slack channel updated with status
- No public status page update required unless duration exceeds 2 hours
- Post-incident review within 48 hours

---

### P3 — Low

**Criteria:**
- Minor issue with no direct customer impact
- Performance degradation within acceptable SLA bounds
- Non-urgent alert that needs investigation

**Initial response time:** Next business day.

**Escalation path:**
- On-call engineer investigates and handles
- Team lead informed at next standup (no immediate notification required)

**Communication requirements:**
- Logged in #incidents or team channel
- No post-incident review required unless team lead requests one

---

## Incident Communication

**Primary channel:** All incidents must be tracked in **#incidents** on Slack from start to close.

Standard updates to post:
- `[P{severity}] OPEN — <service>: <one-line description>` when declaring
- Status updates every 30 minutes during active P1, every hour during P2
- `[P{severity}] RESOLVED — <one-line resolution>` when closing

Avoid using DMs for incident coordination — keep communication in #incidents so
the entire team has visibility and can assist.

---

## Post-Incident Review

**P1:** Mandatory post-incident review within 48 hours. All involved engineers attend.
Team lead facilitates. Output: completed postmortem document (see template below).

**P2:** Mandatory post-incident review within 48 hours. Team lead and on-call engineer at minimum.

**P3:** Optional at team lead's discretion.

Postmortem documents are saved in the engineering wiki. Completed examples:
`postmortem_INC005_paymentgw_mar.md`, `postmortem_INC006_frauddetector.md`, others.

---

## Postmortem Template

```
## [INC-XXX] — <Service> <Severity>, <Date>

**Duration:** X minutes/hours

### Timeline
- HH:MM — [Event]
- HH:MM — [Event]
...

### Root Cause
[What caused the incident — technical, process, or both]

### What Was Tried
[Actions taken during the incident, including those that didn't work]

### Lessons Learned
[What the team would do differently]

### Action Items
- [ ] [Owner] [Due date] — [Action]
...
```

---

## On-Call Rotation

Each team maintains its own on-call rotation. Details are in PagerDuty.

- **Team Platform** (PaymentGW, AuthSvc): Weekly rotation, Monday 09:00 handoff
- **Team Commerce** (OrderSvc): Biweekly rotation
- **Team Data** (ReportingSvc, FraudDetector): Weekly rotation
- **Team Engagement** (NotificationSvc): Monthly + PagerDuty backup

When in doubt about who is on-call, check the #oncall Slack channel or PagerDuty.

---

## Deployment-Related Incidents

If an incident is caused by a recent deployment, the first step is rollback via `/rollback <service>`.
Do not attempt to fix-forward during a P1 unless rollback is impossible.
See `deployment_policy.md` for rollback procedures.
