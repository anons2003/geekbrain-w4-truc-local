---
doc_id: KB-025
title: Q1 2026 Quarterly Review — Meeting Notes
category: internal-meeting
tags: [quarterly-review, q1-2026, paymentgw, frauddetector, notificationsvc, planning]
last_updated: 2026-04-05
status: final
---

# Q1 2026 Quarterly Review — Meeting Notes

**Date:** April 5, 2026
**Location:** Conference Room B / Zoom hybrid
**Facilitator:** James Wright (CTO)
**Note-taker:** Alex Chen

## Attendees

| Name | Role |
|------|------|
| James Wright | CTO |
| Mark Sullivan | VP Engineering |
| Alex Chen | Team Platform Lead |
| Jake Morgan | Team Commerce Lead |
| Ryan Blake | Team Data Lead |
| Nina Shah | Team Engagement Lead |

---

## Agenda

1. Q1 retrospective — what went well, what didn't
2. Incident review highlights
3. Cost discussion
4. Q2 planning priorities
5. Headcount updates
6. Action items

---

## Discussion Notes

### (a) PaymentGW — Cost Growth Concern

James Wright opened with concern that PaymentGW costs grew significantly faster than transaction volume in Q1. Specific observation: the gap widened in March, which may be related to catch-up processing and retries following the March 5 P1 incident.

Mark Sullivan noted that the March incident likely caused unusually high third-party API call volume as the service retried upstream bank requests during the outage window. The cost baseline should normalize in April, but root cause analysis is required.

**Action:** Alex Chen to lead a root cause investigation on PaymentGW cost composition by April 20. Cost optimization plan due April 30.

### (b) FraudDetector — Monitoring Gap Exposed

The March 12 model drift incident (INC-006) surfaced a structural problem: the team was relying on manual dashboard checks to detect false positive rate degradation. The spike from ~2% to ~15% was caught by Sarah Wells during routine review rather than by automated alerting.

Ryan Blake acknowledged the gap. A dedicated CloudWatch alarm on false positive rate has since been added, but the review raised questions about what other model health metrics lack automated coverage.

**Action:** Ryan Blake to audit all FraudDetector model health metrics for alerting coverage by April 15.

### (c) NotificationSvc — Merchant Complaints and Resource Constraints

Nina Shah reported that merchants have been escalating complaints about slow delivery confirmations. The issue appears tied to growing message volumes that the current fixed SQS consumer configuration cannot absorb efficiently.

Mark Sullivan noted that Team Engagement is the smallest engineering team by headcount and is responsible for a service with increasing user-facing impact. A resource reallocation discussion is warranted.

**Action:** Mark Sullivan to schedule a capacity review for NotificationSvc by April 12. Potential reallocation of one engineer from Team Commerce to Team Engagement to be discussed.

### (d) Positive: Refund API Launch

Jake Morgan highlighted that the new refund API endpoint shipped in Q1 with no incidents and positive merchant feedback. The launch went smoothly, and merchant support ticket volume related to refunds has dropped since launch. Recognized as a clean execution by Team Commerce.

### (e) Headcount Approval

James Wright confirmed two new engineer hires approved for Team Platform (to support PaymentGW scaling and AuthSvc reliability work). Offers expected to go out in April, onboarding targeted for May.

### (f) Cost Optimization Directive

All team leads are required to submit infrastructure cost optimization plans by **April 30, 2026**. Plans should identify specific cost reduction opportunities without compromising SLA commitments. VP Mark Sullivan will consolidate and prioritize.

---

## Action Items Summary

| Action | Owner | Due |
|--------|-------|-----|
| PaymentGW cost root cause investigation | Alex Chen | April 20 |
| FraudDetector monitoring audit | Ryan Blake | April 15 |
| NotificationSvc capacity review | Mark Sullivan | April 12 |
| All teams: cost optimization plans | Each team lead | April 30 |
| New hire offers (Team Platform x2) | James Wright / HR | April 30 |

---

## Next Meeting

Q2 mid-quarter check-in tentatively scheduled for early June 2026.
