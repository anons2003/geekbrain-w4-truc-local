---
title: Postmortem — INC-005 PaymentGW P1, March 5 2026
incident_id: INC-005
service: PaymentGW
severity: P1
date: 2026-03-05
duration_minutes: 180
owner: Team Platform
tags: [postmortem, paymentgw, circuit-breaker, bank-api, p1]
---

# Postmortem: INC-005 — PaymentGW P1

**Date:** March 5, 2026
**Duration:** 3 hours (14:23 – 17:23)
**Severity:** P1 — Revenue-impacting, approximately 40% of payment transaction volume affected
**Team:** Team Platform
**Facilitator:** Alex Chen
**Attendees:** Alex Chen, Ben Torres, Chris Park, David Kim, VP Mark Sullivan (joined at 15:15)

---

## Summary

This was the most significant incident in Q1 2026. An upstream VCB bank API timeout cascade
caused PaymentGW's circuit breaker to open and stop routing traffic to VCB. The circuit
breaker should have auto-reset after a 30-second cooldown — but a misconfigured health check
caused the circuit breaker to remain stuck in the OPEN state indefinitely. Approximately 40%
of payment transactions failed for 3 hours while the team diagnosed the health check issue
and deployed a hotfix. Catch-up processing in the following weeks generated significant
additional operational load due to retry storms and compensatory batch jobs.

---

## Timeline

| Time | Event |
|------|-------|
| 14:23 | VCB bank API begins returning HTTP 504 timeout errors |
| 14:25 | PaymentGW circuit breaker starts accumulating trip counts |
| 14:31 | Circuit breaker threshold reached, transitions to OPEN — stops routing to VCB |
| 14:35 | Circuit breaker should auto-reset after 30-second cooldown |
| 14:35 | Health check queries VCB API, receives HTTP 503 — misinterpreted as HTTP 200 by check |
| 14:35 | Circuit breaker remains OPEN (reset condition not satisfied) |
| 14:45 | All VCB-routed payments now failing — approximately 40% of total transaction volume |
| 14:50 | Automated CloudWatch alarm fires on error rate spike |
| 14:50 | PagerDuty pages on-call engineer Chris Park |
| 15:00 | Chris Park confirms error spike, opens #incidents as P2 initially |
| 15:10 | Chris Park escalates — scope is larger than P2. Upgrades to P1, pages Alex Chen |
| 15:15 | Alex Chen assesses situation. Confirms P1. Notifies VP Mark Sullivan per escalation policy |
| 15:20 | Status page updated. VP Mark Sullivan joins the bridge |
| 15:30 | Team attempts manual circuit breaker reset via admin endpoint |
| 15:30 | Manual reset fails — reset logic internally calls the same health check endpoint |
| 15:45 | Team begins reviewing health check configuration source code |
| 16:00 | Root cause identified: health check parses VCB response incorrectly |
| 16:10 | Hotfix written: bypass health check for manual reset, force circuit breaker to HALF_OPEN |
| 16:15 | VP Mark Sullivan approves emergency deployment (deployment freeze overridden per policy) |
| 16:15 | Hotfix deployed via emergency change procedure |
| 16:20 | Circuit breaker enters HALF_OPEN state, sends test traffic to VCB |
| 16:25 | VCB responds normally — it had recovered during the 2-hour diagnosis period |
| 16:30 | Circuit breaker transitions to CLOSED — normal routing resumes |
| 16:45 | Queued transactions begin processing; error rate drops to normal |
| 17:23 | Queue fully drained. Incident closed |

---

## Root Cause

The PaymentGW circuit breaker health check endpoint was misconfigured. It was designed
to check whether the VCB bank API was available before allowing the circuit breaker to reset.
However, the check's HTTP response parsing had a bug: it treated any response from VCB as
success, including HTTP 503 Service Unavailable.

When VCB returned 503 (a legitimate "I am down" response), the health check returned
`healthy = true`. This caused the circuit breaker's reset condition to evaluate as satisfied
but then immediately re-open on the next test request, keeping it stuck in a loop that
never resolved.

The manual override admin endpoint also called the same health check function internally,
which is why the manual reset at 15:30 also failed.

---

## Contributing Factors

1. **No fallback routing**: GeekBrain had no secondary bank API configured for VCB-routed
   transactions. When VCB went down, there was no alternative path.
2. **Health check not independently tested**: The circuit breaker health check function
   had never been tested against non-200 VCB responses in staging.
3. **Manual override depending on the same failing subsystem**: The admin reset endpoint
   reused the health check — coupling the manual escape hatch to the broken component.
4. **Initial P1 declaration delayed**: Incident was initially logged as P2 at 15:00, delaying
   the escalation to Mark Sullivan by 15 minutes. Faster P1 classification criteria would help.

---

## Impact

- Approximately 40% of payment transaction volume failed during the 3-hour outage
- VCB is the primary routing path for a significant portion of GeekBrain's bank transfer volume
- Significant catch-up processing costs in the weeks following the incident due to:
  - Retry storms from merchants retrying failed payments
  - Compensatory batch processing to reconcile queued transactions
- Merchant confidence impact — several merchants reported delayed payments to their end customers

---

## What Was Tried

1. **Wait for auto-reset** — circuit breaker did not reset as expected (root cause)
2. **Manual reset via admin endpoint** — failed, same health check dependency
3. **VCB direct connectivity test** — confirmed VCB itself recovered around 16:20
4. **Hotfix: decouple manual reset from health check** — succeeded

---

## Lessons Learned

- Circuit breakers require their own independent health monitoring, separate from the
  upstream service they protect. The health check cannot be the same system the circuit
  breaker is trying to protect.
- Manual override mechanisms must not depend on the same failing components. Break-glass
  overrides need an independent path.
- Fallback routing should have been in place before this incident. Relying on a single
  upstream bank API without a secondary is an unacceptable single point of failure for
  revenue-critical flows.
- Incident severity should be escalated when scope is unclear — err on the side of P1.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Fix health check: correctly parse all VCB HTTP response codes | David Kim | Mar 10 | Done |
| 2 | Implement fallback routing to Techcombank when VCB circuit breaker is open | Alex Chen | Apr 15 | In progress |
| 3 | Add dedicated circuit breaker health check ping (independent of bank API health) | Ben Torres | Mar 15 | Done |
| 4 | Manual reset endpoint must not call health check — use direct state write | David Kim | Mar 10 | Done |
| 5 | Circuit breaker configuration review meeting scheduled | Alex Chen | Apr 15 | Scheduled |
| 6 | Update P1 classification criteria: any error rate >10% should auto-escalate | Alex Chen | Mar 20 | Done |

---

## Circuit Breaker Review

Scheduled April 15, 2026. All Team Platform engineers attend. Agenda:
- Review all circuit breaker configurations across PaymentGW
- Verify health check implementations for each
- Confirm manual override paths are independent of health checks
- Review fallback routing implementation progress
