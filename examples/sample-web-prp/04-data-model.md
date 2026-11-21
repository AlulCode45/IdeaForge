# 04. Data Model & Schema — DevPulse

## Entity-Relationship Diagram

```mermaid
erDiagram
    WORKSPACES ||--o{ MONITORS : owns
    WORKSPACES ||--o{ ALERT_CHANNELS : configures
    MONITORS ||--o{ CHECK_LOGS : records
    MONITORS ||--o{ INCIDENTS : triggers

    WORKSPACES {
        uuid id PK
        string slug UK
        string name
        timestamp created_at
    }
    MONITORS {
        uuid id PK
        uuid workspace_id FK
        string url
        int interval_sec
        string status
    }
    CHECK_LOGS {
        bigint id PK
        uuid monitor_id FK
        int status_code
        int latency_ms
        timestamp checked_at
    }
    INCIDENTS {
        uuid id PK
        uuid monitor_id FK
        string state
        timestamp started_at
        timestamp resolved_at
    }
```

## Storage & Retention Policy
- Retain raw `check_logs` for 30 days, and roll up daily uptime percentages into `daily_uptime_stats` for the 90-day public status bar [Estimate].
- Partition `check_logs` monthly by `checked_at` to keep index size bounded.
