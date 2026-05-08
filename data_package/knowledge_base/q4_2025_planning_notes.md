---
doc_id: KB-026
title: Q4 2025 Planning Session — Meeting Notes
category: internal-meeting
tags: [quarterly-planning, q4-2025, paymentgw, authsvc, ordersvc, frauddetector, reportingsvc, notificationsvc, pci-dss]
last_updated: 2025-10-03
status: final
---

# Q4 2025 Planning Session — Meeting Notes

**Date:** October 3, 2025
**Location:** Conference Room A / Zoom hybrid
**Facilitator:** Mark Sullivan (VP Engineering)
**Note-taker:** Ben Torres

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

1. Review Q3 outcomes
2. Set Q4 priorities per team
3. Cross-cutting initiatives
4. Headcount updates

---

## Team Priority Discussions

### Team Platform — PaymentGW and AuthSvc

**PaymentGW:** Primary Q4 focus is reliability. Alex Chen flagged that the circuit breaker implementation for upstream bank API integrations is incomplete — currently the service has no graceful degradation path when bank APIs time out. Work to implement and test circuit breaker patterns for all configured bank API endpoints is the top priority for the quarter.

Mark Sullivan: "We can't have PaymentGW go down because BankAPI-3 is slow. This has to be done before year-end."

**AuthSvc:** JWT rotation is currently a manual process. The October 3 planning decision is to automate key rotation by building a rotation script with pre/post validation hooks. Target: rotation automation in production by November.

### Team Commerce — OrderSvc

**OrderSvc:** Q4 focus on order validation performance. Jake Morgan reported that a memory leak in the validation module was caught in Q3 but only partially resolved. A deeper refactor of the validation pipeline is planned, along with adding memory utilization monitoring. The team also wants to improve integration with fulfillment partners.

No new product features planned for OrderSvc in Q4 — engineering bandwidth is focused on hardening.

### Team Data — FraudDetector and ReportingSvc

**FraudDetector:** Model v2 training is the main Q4 initiative. The current model was trained on data from early 2025; Q4 will expand the training feature set to include new transaction metadata fields that have been collected since Q2. Ryan Blake estimates a 4-week training and validation cycle.

**ReportingSvc:** Redshift cluster optimization. The cluster is showing increasing query times as the dataset grows. Q4 plan: add sort keys to key dimension tables, reorganize distribution styles, and evaluate whether the current cluster size is appropriate for the growing data volume.

### Team Engagement — NotificationSvc

**NotificationSvc:** SQS consumer scaling. Nina Shah raised that message volume has been growing and the current fixed consumer count is becoming a bottleneck. Q4 plan: implement auto-scaling of SQS consumers based on queue depth. Also: review DLQ thresholds and retention settings.

---

## Cross-Cutting Initiatives

### PCI-DSS Level 1 Audit Preparation

James Wright announced that the company is preparing for a PCI-DSS Level 1 audit scheduled for Q1 2026. This is the highest compliance tier and requires involvement from all teams. Responsibilities:

- **Team Platform:** PaymentGW data encryption review, key management audit
- **Team Commerce:** OrderSvc access control and data retention policies
- **Team Data:** FraudDetector data handling and model input data classification
- **Team Engagement:** NotificationSvc PII handling in messages

Security leads from each team to coordinate with the compliance officer. Preliminary self-assessment checklist to be completed by November 15.

---

## Headcount

- **Team Platform:** +1 new hire approved (backend, Go/Node.js). Recruiting to start October.
- **Team Data:** +1 new hire approved (ML engineer). Recruiting to start November.
- Other teams: no headcount changes.

---

## Action Items Summary

| Action | Owner | Due |
|--------|-------|-----|
| Circuit breaker implementation for PaymentGW | Alex Chen | December 15 |
| JWT rotation automation for AuthSvc | Ben Torres | November 30 |
| OrderSvc validation refactor | Jake Morgan | December 15 |
| FraudDetector v2 model training | Ryan Blake | November 30 |
| Redshift optimization | Tom Hayes | November 15 |
| SQS consumer auto-scaling | Nina Shah | December 15 |
| PCI-DSS self-assessment checklist | All team leads | November 15 |
| New hire recruiting kickoff (Platform + Data) | Mark Sullivan / HR | October 15 |

---

## Notes

Circuit breaker and JWT rotation were both identified as Q4 commitments. Status of both will be reviewed at Q4 mid-quarter check-in in November.
