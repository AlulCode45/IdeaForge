# 00. Overview — DevPulse (Uptime & Status Page Web App)

Date: 2026-11-22 | Version: v1.0 | Track: tech | Decision status: Go

**Recommendation**: Build the **DevPulse MVP** in 3 weeks using Next.js, PostgreSQL, and a lightweight Go HTTP poller. Estimated upfront build effort is 18–23 man-days (including 25% QA/integration buffer) with fixed cloud infrastructure starting at ~USD 25/month.

<!-- kpi-grid -->
Readiness Score | 4.15 / 5.0 | Go (Tech Track) | good
MVP Effort | 18–23 days | Includes 25% buffer | good
Base Infra Cost | ~USD 25/mo | Up to 1,000 monitors | good
Top Tech Risk | SSRF Attack | Mitigated via egress allowlist | warn
<!-- /kpi-grid -->

## Goals
1. Let teams monitor up to 20 HTTP/HTTPS endpoints per workspace at 60-second intervals [Assumption].
2. Deliver incident alerts via Webhook, Slack, or Discord within 15 seconds of a confirmed 2-check failure [Estimate].
3. Serve a fast, cacheable public status page (`status.devpulse.app/<slug>`) with < 150ms TTFB [Estimate].

## Non-Goals (MVP)
- Multi-region synthetic browser checks (Playwright) — deferred to v1.2.
- On-call SMS/voice escalation rotation — use Webhook/Slack first.
- Custom white-label CNAME SSL automation — use hosted subdomain slug in MVP.

## Success Metrics
- Alert false-positive rate < 1% (enforced by 2-consecutive-failure confirmation).
- Public status page p95 response time < 150ms under 500 req/s spike.
