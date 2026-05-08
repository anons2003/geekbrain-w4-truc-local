---
title: Postmortem — INC-004 AuthSvc P2, February 22 2026
incident_id: INC-004
service: AuthSvc
severity: P2
date: 2026-02-22
duration_minutes: 60
owner: Team Platform
tags: [postmortem, authsvc, jwt, key-rotation, automation]
---

# Postmortem: INC-004 — AuthSvc P2

**Date:** February 22, 2026
**Duration:** 60 minutes (06:30 – 07:30)
**Severity:** P2 — JWT validation failures in downstream services, single service degraded
**Team:** Team Platform
**Facilitator:** Alex Chen

---

## Summary

The automated JWT signing key rotation script ran at 02:00 as scheduled but failed silently —
it returned exit code 0 despite an internal error, meaning the rotation did not complete.
AuthSvc continued serving tokens signed with the old key, but the key metadata indicated
rotation had occurred. Downstream services began failing JWT validation when they received
tokens they could not verify. The issue was not detected until Ben Torres reviewed morning logs
at 06:30 — a four-and-a-half-hour gap between failure and detection.

---

## Timeline

| Time | Event |
|------|-------|
| 02:00 | Automated key rotation script executes on schedule |
| 02:01 | Rotation script encounters internal error during key write |
| 02:01 | Script exits with code 0 (success) despite the error — error was swallowed |
| 02:01 | No alert fires; rotation appears successful in monitoring |
| 06:30 | Ben Torres begins morning routine, reviews downstream service logs |
| 06:30 | Notices repeated JWT validation failure errors in PaymentGW and OrderSvc logs |
| 06:35 | Ben Torres escalates to Alex Chen via Slack |
| 06:45 | Alex Chen begins investigation, opens #incidents thread |
| 07:00 | Root cause identified: rotation script failure, signing key in inconsistent state |
| 07:05 | Decision: perform manual rotation following the documented runbook |
| 07:15 | Manual rotation executed successfully — sign-and-verify cycle confirms new key is valid |
| 07:20 | AuthSvc reloads new signing key |
| 07:30 | Downstream services re-validate successfully, all JWT errors clear |
| 07:30 | INC-004 closed |

---

## Root Cause

The JWT signing key rotation script had a defect in its error handling. When the key write
operation failed (due to a transient KMS API error at 02:01), the exception was caught by
a broad try/except block that logged the error internally but returned control flow normally —
resulting in exit code 0.

Because the script reported success, no alert fired and the incident went undetected for
over four hours. The actual state was that the old signing key remained active but the
rotation metadata claimed a new rotation had occurred.

---

## Contributing Factors

- No pre-rotation validation: the script did not perform a test sign-and-verify cycle
  before committing the key swap, which would have caught the failure immediately.
- No key age monitoring: there was no alert configured to detect if a signing key was
  approaching or exceeding the 30-day rotation policy threshold.
- Silent detection gap: the incident only surfaced because Ben Torres noticed error messages
  during a routine log review, not because of automated alerting.

---

## What Was Tried

During the investigation:
1. Checked AuthSvc application logs — confirmed service was running but using stale key
2. Reviewed KMS audit logs — identified the failed write at 02:01
3. Attempted automatic re-run of rotation script — rejected, root cause not yet fixed
4. Executed manual rotation following the runbook — succeeded

---

## Lessons Learned

- Exit code is not a sufficient health signal for critical automation scripts. Scripts must
  validate their own success with end-to-end verification before reporting completion.
- Silent failures in security-critical automation are especially dangerous — the impact is
  discovered much later, under time pressure.
- Key age monitoring provides a backstop: even if rotation silently fails, an age-based
  alert would catch it within hours, not during a morning log review.

---

## Action Items

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Rewrite rotation script error handling — exceptions must propagate, not be swallowed | Ben Torres | Done (Feb 23) |
| 2 | Add pre-rotation validation: test sign + verify cycle before swapping key | Ben Torres | Done (Feb 23) |
| 3 | Add CloudWatch alarm: alert if signing key age exceeds 32 days | Ben Torres | Done (Feb 24) |
| 4 | Update rotation script to emit structured logs to CloudWatch on success and failure | Ben Torres | Done (Feb 24) |
| 5 | Review other critical automation scripts for similar silent-failure patterns | Alex Chen | In progress |

---

## Follow-Up

The rotation script now runs an end-to-end sign/verify cycle before committing any key swap.
If the cycle fails, the script exits non-zero and CloudWatch triggers an alert. Key age
monitoring provides an independent backstop for any future rotation failures.
