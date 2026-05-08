---
title: Security Policy
status: current
owner: VP Engineering (Mark Sullivan)
last_updated: 2026-01-20
tags: [policy, security, pci-dss, encryption, access-control]
---

# Security Policy

GeekBrain operates as a payment processor and is subject to PCI-DSS Level 1 requirements.
This document describes our security standards, controls, and compliance posture.
All engineers must read and follow this policy. Questions go to the Platform team or VP Engineering.

---

## Compliance

GeekBrain is **PCI-DSS Level 1** compliant. This is the highest level of compliance,
required for processors handling a large volume of card transactions annually.

Annual audit is conducted by an external Qualified Security Assessor (QSA).
Internal quarterly self-assessments are performed by the Platform security representative.

---

## Encryption

**Data at rest:** AES-256 encryption for all datastores containing payment or personal data.
This includes PostgreSQL databases, Redshift data warehouse, S3 buckets, and DynamoDB tables.

**Data in transit:** TLS 1.3 minimum for all internal and external communications.
TLS 1.2 is disabled on all services. No plaintext connections are permitted.

**Key management:** Encryption keys are managed via AWS KMS. No service directly stores
raw encryption keys in environment variables or configuration files.

---

## API Key Policy

- API keys expire and must be rotated every **90 days**
- Keys are issued through the Platform team; no self-service key generation in production
- Compromised keys must be revoked immediately — contact Platform team on-call
- Keys must never be committed to version control or included in logs

---

## JWT and Signing Keys

JWT signing keys (used by AuthSvc) rotate every **30 days** on an automated schedule.
The rotation script performs a test sign-and-verify cycle before committing the swap.

Key age is monitored — an alert fires if any signing key exceeds 32 days without rotation,
providing an 2-day buffer before the 30-day policy is breached.

If a rotation fails, the monitoring alert fires within hours. Do not attempt manual rotation
without following the documented runbook (see AuthSvc runbook in team wiki).

---

## Network Architecture

- All services run in **private subnets** — no direct internet access
- External traffic enters via load balancers in public subnets
- Service-to-service communication stays within the VPC
- Bank API connections route through a managed NAT gateway with fixed egress IPs
- Security groups follow deny-by-default; only explicitly required ports are open
- VPC flow logs are enabled and retained for 90 days

---

## Access Control

**Principle of least privilege:** Every service, IAM role, and human user gets the minimum
permissions required to perform their job. Blanket `*` policies are prohibited.

**Quarterly access reviews:** Team leads review all IAM permissions and Slack access for
their team members. Stale permissions are revoked within 5 business days of review.

**No direct production access:** Engineers do not have SSH access to production instances.
All changes go through CI/CD pipelines or approved runbooks. Break-glass access requires
VP Engineering approval and is fully logged.

**MFA required:** All AWS console access and GitHub repository access requires MFA.

---

## Data Retention

| Data Type | Retention Period |
|-----------|-----------------|
| Transaction logs | 7 years (regulatory requirement) |
| System logs | 1 year |
| Audit logs (access, changes) | 3 years |
| Application debug logs | 30 days |

Logs are archived to S3 with Glacier transition after 90 days for cost efficiency.
Deletion policies are enforced via S3 lifecycle rules — manual deletion of audit logs
requires VP Engineering approval.

---

## Penetration Testing

Annual penetration test conducted by an external third party.
Most recent test: **December 2025**. Results are stored in the security team's confidential
wiki space and shared with the QSA during the annual PCI audit.

Findings are tracked in Jira (project: SEC) with mandatory remediation timelines by severity.

---

## Vulnerability Scanning

**Weekly automated scanning** using AWS Inspector and a third-party SCA tool for dependencies.
Critical and high-severity findings generate a Jira ticket automatically and must be
remediated within:
- Critical: 7 days
- High: 30 days
- Medium: next quarterly security review
- Low: backlog, addressed opportunistically

---

## Incident and Breach Response

Security incidents follow the same P1 escalation path as production incidents, with the
addition of the security representative being looped in immediately. Suspected data breaches
require CTO notification within 1 hour regardless of resolution status.

Refer to `incident_response_policy.md` for the general escalation chain.

---

## Developer Responsibilities

Every engineer is responsible for:
- Not committing secrets, credentials, or API keys to any repository
- Reporting suspected security issues immediately to the Platform team
- Completing annual security awareness training
- Following secure coding practices (input validation, parameterized queries, no eval on user input)
