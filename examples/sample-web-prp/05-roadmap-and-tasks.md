# 05. Roadmap & Task Breakdown — DevPulse

## Milestones (3-Week MVP)

| Phase | Target | Key Deliverables | Est. Effort |
|---|---|---|---|
| **Phase 1: Core Poller & DB** | Week 1 | Postgres schema, SSRF-safe Go poller, 2-check failure confirmation | 6–8 days |
| **Phase 2: Web Dashboard & Status Page** | Week 2 | Next.js auth, Monitor CRUD, cached `/s/<slug>` public status page | 7–9 days |
| **Phase 3: Alerts, QA & Beta** | Week 3 | Slack/Discord/Webhook dispatcher, load test, security audit, beta deploy | 5–6 days |

## First 30-Minute Action
- [ ] Initialize repo with `apps/web` (Next.js) and `services/poller` (Go), plus `docker-compose.yml` for local Postgres + Redis.
