# WPACS V2 Architecture

WPACS V2 uses an event-driven model.

```text
Windows Desktop Agent
  -> POST /api/v2/events
  -> PostgreSQL workstation_events
  -> productivity_daily calculation
  -> /api/v2/live WebSocket
  -> Agent, Manager, and Admin apps
```

PostgreSQL is the source of truth. The desktop agent never writes to the database directly.

## Roles

- `AGENT`: sends and views its own workstation events.
- `MANAGER`: views assigned employees.
- `SUPERVISOR`: read-only scoped visibility.
- `ADMIN`: full system access.

## Productivity

```text
Productive Time = Shift Duration - Locked Duration
```
