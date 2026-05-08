---
doc_id: KB-035
title: New Engineer Onboarding Guide
category: people-ops
tags: [onboarding, new-hire, setup, access, tools, pci-dss]
last_updated: 2026-03-01
status: active
---

# New Engineer Onboarding Guide

**Welcome to GeekBrain.**

This guide covers everything you need to get set up and productive in your first month. If anything is unclear or out of date, post in `#engineering` or ask your team lead.

---

## Day 1 Checklist

### IT and Access

- [ ] Submit an IT ticket via `it-support@geekbrain.io` for VPN access. Include your team lead's name as approver. VPN is required for Grafana and internal service access.
- [ ] Request GitHub organization invite from your team lead. You will be added to your team's repositories.
- [ ] Submit an AWS console access request via your team lead. An IAM role scoped to your team's services will be assigned. Do not use team-shared credentials — you will have a personal IAM user.
- [ ] Confirm PagerDuty account is active (IT will set this up). Enable mobile push notifications before your first on-call shift.

### Slack

Join these channels on your first day:

| Channel | Purpose |
|---------|---------|
| `#general` | Company announcements |
| `#engineering` | Engineering discussions, architecture decisions |
| `#incidents` | Active incident communication — all engineers must be here |
| `#deployments` | Deployment announcements (automated + manual) |
| `#it-help` | IT support requests |
| `#random` | Non-work chat |

Ask your team lead to add you to your team's private channel.

---

## Development Environment Setup

### Required Tools

```bash
# Install Docker Desktop (macOS/Windows)
# https://docs.docker.com/desktop/

# Install AWS CLI v2
brew install awscli

# Configure AWS CLI with your IAM credentials
aws configure

# Clone your team's service repositories
# (URLs provided by team lead after GitHub invite)
git clone git@github.com:geekbrain/{service-name}.git
```

### Local Service Mesh

Each service has a `docker-compose.yml` for local development. To run the full service mesh locally:

```bash
# From the infrastructure repo (request access from team lead)
docker-compose up -d
```

This starts all six services plus their dependencies (PostgreSQL 15, Redis, LocalStack for SQS/SES simulation).

**Note:** Local SageMaker is not supported. FraudDetector local development uses a mock scoring endpoint. For testing against real SageMaker, use the shared staging endpoint (access via team lead).

### Database

Local development uses PostgreSQL 15. Connection details are in your service's `.env.example` file. Copy to `.env` and fill in values per your service's README.

```bash
cp .env.example .env
# Edit .env with local values
```

---

## Key Contacts

| Need | Contact |
|------|---------|
| Architecture and design questions | Mark Sullivan (VP Engineering) |
| Daily work, task questions | Your team lead |
| Access and account issues | `#it-help` |
| Security and compliance questions | Your team lead → Security team |
| HR and people ops | `people@geekbrain.io` |

**Team leads:**
- Team Platform: Alex Chen
- Team Commerce: Jake Morgan
- Team Data: Ryan Blake
- Team Engagement: Nina Shah

---

## Monitoring Access

- **Grafana:** `https://grafana.internal` — requires VPN. Ask team lead to confirm your role has read access. This is your primary dashboard for service health during on-call shifts.
- **CloudWatch:** AWS Console → CloudWatch. Accessible via your IAM role. You will have read-only access to dashboards and alarms for your team's services initially.

See `monitoring_dashboard_guide.md` for a full walkthrough of key dashboards.

---

## First Week Goals

1. **Shadow on-call rotation.** Your team lead will pair you with the current on-call engineer for your first week. Observe how alerts are triaged, how incidents are communicated, and how dashboards are used.
2. **Review service architecture docs.** Read `architecture_review_feb_2026.md` for a complete picture of all six services and how they connect. Read the specific docs for your team's services.
3. **Complete security training.** Mandatory for all engineers. Takes approximately 2 hours. Link will be sent by IT on Day 1. Must be completed within your first week.
   - Covers: PCI-DSS awareness (GeekBrain is PCI-DSS Level 1 compliant), data handling policies, access control principles.

---

## First Month Goals

1. **Own a small feature end-to-end.** Your team lead will assign a well-scoped task. The goal is to go through the full cycle: design, implementation, code review, testing, and deployment.
2. **Attend an Architecture Review meeting.** Held quarterly. Ask Mark Sullivan to be added to the invite. Even if you don't present, observing the discussion helps you understand how architectural decisions are made.
3. **Complete your first on-call shift.** By the end of month 1, you should take a full on-call shift with backup coverage available from your team lead.

---

## Security and Compliance Notes

GeekBrain processes payment data and is subject to PCI-DSS Level 1 requirements. As an engineer, you are responsible for:

- Never committing secrets, credentials, or PII to version control. Git history is audited.
- Using only approved services and tools for production data access. Do not copy production data to local development environments.
- Reporting any suspected security incidents to your team lead immediately.
- Completing annual security training refreshers when notified.

Production database access requires separate approval and MFA. Contact your team lead if your role requires production data access.

---

## Useful Internal Links (VPN required)

| Resource | URL |
|----------|-----|
| Grafana dashboards | `https://grafana.internal` |
| Internal API docs | `https://docs.internal` |
| Confluence (team wikis) | `https://geekbrain.atlassian.net` |
| PagerDuty | `https://geekbrain.pagerduty.com` |

---

## Related Documents

- `team_platform.md`, `team_commerce.md`, `team_data.md`, `team_engagement.md` — Team rosters, responsibilities, and escalation paths
- `architecture_review_feb_2026.md` — Service architecture review and tech stacks
- `on_call_handbook.md` — On-call procedures for when you take your first shift
- `monitoring_dashboard_guide.md` — Dashboard guide
- `security_policy.md` — Full security and compliance policies
