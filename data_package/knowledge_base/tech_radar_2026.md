---
doc_id: KB-036
title: GeekBrain Tech Radar — 2026
category: architecture
tags: [tech-radar, 2026, technology, stack, evaluation, aws]
last_updated: 2026-04-01
status: active
owner: Mark Sullivan
---

# GeekBrain Tech Radar — 2026

**Purpose:** Quarterly snapshot of technology decisions across GeekBrain's engineering platform. Documents what we are actively using, what we are evaluating, and what we have consciously chosen not to adopt.

**Owner:** Mark Sullivan (VP Engineering)  
**Updated:** April 2026  
**Next review:** July 2026

---

## How to Read This Radar

| Quadrant | Meaning |
|----------|---------|
| **ADOPT** | In active production use. Proven in our environment. New work should use these. |
| **TRIAL** | In limited production or controlled evaluation. Gather experience before committing fully. |
| **ASSESS** | Researching. Not in production. May be worth trialing in the next 1–2 quarters. |
| **HOLD** | Consciously not adopting. Either not suitable for our scale, complexity level, or strategy. |

---

## ADOPT — Actively Using in Production

### Languages and Runtimes

| Technology | Service(s) | Notes |
|-----------|-----------|-------|
| **Node.js** | PaymentGW | Express-based HTTP server. Well-suited for high-throughput I/O. |
| **Java / Spring Boot** | OrderSvc | Mature framework for complex business logic. Team Commerce is Java-native. |
| **Go** | AuthSvc | Excellent performance-per-cost for high-QPS, low-latency services. |
| **Python** | FraudDetector, ReportingSvc, NotificationSvc | Dominant for data and ML workloads. Used with FastAPI (FraudDetector) and batch scripts (ReportingSvc). |

### Databases and Storage

| Technology | Service(s) | Notes |
|-----------|-----------|-------|
| **PostgreSQL 15** | PaymentGW, OrderSvc | Primary OLTP database. Reliable, battle-tested. |
| **Amazon DynamoDB** | FraudDetector | Feature store for ML inputs. High-throughput, low-latency key-value access. |
| **Amazon Redis (ElastiCache)** | AuthSvc | Session cache and JWT validation caching. |
| **Amazon S3** | ReportingSvc, general | Object storage for reports, ML training data, artifacts. |
| **Amazon Redshift** | ReportingSvc | Managed data warehouse for analytics and BI reporting. |

### Messaging and Async

| Technology | Service(s) | Notes |
|-----------|-----------|-------|
| **Amazon SQS** | NotificationSvc | Message queue for async notification delivery. |
| **Amazon SES** | NotificationSvc | Managed email delivery. |

### ML and AI

| Technology | Service(s) | Notes |
|-----------|-----------|-------|
| **Amazon SageMaker** | FraudDetector | Managed ML training and inference. Fully managed endpoint removes infra overhead. |

### Infrastructure and Delivery

| Technology | Notes |
|-----------|-------|
| **Docker** | All services containerized. Standard for local dev and CI. |
| **GitHub Actions** | CI/CD pipeline for all services. Build, test, and deploy workflows. |
| **AWS ECS (Fargate)** | Container orchestration for production workloads. Fargate removes EC2 management burden. |
| **AWS Application Load Balancer** | HTTP traffic routing for external-facing services. |
| **AWS CloudWatch** | Primary metrics, alarms, and log aggregation. |
| **Grafana** | Dashboards and visualization layer on top of CloudWatch metrics. |
| **PagerDuty** | On-call alerting and escalation routing. |

---

## TRIAL — In Evaluation

### Amazon OpenSearch Serverless

**Use case under evaluation:** Advanced full-text search for merchant transaction history and audit log querying. Redshift is adequate but slow for ad-hoc text search.  
**Status:** Proof-of-concept in progress by Team Data. Evaluating query performance and cost-per-query compared to Redshift.

### Amazon Bedrock

