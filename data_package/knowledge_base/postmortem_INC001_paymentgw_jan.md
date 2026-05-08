---
title: Postmortem — INC-001 PaymentGW P2, January 15 2026
incident_id: INC-001
service: PaymentGW
severity: P2
date: 2026-01-15
duration_minutes: 45
owner: Team Platform
tags: [postmortem, paymentgw, database, connection-pool]
---

# Postmortem: INC-001 — PaymentGW P2

**Date:** January 15, 2026
**Duration:** 45 minutes (10:15 – 11:00)
**Severity:** P2 — Single service degraded, workaround not available during incident
**Team:** Team Platform
**Facilitator:** Alex Chen

---

## Summary

PaymentGW experienced elevated latency and request queuing due to database connection pool
exhaustion under peak morning load. The pool was sized for initial deployment traffic levels
and had not been reviewed as throughput grew. Incident was detected automatically and
resolved by increasing the connection pool size.

---

## Timeline

| Time | Event |
|------|-------|
| 10:15 | PostgreSQL connection pool hits maximum (20/20 connections in use) |
| 10:18 | New incoming requests begin queuing — connection wait times increase |
| 10:22 | p99 latency spikes, CloudWatch alarm fires on elevated response time |
| 10:25 | PagerDuty pages on-call engineer Chris Park |
| 10:30 | Chris Park acknowledges, begins investigation in #incidents |
| 10:35 | Root cause identified: connection pool at 100% saturation |
| 10:40 | Alex Chen consulted, confirms plan to increase pool limit |
| 10:45 | Pool size increased from 20 to 50 connections via configuration update |
| 10:55 | Latency returns to normal range, queue drains |
| 11:00 | All clear declared, INC-001 closed |

---

## Root Cause

Database connection pool was configured at 20 connections — the initial deployment setting
from early 2025. Payment transaction volume had grown significantly since then, and during
the morning peak on January 15, concurrent database-heavy requests exceeded pool capacity.

Once the pool was exhausted, new requests had to wait for a connection to become available.
This manifested as queuing and latency spikes rather than hard failures, which is why the
incident was P2 rather than P1.

---

## Contributing Factors

- Pool size had never been reviewed since initial deployment, despite growing traffic
- No monitoring alert existed for pool utilization percentage (only for latency impact)
- The saturation point was only discovered reactively, not during capacity planning

---

## What Was Tried

1. **Check for slow queries** — reviewed pg_stat_activity, no abnormally long-running queries
   found. All connections were actively processing, not blocked.
2. **Restart application** — considered but rejected. Restart would briefly drop all connections
   and could worsen queuing.
3. **Increase pool size** — applied as configuration change, resolved the issue.

---

## Lessons Learned

- Infrastructure sizing from initial deployment should be reviewed at regular intervals
  as traffic grows, not only when an incident occurs.
- Connection pool utilization is a leading indicator of latency issues, not a lagging one.
  Monitoring should alert before the pool is fully saturated.

---

## Action Items

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Increase PostgreSQL connection pool from 20 to 50 connections | Chris Park | Done (during incident) |
| 2 | Add CloudWatch alarm at 80% pool utilization (16/20 → 40/50 threshold) | Chris Park | Done (Jan 16) |
| 3 | Schedule quarterly capacity review for all PaymentGW resource limits | Alex Chen | Scheduled (next: April 2026) |

---

## Follow-Up

Quarterly capacity review now on the Team Platform calendar. Metrics reviewed:
connection pool, CPU, memory, and request queue depth for PaymentGW each quarter.
