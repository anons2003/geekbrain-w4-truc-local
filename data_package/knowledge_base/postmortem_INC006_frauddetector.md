---
title: Postmortem — INC-006 FraudDetector P2, March 12 2026
incident_id: INC-006
service: FraudDetector
severity: P2
date: 2026-03-12
duration_minutes: 90
owner: Team Data
tags: [postmortem, frauddetector, ml, model-drift, false-positive]
---

# Postmortem: INC-006 — FraudDetector P2

**Date:** March 12, 2026
**Duration:** 90 minutes (10:15 – 11:45)
**Severity:** P2 — Single service degraded; legitimate transactions flagged, workaround not practical at scale
**Team:** Team Data
**Facilitator:** Ryan Blake
**Detected by:** Sarah Wells (routine dashboard review)

---

## Summary

The FraudDetector model experienced significant drift caused by Lunar New Year (February 2026)
spending patterns that were not represented in its training data. The model began treating
normal Lunar New Year purchase behavior — higher transaction volumes, new merchant categories,
unusual timing — as anomalous, causing the false positive rate to spike from the baseline of
approximately 2% to approximately 15%. The issue was detected during a routine dashboard check
by Sarah Wells. The team retraining the model with February and March data and adjusting
the decision threshold resolved the incident within 90 minutes.

---

## Timeline

| Time | Event |
|------|-------|
| ~Feb 2026 | Lunar New Year spending patterns begin — high transaction volume, new merchants, unusual hours |
| Feb–Mar | FraudDetector false positive rate gradually increases — not detected immediately |
| 10:15 | Sarah Wells opens daily monitoring dashboard during morning routine |
| 10:15 | Notices false positive rate at 15% (normal baseline: approximately 2%) |
| 10:20 | Sarah Wells alerts Ryan Blake via Slack, opens #incidents thread |
| 10:30 | Ryan Blake confirms via CloudWatch metrics — false positive rate elevated, sustained |
| 10:30 | Incident declared P2 |
| 10:45 | Team hypothesis: model drift from Lunar New Year spending patterns |
| 11:00 | Analysis of prediction score distribution — significant shift from historical baseline |
| 11:00 | Comparison of flagged transactions confirms hypothesis: Lunar New Year categories dominant |
| 11:15 | Decision: retrain model with February–March data and adjust decision threshold |
| 11:20 | Retrain initiated on SageMaker with extended dataset |
| 11:35 | Retrained model passes offline evaluation metrics |
| 11:45 | New model deployed to SageMaker endpoint; decision threshold adjusted from 0.70 to 0.75 |
| 11:45 | False positive rate drops to approximately 3%, continuing to normalize |
| 11:45 | INC-006 closed (monitoring continues) |

---

## Root Cause

The FraudDetector model was trained on transaction data that did not include Lunar New Year
spending patterns. The Lunar New Year period in Vietnam generates a significantly distinct
transaction profile: elevated volumes, higher average amounts, new or infrequent merchant
categories (gifts, travel, dining), and unusual time-of-day distributions.

To the model, this pattern looked like coordinated fraud activity. Scores for legitimate
transactions shifted above the 0.70 decision threshold, causing them to be flagged for
manual review.

The drift was gradual through February — not a sudden spike — which is why it was not
caught by automated alerting (which monitors for sudden changes, not gradual drift).

---

## Contributing Factors

1. **Training data did not include seasonal events**: The initial training dataset was
   collected during a non-holiday period and did not represent Lunar New Year behavior.
2. **No automated drift detection**: There was no alert configured for gradual increases
   in false positive rate — only the absolute rate was monitored, not the trend.
3. **Model retraining was ad-hoc**: There was no scheduled quarterly retraining cycle.
   The model had been running on the same version since its initial deployment.
4. **No A/B model testing pipeline**: The team had no established process to evaluate
   a new model against the current one before production deployment.

---

## Impact

- Approximately 15% of legitimate transactions flagged for manual review during the affected period
- Manual review queue backed up — delays in transaction approvals during peak hours
- Merchant complaints received about delayed payments to their end customers
- Additional load on the team performing manual fraud review

---

## What Was Tried

1. **Threshold adjustment alone** — considered, but a threshold change without retraining
   would reduce true positive detection, increasing fraud risk. Rejected.
2. **Rollback to previous model** — no previous model version available (gap in model versioning).
3. **Retrain with recent data and adjust threshold** — chosen approach. Successful.

---

## Lessons Learned

- Seasonal events (Lunar New Year, year-end, holidays) are predictable and should be
  incorporated into training data proactively, not reactively.
- Gradual drift requires trend-based alerting, not just threshold-based alerting.
  A slowly rising false positive rate can be as damaging as a sudden spike.
- Model versioning and rollback capability are as important for ML services as for
  application code. The lack of a previous model version to roll back to was a gap.
- A/B testing for model deployments reduces risk — new models should carry a portion
  of traffic before full deployment.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Implement automated drift detection — alert if false positive rate >5% sustained 30 min | Sarah Wells | Mar 25 | Done |
| 2 | Establish quarterly model retraining schedule (was ad-hoc) | Ryan Blake | Apr 1 | Scheduled |
| 3 | Include seasonal and holiday patterns in training data pipeline | Victor Stone | Apr 15 | In progress |
| 4 | Implement model versioning with rollback capability in SageMaker | Tom Hayes | Apr 15 | In progress |
| 5 | Design and implement A/B model testing process before full deployment | Ryan Blake | Apr 30 | Planned |

---

## Follow-Up

Quarterly retraining is now on Team Data's calendar: Q2 (June), Q3 (September), Q4 (December).
The Q2 retraining will include a full review of seasonal coverage in the training dataset.