**Use case under evaluation:** AI-powered features — specifically, natural-language merchant support (automating responses to common questions using LLM), and anomaly explanation (providing human-readable explanations for fraud flag decisions).  
**Status:** James Wright has approved a 4-week trial. Team Data is leading with input from Team Engagement. No production deployment yet.

### AWS Step Functions

**Use case under evaluation:** Orchestrating multi-step workflows — specifically the FraudDetector model retraining pipeline (which is currently a series of Python scripts run manually). Step Functions would provide visibility, retry logic, and error handling for each step automatically.  
**Status:** Sarah Wells (Team Data) is prototyping. Decision expected by July 2026.

### AWS Graviton Instances

**Use case under evaluation:** Cost reduction for compute-heavy workloads. Graviton3 instances (ARM-based) offer better price-performance than equivalent x86 instance types for many workloads.  
**Status:** Team Data is benchmarking ReportingSvc Python batch jobs on Graviton. Go services (AuthSvc) are natural candidates due to excellent ARM compile support. Results expected by May 2026.

---

## ASSESS — Researching, Not Yet in Trial

### Apache Kafka

**Why we're looking at it:** SQS is adequate for current NotificationSvc message volumes, but Kafka's log-based model is better suited for high-volume event streaming if we expand to real-time analytics pipelines. The ReportingSvc ETL pipeline could benefit from a streaming approach rather than nightly batch jobs.  
**Why we're not trialing yet:** Kafka requires dedicated operational expertise and infrastructure management. Not appropriate at our current team size without a dedicated data platform engineer.  
**Revisit:** Q4 2026 if streaming use cases grow.

### Aurora Serverless v2

**Why we're looking at it:** OrderSvc and PaymentGW traffic has predictable daily peaks and quieter overnight periods. Aurora Serverless v2's auto-scaling compute could reduce database costs during off-peak hours while handling peak loads without over-provisioning.  
**Why we're not trialing yet:** PostgreSQL compatibility is well-documented, but migration risk is non-trivial. Planning to assess in Q3 2026 alongside Reserved Instance decisions.

### Amazon Q Developer

**Why we're looking at it:** Developer productivity tooling — code completion, test generation, documentation assistance.  
**Why we're not trialing yet:** Security review is required before introducing any AI code assistance tool into the development workflow for a PCI-DSS compliant environment. Compliance team review in progress.

---

## HOLD — Consciously Not Adopting

### Kubernetes

**Decision:** Do not adopt at current team size.

**Rationale:** ECS Fargate meets our container orchestration needs without the operational overhead of Kubernetes. The engineering investment required to operate Kubernetes (cluster management, upgrades, networking model, RBAC) is not justified for a team of ~35 engineers. AWS manages the control plane complexity in ECS. This decision will be revisited if we reach significantly higher engineering headcount.

### Self-Hosted ML Infrastructure

**Decision:** Stay on SageMaker managed endpoints.

**Rationale:** Operating GPU infrastructure, CUDA dependencies, and ML serving frameworks (TorchServe, Triton) in-house requires dedicated MLOps expertise that Team Data does not currently have. SageMaker managed endpoints provide sufficient performance and reliability for FraudDetector's requirements. The cost premium for managed infrastructure is justified by operational simplicity and reliability.

### MongoDB

**Decision:** Not adopting. Standardized on PostgreSQL + DynamoDB.

**Rationale:** We have no use case that requires MongoDB's document model that cannot be served by PostgreSQL JSONB columns or DynamoDB. Adding a third database technology increases operational surface area, tooling fragmentation, and knowledge requirements for new hires. Standardization on two well-understood databases is preferred.

---

## Upcoming Radar Changes

The following items are expected to move quadrants at the July 2026 review:

- Graviton instances: TRIAL → ADOPT (if benchmark results are positive)
- Step Functions: TRIAL → ADOPT or HOLD (decision by July)
- Aurora Serverless v2: ASSESS → TRIAL (planned for Q3 evaluation)
