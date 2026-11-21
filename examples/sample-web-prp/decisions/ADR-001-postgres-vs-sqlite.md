# ADR-001: Managed PostgreSQL vs Single-Node SQLite for MVP

- **Date**: 2026-11-22
- **Status**: Accepted

## Context
The Next.js web dashboard and the Go poller worker run as separate processes and both write/read monitor state and check logs concurrently.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| A. Embedded SQLite (WAL) | Zero extra DB cost | Single-host coupling between Next.js and Go worker |
| B. Managed PostgreSQL | Clean separation of web & worker, native monthly partitioning | ~USD 10/mo base cost |

## Decision
Select Option B (Managed PostgreSQL) so the Next.js app and Go poller can scale and deploy independently.

## Rationale and evidence
Supports concurrent writes from the Go poller and partitioned `check_logs` retention in [04-data-model.md](../04-data-model.md).

## Consequences and revisit trigger
Adds USD 10/mo fixed cost ([03-architecture.md](../03-architecture.md)); revisit read-replica or TimescaleDB only if `check_logs` exceeds 50M rows/month.
