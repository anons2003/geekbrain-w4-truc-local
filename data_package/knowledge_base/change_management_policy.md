---
title: Change Management Policy
status: current
owner: VP Engineering (Mark Sullivan)
last_updated: 2026-01-12
tags: [policy, change-management, infra, cab, jira]
---

# Change Management Policy

This document governs how infrastructure and configuration changes are proposed, reviewed,
and executed at GeekBrain. It applies to all production environment changes regardless of
service or team.

---

## Scope

This policy covers:
- AWS infrastructure changes (instance types, security groups, networking, IAM)
- Database configuration changes (connection limits, storage, parameter groups)
- Third-party service configuration (bank API credentials, SQS queues, SES settings)
- Kubernetes/ECS resource definitions
- Environment variables and secrets rotation (beyond automated rotations)

Application code deployments are governed by `deployment_policy.md`, not this policy.

---

## Change Request (CR) Process

All infrastructure changes must have a Change Request filed in **Jira, project: INFRA**
before work begins. No exceptions.

**Required CR fields:**
- Summary and description of the change
- Services and environments affected
- Risk assessment (low / medium / high)
- Rollback plan
- Scheduled window (must align with `deployment_policy.md` windows)
- Requester and implementing engineer (may be the same person)

---

## CR Types

### Standard Change

Pre-approved change patterns with known, low-risk procedures. No CAB review required.

Examples:
- Horizontal scaling (adding/removing instances within approved ranges)
- Auto-scaling policy parameter adjustments within defined bounds
- Certificate renewals via ACM (automated)
- Non-schema database configuration adjustments (e.g., connection pool size within limits)

Standard changes still require a Jira CR for audit trail. Implementation can begin
immediately after CR is filed.

### Normal Change

Requires **Change Advisory Board (CAB) review** within 48 hours of filing.
CAB reviews for risk, cross-service impact, and rollback viability.

Examples:
- New AWS services being introduced
- Security group rule changes
- Database instance type changes
- IAM role modifications
- New third-party integrations

Implementation may not begin until CAB approval is recorded in the Jira CR.

### Emergency Change

For P1 incident response only. Change is implemented immediately and reviewed retrospectively.

**Requirements:**
- P1 incident must be declared and active (per `incident_response_policy.md`)
- VP Engineering Mark Sullivan verbally approves during the incident
- CR is filed in Jira within 2 hours of the change (retrospective)
- CAB retrospective review at next Tuesday meeting

Emergency changes that are not tied to a declared P1 incident are not permitted.
If the situation doesn't qualify as P1, file a Normal Change and request expedited review.

---

## Change Advisory Board (CAB)

**Meeting cadence:** Tuesdays at 10:00 Vietnam time.

**Members:**
- VP Engineering Mark Sullivan (chair)
- Team Platform lead: Alex Chen
- Team Commerce lead: Jake Morgan
- Team Data lead: Ryan Blake
- Team Engagement lead: Nina Shah
- Security representative (rotating from Platform team)

**Decision:** Majority approval required. VP Engineering has final say in disputed cases.

CRs submitted by Monday 18:00 are reviewed at Tuesday's meeting. CRs submitted after that
window are reviewed the following Tuesday unless an expedited review is requested and approved.

---

## Database Schema Changes

Schema changes have an additional review step beyond the standard Normal Change process:

1. DBA review required before CAB submission (contact Ryan Blake)
2. Migration must be backward-compatible with the current deployed application version
3. Schema migration runs in a separate deployment step before the application deployment
4. Explicit rollback SQL must be included in the CR

This additional rigor exists because schema rollbacks are often more complex and risky
than application code rollbacks.

---

## Direct Production Access

**No direct production access.** All changes go through:
- CI/CD pipelines (for application and infrastructure-as-code changes)
- Approved runbooks executed by on-call engineers during incidents

Break-glass access (emergency SSH/console) requires VP Engineering approval and is
fully logged via AWS CloudTrail and session manager. Logs are reviewed weekly.

---

## Audit Trail

All CRs remain in Jira permanently. The Jira INFRA project is the system of record for
all infrastructure changes. Do not close or delete CRs — mark them as complete with
implementation notes.

---

## Questions

Process questions → #infra-changes Slack channel or your team lead.
CAB scheduling → VP Engineering Mark Sullivan.
