---
title: ReportingSvc — Service Reference
last_updated: 2026-04-05
author: Tom Hayes
department: Engineering / Team Data
---

# ReportingSvc — Service Reference

## Purpose

ReportingSvc is GeekBrain's analytics and business intelligence service. It generates daily automated reports, weekly business summaries, and serves ad-hoc query requests from internal teams and merchant dashboards. It reads from the read replicas of all production databases — it has no write access to production data.

## Owner

**Team Data** — Lead: Ryan Blake. Tom Hayes and Victor Stone are the primary engineers.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python |
| Data warehouse | AWS Redshift |
| Object storage | AWS S3 |
| Orchestration | Scheduled ETL jobs (nightly) |

## Architecture

ReportingSvc operates in two modes:

### Batch Mode (primary)
Nightly ETL pipelines extract data from all service databases (via read replicas), transform it, and load it into Redshift. Automated reports (daily and weekly) are generated from Redshift and delivered to configured recipients or stored in S3 for access.

### On-Demand Mode
Ad-hoc queries are served via an internal API. These queries run against the Redshift warehouse. Query complexity and result size vary widely; complex queries can take several minutes.

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily transaction summary | 02:00 ICT | Aggregated transaction metrics per merchant |
| Weekly business summary | Sunday 03:00 ICT | Company-wide KPIs for leadership |
| Monthly financial reconciliation | 1st of month, 04:00 ICT | Cross-service financial consistency check |
| Data freshness validation | 06:00 ICT | Alerts if ETL has not completed by this time |

## Known Issues and Current State

### Growing Dataset Performance
The datasets that ReportingSvc queries have grown substantially as GeekBrain's transaction volume has scaled. Some ETL jobs that previously completed comfortably within their scheduled window are now approaching timeout limits. A P2 incident in April 2026 involved an ETL job exceeding the 30-minute query timeout. Redshift query optimization (sort keys, pagination for large result sets) has been applied, but this will remain an area of ongoing work.

### Query Time Trends
Both nightly ETL duration and ad-hoc query response times have been trending upward. Victor Stone is leading a backlog of Redshift optimization and data partitioning work to address this.

## SLA Targets

ReportingSvc has the most lenient SLA in the stack. It is not in the critical path of payment processing or order creation. Latency targets allow for queries that take several seconds to a few minutes. Availability target is the lowest of all services. Full targets are in the SLA CSV.

## Data Sources

ReportingSvc reads from read replicas of:
- PaymentGW PostgreSQL
- OrderSvc PostgreSQL
- AuthSvc (aggregated auth event logs, not session data)

It does not read from FraudDetector's DynamoDB or NotificationSvc's SQS queue directly; those data sources are fed into Redshift via separate ETL pipelines.

## Runbooks

- Runbook: ETL job manual re-run
- Runbook: Redshift query timeout investigation
- Runbook: S3 report delivery failure
- Runbook: ReportingSvc on-demand API troubleshooting

## Contact

For incidents or questions: **Team Data** (#data-eng in Slack). For business report content questions: Wendy Cruz (BI) or Ryan Blake.
