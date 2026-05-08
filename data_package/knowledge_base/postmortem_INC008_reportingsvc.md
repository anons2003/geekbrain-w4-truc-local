---
title: Postmortem — INC-008 ReportingSvc P2, April 2 2026
incident_id: INC-008
service: ReportingSvc
severity: P2
date: 2026-04-02
duration_minutes: 120
owner: Team Data
tags: [postmortem, reportingsvc, redshift, etl, query-performance]
---

# Postmortem: INC-008 — ReportingSvc P2

**Date:** April 2, 2026
**Duration:** 2 hours (05:30 – 08:00)
**Severity:** P2 — Daily reporting pipeline failed; business dashboards unavailable until mid-morning
**Team:** Team Data
**Facilitator:** Ryan Blake
**Detected by:** Automated pipeline timeout alarm

---

## Summary

The daily ETL pipeline for ReportingSvc timed out at its 30-minute limit due to a full table
scan on the `cost_items` table in Redshift. The dataset had grown approximately 40% during Q1
without any corresponding update to the query strategy — no sort keys were configured for
the aggregation columns used by the query. Tom Hayes diagnosed the issue, added the appropriate
sort keys, and optimized the query with pagination. The pipeline re-ran successfully in 12 minutes.

---

## Timeline

| Time | Event |
|------|-------|
| 05:00 | Daily ETL pipeline starts as scheduled |
| 05:30 | Pipeline hits the 30-minute execution timeout, job fails |
| 05:30 | CloudWatch alarm fires on pipeline failure |
| 06:00 | PagerDuty alert reaches Tom Hayes (on-call for Team Data) |
| 06:00 | Tom Hayes acknowledges, opens #incidents thread |
| 06:15 | Tom Hayes reviews Redshift query execution plan |
| 06:15 | Query plan shows full table scan on `cost_items` — no sort keys used for aggregation |
| 06:30 | Confirms dataset has grown significantly in Q1 — full scan now too slow within timeout |
| 06:45 | Ryan Blake consulted via Slack |
| 07:00 | Root cause confirmed: missing sort keys on aggregation columns |
| 07:15 | Tom Hayes implements fix: VACUUM + ANALYZE, adds sort keys to `cost_items` |
| 07:30 | Refactors query to add pagination for large result sets |
| 07:30 | Re-runs pipeline in staging environment — completes in 8 minutes |
| 07:45 | Fix deployed to production Redshift |
| 08:00 | Pipeline re-run initiated and completes successfully in 12 minutes |
| 08:00 | INC-008 closed; dashboards available |

---

## Root Cause

The daily aggregation query on `cost_items` was written when the dataset was relatively small.
At that scale, a full table scan was fast enough to complete well within the 30-minute timeout.

During Q1 2026, the dataset grew approximately 40% due to increased transaction volume and the
expansion of cost attribution data collected per transaction. The query was never updated —
no sort keys were defined for the columns used in the GROUP BY and ORDER BY clauses, meaning
Redshift could not use its columnar storage to optimize the scan. The result was a full table
scan on a table that had outgrown it.

---

## Contributing Factors

1. **No sort key configuration for aggregation columns**: The `cost_items` table was created
   without sort keys appropriate for its primary query patterns. This was acceptable at small
   scale but became a bottleneck as data grew.
2. **No query execution time monitoring**: There were no intermediate alerts for queries
   running longer than expected — only the hard timeout at 30 minutes. A warning at 15 minutes
   would have allowed intervention before complete failure.
3. **Dataset growth not tracked against query performance**: Q1 saw significant data growth
   but there was no process to re-evaluate query strategies as data volume changed.
4. **No pagination on large result sets**: The query fetched all rows in a single operation.
   At larger data volumes, iterative pagination is more resilient.

---

## Impact

- Daily reporting pipeline failed to complete — business stakeholders did not have access
  to the morning dashboard by the expected 06:00 availability window
- Dashboards were unavailable until approximately 08:30 (including re-run time)
- No data loss or data corruption occurred — only a delay in report availability

---

## What Was Tried

1. **Increase timeout** — considered but rejected. Increasing the timeout would mask the
   underlying performance issue without fixing it. Root cause must be addressed.
2. **Kill long-running query and retry** — done during investigation to free up Redshift
   resources for analysis.
3. **Add sort keys and optimize query** — applied, resolved the issue.

---

## Lessons Learned

- Redshift query performance degrades non-linearly as data grows without appropriate sort
  keys. A query that works at small scale can fail badly as data volume increases.
- Query execution time monitoring should alert before hard timeouts. A pipeline that runs
  in 5 minutes suddenly taking 25 minutes is a signal, not just the 30-minute hard failure.
- Pagination is a good practice for all large result set queries — it makes queries more
  resilient and allows partial progress even if interrupted.
- Database performance should be reviewed periodically as a regular maintenance activity,
  not only reactively during incidents.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Add sort keys to frequently aggregated columns on `cost_items` and similar tables | Tom Hayes | Apr 2 | Done (during incident) |
| 2 | Implement pagination for all large result set queries in the ETL pipeline | Tom Hayes | Apr 10 | Done |
| 3 | Add CloudWatch metric for ETL job execution time; alert at 20 minutes (before 30-min timeout) | Victor Stone | Apr 10 | Done |
| 4 | Schedule quarterly Redshift performance review — sort key and distribution key audit | Ryan Blake | Quarterly | Scheduled (next: July 2026) |
| 5 | Document query design standards for Redshift in team wiki | Tom Hayes | Apr 20 | In progress |

---

## Follow-Up

Quarterly Redshift performance review is now on Team Data's maintenance calendar,
alongside the quarterly model retraining added after INC-006. The April session will
audit all major tables for missing or suboptimal sort keys.
