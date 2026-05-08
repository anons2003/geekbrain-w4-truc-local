---
title: FraudDetector — Service Reference
last_updated: 2026-03-25
author: Sarah Wells
department: Engineering / Team Data
---

# FraudDetector — Service Reference

## Purpose

FraudDetector provides real-time machine learning fraud scoring for every payment transaction. It is called by PaymentGW before any transaction is committed to the bank. If the fraud score exceeds a configured threshold, the transaction is rejected. This service is the primary defense against fraudulent transactions on the GeekBrain platform.

## Owner

**Team Data** — Lead: Ryan Blake. Sarah Wells is the primary engineer for model monitoring and operations.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python |
| ML inference | AWS SageMaker endpoint |
| Feature store | AWS DynamoDB |
| Model storage | S3 (versioned model artifacts) |

## Architecture

### Scoring Flow

For every transaction that PaymentGW receives:
1. FraudDetector is called synchronously with transaction features (merchant ID, amount range, payment method type, customer behavior signals, etc.)
2. FraudDetector retrieves precomputed features from the DynamoDB feature store (sub-millisecond lookup)
3. The SageMaker endpoint runs the ML model inference
4. A score between 0 and 1 is returned to PaymentGW
5. PaymentGW compares the score against the configured decision threshold and either proceeds or rejects the transaction

### Decision Threshold

The current decision threshold is **0.75**. Transactions with a fraud score at or above 0.75 are rejected. This threshold was adjusted upward from 0.70 following a model drift incident in March 2026 that caused an elevated false positive rate (see `postmortem_INC006_frauddetector.md`). Threshold adjustments require Team Data lead sign-off and are documented.

## Latency Requirement

FraudDetector has a strict sub-200ms latency requirement at the p99 level. Because it sits inline in the payment processing flow, any latency added by FraudDetector directly adds to the merchant-facing payment response time. The SageMaker endpoint and DynamoDB feature store are both configured and sized to meet this target.

## Model Details

### Training
The model is trained on historical transaction data from GeekBrain's own transaction history. Features include merchant behavior patterns, transaction characteristics, customer device signals, and temporal patterns (time of day, day of week).

### Retraining Cadence
The model is currently retrained quarterly. This cadence has been flagged as insufficient — fraud patterns evolve faster than a quarterly cycle can capture, and the March 2026 model drift incident demonstrated the risk. The team is evaluating a move to monthly retraining, subject to the engineering effort required to make the pipeline more automated.

### Model Versioning
All model versions are stored in S3 with version tags. A rollback to a previous model version can be performed within 30 minutes. Model performance metrics (precision, recall, false positive rate) are logged for each version.

## Known Issues and Recent History

- **March 2026 — Model drift incident (INC-006)**: The false positive rate spiked significantly, causing legitimate transactions to be rejected at a rate far above normal. The issue was traced to a shift in transaction patterns that the previous model had not seen. The model was retrained with more recent data and redeployed. The decision threshold was also adjusted. Full narrative in `postmortem_INC006_frauddetector.md`.
- **Quarterly retraining gap**: This is a known architectural risk. The team has a backlog item for automated monthly retraining with a canary deployment process.
- **Operating costs**: FraudDetector runs a continuously active SageMaker endpoint and the cost has been rising as transaction volume grows. It is one of the two most expensive services (alongside PaymentGW) and has been identified in the cost optimization initiative.

## SLA Targets

FraudDetector carries a high availability target — comparable to PaymentGW — because a FraudDetector outage would either halt all payments (if PaymentGW fails closed) or allow all transactions through unscored (if PaymentGW fails open). The latency target is among the most aggressive in the stack. Full targets are in the SLA CSV.

## Runbooks

- Runbook: FraudDetector SageMaker endpoint health check
- Runbook: Emergency threshold override procedure
- Runbook: Model rollback to previous version
- Runbook: DynamoDB feature store investigation

## Contact

For incidents: **Team Data** (#data-eng in Slack, PagerDuty on-call). For model performance questions: Sarah Wells.
