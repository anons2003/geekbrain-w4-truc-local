---
doc_id: KB-032
title: On-Call Handbook for GeekBrain Engineers
category: operations
tags: [on-call, incident-response, pagerduty, grafana, handbook]
last_updated: 2026-03-15
status: active
---

# On-Call Handbook for GeekBrain Engineers

**Purpose:** Practical guide for engineers taking on-call shifts. Covers tooling, first-response procedures, common scenarios, and escalation.

---

## On-Call Rotation Schedule

Each team manages its own rotation. See team-specific Confluence pages for the live schedule.

| Team | Rotation Frequency | Handoff |
|------|--------------------|---------|
| Team Platform | Weekly | Monday 09:00 ICT |
| Team Commerce | Biweekly | Monday 09:00 ICT |
| Team Data | Weekly | Monday 09:00 ICT |
| Team Engagement | Monthly + PagerDuty backup | Monday 09:00 ICT |

If you are unsure who is currently on call, check the `#on-call` Slack channel — the current on-call engineer pins themselves at handoff time.

---

## Required Tools

Ensure you have access to all of these before your first shift:

| Tool | Purpose | Access |
|------|---------|--------|
| PagerDuty | Primary alerting | Mobile app + web. Ensure mobile notifications are enabled. |
| Slack `#incidents` | Incident communication | All engineers should be in this channel. |
| Grafana (`grafana.internal`) | Service dashboards | VPN required |
| AWS Console | Infrastructure management | IAM role via team lead |
| GitHub | Deployment review, log access | Org access via team lead |

---

## First Response Protocol

When you receive a PagerDuty alert, follow these steps in order.

### Step 1 — Acknowledge

Acknowledge the alert in PagerDuty within **5 minutes**. If you do not acknowledge within 5 minutes, the alert escalates to your team lead automatically.

### Step 2 — Assess Scope

Open Grafana → Service Health Overview. Check:
- Which service(s) show degraded status or active alerts?
- Are multiple services affected? (May indicate upstream dependency failure)
- When did the issue start?

### Step 3 — Classify Severity

Refer to `incident_response_policy.md` for full severity definitions. Quick reference:

| Severity | Description |
|----------|-------------|
| **P1** | Production down or severely degraded. SLA breach imminent or occurring. Customer-visible. |
| **P2** | Degraded performance or elevated errors. Not fully down. SLA at risk. |
| **P3** | Minor issue. No customer impact. Can be addressed during business hours. |

### Step 4 — Communicate

- **P1:** Immediately post in `#incidents` with: service name, observed symptom, severity, time started. Then escalate per Step 5.
- **P2:** Post in `#incidents`. No immediate escalation unless it worsens.
- **P3:** Investigate. No Slack post required. Update team at next standup.

Template for `#incidents` post:
```
[P1] PaymentGW — circuit breaker open for BankAPI-1
Started: ~10:32 ICT
Symptom: Transactions to BankAPI-1 failing fast. ~40% of payment volume affected.
On-call: [your name]
Investigating now.
```

### Step 5 — Escalate (P1 only)

P1 escalation path:
1. **On-call engineer** — immediate response
2. **Team lead** — call/page at 15 minutes if not resolved
3. **VP Engineering Mark Sullivan** — call at 30 minutes if not resolved
4. **CTO James Wright** — call at 1 hour if not resolved

For P2: escalate to team lead at 30 minutes if not resolved.

---

## Common Scenarios and First Steps

### High Latency Alert

1. Check Grafana → affected service dashboard → latency panels
2. Check CPU and memory utilization — are resources saturated?
3. Check recent deployments — was there a canary or config change in the last 2 hours?
4. Check upstream dependency health (especially if it's PaymentGW — check bank API health)

### Error Rate Spike

1. Check Grafana → affected service dashboard → error breakdown panel
2. Check recent deployments (GitHub Actions → deployment history)
3. If a canary was deployed: is the error rate elevated on the new version only? If so, rollback.
4. Check dependency health — is an upstream service causing errors?

### Circuit Breaker Open (PaymentGW)

Follow `runbook_paymentgw_circuit_breaker.md`.

Summarized:
1. Check `/admin/circuit-breaker/status` to confirm state and identify which bank is affected
2. Check bank API health ping endpoint
3. If upstream is confirmed recovered: POST to `/admin/circuit-breaker/reset`
4. If reset fails within 10 min: escalate to Alex Chen

### Model Drift Alert (FraudDetector)

Follow `runbook_frauddetector_model_retraining.md`.

Summarized:
1. Check Grafana → FraudDetector Model Dashboard → false positive/negative rates
2. Check feature drift panel — which features are deviating?
3. If drift confirmed: initiate emergency retraining procedure
4. Escalate to Ryan Blake if retraining cannot start within 1 hour

### SQS DLQ High Depth (NotificationSvc)

1. Check CloudWatch → NotificationSvc DLQ depth metric
2. Check consumer error logs for the specific message failure pattern
3. If messages are poisoned (cannot be processed): increase DLQ retention to prevent data loss
4. Implement consumer fix if the root cause is a code bug
5. Escalate to Nina Shah if unclear

---

## After Resolution

### All incidents
- Update PagerDuty: add resolution notes and mark resolved
- Post resolution message in `#incidents`

### P1 and P2 incidents
- File a post-incident review (postmortem) within **48 hours** of resolution
- Use the postmortem template in Confluence
- Share in `#engineering` and schedule a brief sync with the team

---

## Shift Handoff Checklist

At handoff:
- [ ] Confirm outgoing on-call acknowledges handoff in `#on-call`
- [ ] Review any open or recently resolved incidents from your shift
- [ ] Verify no alerts are still in triggered state
- [ ] Brief the incoming on-call on any active risks or watch items

---

## Related Documents

- `incident_response_policy.md` — Full severity definitions and SLA breach thresholds
- `monitoring_dashboard_guide.md` — Dashboard locations and what each shows
- `runbook_paymentgw_circuit_breaker.md`
- `runbook_frauddetector_model_retraining.md`
- `deployment_policy.md` — Deployment freeze windows (relevant for hotfix decisions)
