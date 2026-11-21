# 02. Requirements — DevPulse

## Functional Requirements (MoSCoW)

| Priority | ID | Requirement | Acceptance Criteria |
|---|---|---|---|
| **Must-Have** | FR-1 | Workspace Auth | Users sign in via GitHub/Google OAuth or email magic link; isolated by `workspace_id`. |
| **Must-Have** | FR-2 | HTTP/HTTPS Monitor CRUD | Create/pause/delete monitors (URL, method, 60s interval, timeout 5s); block private/loopback IPs. |
| **Must-Have** | FR-3 | 2-Step Failure Confirmation | Incident opens only after 2 consecutive failed checks (10s retry gap) to avoid transient blips. |
| **Must-Have** | FR-4 | Alert Channels | Dispatch JSON webhook, Slack, or Discord payload on incident open and resolve. |
| **Must-Have** | FR-5 | Public Status Page | Public URL `/s/<workspace-slug>` showing current status, 90-day daily uptime bars, and incident log. |
| **Should-Have** | FR-6 | Maintenance Windows | Suppress alerts during scheduled maintenance windows. |
| **Won't-Have (v1)** | FR-7 | Multi-Region Checks | Single-region poller for MVP; multi-region deferred to v1.2. |

## Non-Functional Requirements
- **Performance**: Status page cached via CDN/Redis (`stale-while-revalidate=30s`), p95 TTFB < 150ms.
- **Security**: Strict SSRF protection (resolve DNS, reject RFC1918/link-local/metadata IPs before outbound HTTP), HTTPS-only cookies, rate-limited public API.
- **Reliability**: Poller gracefully handles worker restarts without duplicate incident alerts.
