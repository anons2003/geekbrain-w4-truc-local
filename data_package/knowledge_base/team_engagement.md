---
title: Team Engagement — Team Reference
last_updated: 2026-02-20
author: Nina Shah
department: Engineering
---

# Team Engagement

## Overview

Team Engagement owns NotificationSvc, the asynchronous messaging layer that delivers order confirmations, delivery updates, alerts, and marketing communications to merchants and their customers. The team is the smallest at GeekBrain by headcount, and the gap between team capacity and growing message volume is a known challenge the team is working to address.

## Lead

**Nina Shah** — Engineering Lead, Team Engagement

## Members

| Name | Primary Focus |
|------|--------------|
| Nina Shah | Lead, system architecture, SQS/SES configuration |
| Owen Clark | Consumer services, queue processing, DLQ management |
| Paula West | Email template management, SES, notification content |
| Quinn Adams | SMS/push integrations, SNS, merchant alerting |

## Services Owned

- **NotificationSvc** — async queue-based notification service (Python, SQS, SES, SNS)

## On-Call Rotation

- **Schedule**: Monthly rotation (given the smaller team size, on-call burden is reduced)
- **Coverage**: PagerDuty active for all hours; alerts routed by severity
- **Handoff**: First Monday of each month
- **Note**: Because P1 failures in NotificationSvc cause delayed merchant notifications (not payment failures), on-call response targets are slightly less aggressive than Team Platform's. However, sustained degradation has merchant-facing impact and is treated seriously.

## Focus Areas

### Queue-Based Message Processing
NotificationSvc is fully asynchronous — messages enter an SQS queue and are processed by consumer workers. This decouples notification delivery from the upstream services (OrderSvc being the primary producer). The team maintains dead letter queue (DLQ) configuration and ensures failed messages are retained and re-processable.

### Email Delivery
Paula West manages SES configuration, email templates, and delivery monitoring. Order confirmation emails are the highest-volume notification type and are the most visible to merchants and customers.

### SMS and Push
Quinn Adams handles SNS-based SMS delivery and push notification integrations. Merchant alert messages (unusual activity, payout events) use this channel.

### Growing Volume Challenge
As GeekBrain's transaction volume has grown, notification volume has grown proportionally. The team has been under-resourced relative to this growth. Merchants have raised concerns about slow delivery of confirmation notifications in recent months. The team is working with leadership on a capacity and staffing plan, but this remains an active concern as of this writing.

## Dependencies

- **SQS** — AWS managed queue; primary message transport
- **SES** — AWS managed email; primary email delivery
- **SNS** — AWS managed notifications; SMS and push
- **OrderSvc** (Team Commerce) — primary producer of notification events

## Escalation

For P1/P2 incidents involving NotificationSvc:
1. On-call engineer responds
2. If not resolved within 30 minutes: Nina Shah (team lead) is paged
3. Further escalation follows the standard escalation policy
4. Sustained notification delays are escalated to Merchant Success for proactive communication with affected merchants

## Team Norms

- Standup: weekdays 10:00 ICT
- DLQ contents are reviewed every Monday morning
- Any change to SES sending configuration requires Nina Shah approval (risk of deliverability impact)
- Template changes go through a staging environment and are tested with test addresses before production deployment
- Post-mortems for significant DLQ overflow events, even at P3 severity
