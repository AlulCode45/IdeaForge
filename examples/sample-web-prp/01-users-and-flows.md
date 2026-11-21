# 01. Users & Flows — DevPulse

## Personas
1. **Indie SaaS Founder (Alex)**: Wants a 2-minute setup to monitor API + landing page and share a clean public status page with customers.
2. **Ops / Backend Engineer (Maya)**: Needs reliable webhook payloads, zero false-positive Slack noise, and 90-day uptime history.

## Primary User & Alerting Flow

```mermaid
flowchart LR
    U["User Signs In (OAuth / Magic Link)"] --> M["Add Monitor (URL + Interval)"]
    M --> V["SSRF & URL Validation"]
    V --> W["Worker Polls Every 60s"]
    W --> C{"HTTP 2xx?"}
    C -- "Yes" --> OK["Log Check (UP)"]
    C -- "No (2x consecutive)" --> INC["Open Incident + Send Slack/Webhook"]
    INC --> SP["Update Public Status Page"]
```
