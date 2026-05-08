---
doc_id: KB-030
title: Runbook — FraudDetector Model Retraining
category: runbook
tags: [runbook, frauddetector, ml, sagemaker, model-retraining, team-data, on-call]
last_updated: 2026-03-15
status: active
owner: Team Data
---

# Runbook: FraudDetector Model Retraining

**Purpose:** Step-by-step guide for retraining and promoting the FraudDetector ML model, both on scheduled cadence and in response to model drift incidents.

**Last updated:** March 15, 2026 (updated post INC-006 to reflect threshold change and new A/B procedure)

**Owner:** Team Data / Ryan Blake

---

## When to Retrain

Retraining is triggered in two ways:

### Scheduled Retraining
Quarterly schedule: **January, April, July, October** (first two weeks of the month).

### Incident-Triggered Retraining
Immediate retraining is required when either of the following conditions is sustained for more than 30 minutes:
- False positive rate exceeds **5%** (flagging legitimate transactions as fraud)
- False negative rate exceeds **1%** (missing fraudulent transactions)

These thresholds are monitored via CloudWatch alarms (added February 2026 after architecture review). On-call engineer will receive a PagerDuty alert.

**Reference:** The March 12, 2026 incident (INC-006) was triggered by model drift. The false positive rate spiked significantly above threshold before being caught by manual review. Automated alerting is now in place.

---

## Retraining Process

### Step 1: Export Training Data

Export the last 90 days of labeled transaction data from the DynamoDB feature store.

```bash
# Run from Team Data's data engineering environment
python scripts/export_training_data.py \
  --days 90 \
  --output s3://geekbrain-ml-data/training/$(date +%Y%m%d)/
```

Verify export completed without errors. Check that the export includes both confirmed fraud labels and confirmed legitimate labels. Imbalanced label distribution (fraud << legitimate) is expected — do not attempt to equalize unless ratio is more extreme than 1:200.

### Step 2: Run SageMaker Training Pipeline

```bash
python scripts/launch_training_job.py \
  --data-path s3://geekbrain-ml-data/training/$(date +%Y%m%d)/ \
  --job-name fraud-model-$(date +%Y%m%d)
```

Monitor job status in SageMaker console or via CLI. Training typically completes in 2–3 hours.

### Step 3: Evaluate on Held-Out Test Set

After training completes, evaluation runs automatically. Review the evaluation report:

```bash
python scripts/evaluate_model.py \
  --model-name fraud-model-$(date +%Y%m%d)
```

**Promotion gates (both must pass):**
- AUC (Area Under Curve): must be **> 0.95**
- False positive rate on test set: must be **< 3%**

If either gate fails, do not promote. Investigate training data quality or feature drift. Escalate to Ryan Blake.

### Step 4: Deploy to Staging Endpoint

```bash
python scripts/deploy_model.py \
  --model-name fraud-model-$(date +%Y%m%d) \
  --endpoint fraud-detector-staging
```

Confirm deployment in SageMaker console. Staging endpoint is isolated from production traffic.

### Step 5: A/B Test — Production Shadow Traffic

Route 10% of production transaction scoring requests to the new model endpoint for 1 hour. PaymentGW is configured to support split routing via an environment variable:

```bash
# In PaymentGW deployment config
FRAUD_MODEL_NEW_ENDPOINT=fraud-detector-staging
FRAUD_MODEL_SPLIT_PERCENT=10
```

Deploy this configuration change to production. During the A/B window, monitor:
- New model false positive rate vs. production model false positive rate
- New model latency p99 (must remain under 150ms)
- Any scoring errors from the new endpoint

### Step 6: Promote to Production (if A/B passes)

If A/B metrics are acceptable after 1 hour:

```bash
python scripts/promote_model.py \
  --model-name fraud-model-$(date +%Y%m%d) \
  --endpoint fraud-detector-production
```

Remove the A/B split configuration from PaymentGW and redeploy to full production routing.

### Step 7: Update Decision Threshold if Needed

The current production decision threshold is **0.75** (transactions scoring above this are flagged as fraud).

This threshold was adjusted from 0.70 following the March 2026 incident (INC-006), which revealed that the previous threshold was too sensitive to the specific transaction patterns seen during the PaymentGW outage window.

If the new model's false positive rate on production is drifting above acceptable levels at 0.75, the threshold can be adjusted upward incrementally. Do not lower the threshold without explicit approval from Ryan Blake — lowering increases false negative risk.

To update threshold:
```bash
# Update in PaymentGW environment config
FRAUD_SCORE_THRESHOLD=0.75
```

---

## Rollback

If any step fails or the promoted model behaves unexpectedly in production:

```bash
python scripts/rollback_model.py \
  --endpoint fraud-detector-production \
  --revert-to-previous
```

The previous model artifact is retained for 30 days before automatic cleanup.

---

## Estimated Duration

End-to-end retraining cycle: **4–6 hours**

| Phase | Duration |
|-------|----------|
| Data export | 20–30 min |
| SageMaker training job | 2–3 hours |
| Evaluation | 15–20 min |
| Staging deploy + A/B test | 1 hour |
| Production promotion | 15 min |

---

## Escalation

If retraining fails or evaluation gates cannot be met, escalate to **Ryan Blake (Team Data Lead)**.

---

## Related Documents

- `postmortem_INC006_frauddetector.md` — Root cause of the March 12 model drift incident
- `monitoring_dashboard_guide.md` — FraudDetector Model Dashboard location
- `on_call_handbook.md` — General on-call procedures
