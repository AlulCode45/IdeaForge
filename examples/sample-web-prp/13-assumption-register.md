# Assumption Register - DevPulse (Web PRP)

Last reviewed: 2026-11-22

| ID | Assumption | Confidence (H/M/L) | Impact if wrong (H/M/L) | Test method (cheapest) | Kill trigger | Source / grade | Owner | Date reviewed | Status (open/confirmed/refuted) |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Single 512MB Go worker handles 1,000 monitors at 60s interval | M | M | Benchmark with 1,000 local mock endpoints | CPU > 80% or p95 drift > 5s | Engineering / B | Backend | 2026-11-22 | open |
| A2 | 2-consecutive-failure check cuts false positives < 1% | M | H | Replay 7-day sample HTTP logs | False positives > 2% | Engineering / B | Ops | 2026-11-22 | open |
| A3 | Managed infra stays <= USD 25/mo for MVP (< 1,000 monitors) | H | L | Price check Fly.io / Railway + Neon | Cost > USD 60/mo at 1k monitors | Vendor pricing / A | Infra | 2026-11-22 | open |

## Top risky assumptions (Low/Medium confidence x High impact)
1. `A2` — 2-check confirmation eliminates transient network noise without delaying real incident alerts beyond 15 seconds.
