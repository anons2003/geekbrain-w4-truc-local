---
title: Team Data — Team Reference
last_updated: 2026-03-10
author: Ryan Blake
department: Engineering / Data
---

# Team Data

## Overview

Team Data owns the analytics, business intelligence, and fraud detection capabilities at GeekBrain. The team sits at the intersection of engineering and data science, responsible for both operational data pipelines (ReportingSvc) and real-time ML inference (FraudDetector). The team's work directly impacts revenue protection (fraud detection) and business decision-making (reporting and dashboards).

## Lead

**Ryan Blake** — Engineering Lead, Team Data

## Members

| Name | Primary Focus |
|------|--------------|
| Ryan Blake | Lead, data architecture, ML platform |
| Sarah Wells | FraudDetector, model monitoring, anomaly detection |
| Tom Hayes | ReportingSvc, ETL pipelines, Redshift |
| Victor Stone | Data engineering, pipeline reliability, S3/Redshift |
| Wendy Cruz | Business intelligence, dashboards, merchant-facing analytics |

## Services Owned

- **ReportingSvc** — batch and on-demand analytics service (Python, Redshift, S3)
- **FraudDetector** — real-time ML fraud scoring service (Python, SageMaker, DynamoDB)

## On-Call Rotation

- **Schedule**: Weekly rotation
- **Coverage**: PagerDuty for FraudDetector P1/P2 alerts (inline with PaymentGW); ReportingSvc alerts during business hours unless service is fully down
- **Handoff**: Weekly on Mondays
- **Note**: FraudDetector is treated as a P1-capable service because it is in the critical path of every payment transaction. Alerting thresholds are tuned accordingly.

## Focus Areas

### Fraud Detection
Sarah Wells leads model monitoring and drift detection for FraudDetector. Model performance is reviewed continuously, and retraining cadence is a known area requiring improvement — the model is currently retrained quarterly but more frequent retraining has been identified as a need. The decision threshold was adjusted following a model drift incident earlier this year.

### Analytics and Reporting
Tom Hayes and Victor Stone maintain the ETL pipelines that feed ReportingSvc. Daily automated reports and weekly business summaries are scheduled jobs; ad-hoc queries are served on demand. As the dataset grows, query performance has become an increasing concern and ongoing optimization work is in progress.

### ML Platform
Ryan Blake oversees the SageMaker endpoint configuration and DynamoDB feature store. The team is evaluating more automated model monitoring tooling to reduce manual intervention when drift is detected.

### Business Intelligence
Wendy Cruz works with the Merchant Success and Finance teams to maintain dashboards and merchant-facing analytics. This is a largely internal-facing role but with high visibility across the business.

## Dependencies

- **ReportingSvc** reads from read replicas of all services' databases — no direct write access to production databases
- **FraudDetector** is called inline by PaymentGW before every transaction commit; latency SLA is strict
- Team Data coordinates with Team Platform on FraudDetector integration changes

## Escalation

For P1/P2 incidents:
- FraudDetector: on-call → Ryan Blake (15 min) → standard escalation chain
- ReportingSvc: on-call → Ryan Blake (30 min) → standard escalation chain (lower urgency unless ETL failure causes missed SLA reports)

## Team Norms

- Standup: weekdays 10:00 ICT
- Model changes require a documented evaluation against a holdout dataset before deployment
- ETL changes that affect report outputs require Ryan Blake sign-off
- All ML model versions are tagged and stored; rollback must be possible within 30 minutes
- Post-mortems written for all FraudDetector P1/P2 incidents within 48 hours
