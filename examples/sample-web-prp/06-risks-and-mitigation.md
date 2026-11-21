# 06. Technical & Delivery Risks — DevPulse

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| TR-1 | **SSRF vulnerability** via user-submitted monitor URLs probing internal/cloud metadata IPs | Medium | Critical | Resolve DNS in Go dialer (`Control` hook) and block RFC1918, loopback, and `169.254.169.254` before connecting |
| TR-2 | **False-positive incident alerts** from transient network blips | High | High | Require 2 consecutive failures (10s apart) before opening an incident |
| TR-3 | **Unbounded `check_logs` table growth** degrading dashboard queries | Medium | Medium | Partition `check_logs` by month + pre-aggregate 90-day daily uptime stats |
| TR-4 | **Alert storm** during regional DNS outage | Low | Medium | Deduplicate alerts per `incident_id` and rate-limit webhook retries with exponential backoff |
