# Go/No-Go Scorecard - DevPulse (Tech Readiness)

Date: 2026-11-22

## Weighted Evaluation

| Criterion | Weight | Score (1-5) | Weighted | Justification (link) |
|---|---|---|---|---|
| Market demand | 20 | 4 | 0.80 | Consistent developer need for simple, low-noise status pages ([00](00-overview.md)) |
| Evidence quality | 15 | 4 | 0.60 | Clear technical benchmarks & vendor infra pricing ([13](13-assumption-register.md)) |
| Unit economics | 20 | 4 | 0.80 | ~USD 25/mo fixed infra, ~USD 0.02/monitor variable cost ([03](03-architecture.md)) |
| Feasibility | 15 | 5 | 0.75 | Well-understood stack; 18–23 man-day MVP with 25% buffer ([05](05-roadmap-and-tasks.md)) |
| Competitive edge | 10 | 3 | 0.30 | Differentiated by 2-step alert noise reduction & fast UX ([02](02-requirements.md)) |
| Risk and compliance | 10 | 4 | 0.40 | SSRF egress control & log partitioning designed upfront ([06](06-risks-and-mitigation.md)) |
| Founder fit | 10 | 5 | 0.50 | Core Next.js + Go stack matches team skillset ([03](03-architecture.md)) |
| **Total** | 100 | | **4.15/5.0** | |

## Verdict
Go (>= 4.0)

## Sensitivity Check (Weight Shift +/- 10 pts)
- Shifting +10% weight to `Competitive edge` (20%) and -10% from `Feasibility` (5%) yields `3.95/5.0` (Conditional Go — validate positioning with 5 beta devs).

## Conditions / What would change this verdict
- SSRF DNS-level IP validation (`TR-1`) must pass integration tests before opening public signups.
- See database choice in [ADR-001](decisions/ADR-001-postgres-vs-sqlite.md).

## Red-team summary
- Main technical risk is SSRF abuse from malicious public signups; mitigated via Go `net.Dialer.Control` IP filtering before TCP handshake.
