from datetime import datetime, time, timezone

from app.database import query, query_one


def _minutes(start_at, end_at) -> int:
    return max(0, int((end_at - start_at).total_seconds() // 60))


def calculate_daily(employee_id: str, target_date):
    start_at = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    rows = query(
        """
        SELECT event_type, event_timestamp
        FROM workstation_events
        WHERE employee_id = %s
          AND event_timestamp >= %s
          AND event_timestamp <= %s
          AND event_type <> 'HEARTBEAT'
        ORDER BY event_timestamp ASC, id ASC
        """,
        (employee_id, start_at, end_at),
    )
    shift_start = None
    shift_end = None
    lock_start = None
    locked_minutes = 0
    for row in rows:
        event_type = row["event_type"]
        event_time = row["event_timestamp"]
        if event_type == "SHIFT_START":
            shift_start = event_time
        elif event_type == "SHIFT_END":
            shift_end = event_time
            if lock_start:
                locked_minutes += _minutes(lock_start, event_time)
                lock_start = None
        elif event_type == "LOCK" and shift_start and not shift_end and not lock_start:
            lock_start = event_time
        elif event_type == "UNLOCK" and lock_start:
            locked_minutes += _minutes(lock_start, event_time)
            lock_start = None
    if not shift_start:
        total_minutes = 0
        productive_minutes = 0
    else:
        effective_end = shift_end or datetime.now(timezone.utc)
        if lock_start:
            locked_minutes += _minutes(lock_start, effective_end)
        total_minutes = _minutes(shift_start, effective_end)
        productive_minutes = max(0, total_minutes - locked_minutes)
    score = round((productive_minutes / total_minutes) * 100, 2) if total_minutes else 0
    return query_one(
        """
        INSERT INTO productivity_daily (
          employee_id, date, productive_minutes, locked_minutes,
          logged_out_minutes, productivity_score, updated_at
        )
        VALUES (%s, %s, %s, %s, 0, %s, NOW())
        ON CONFLICT (employee_id, date) DO UPDATE SET
          productive_minutes = EXCLUDED.productive_minutes,
          locked_minutes = EXCLUDED.locked_minutes,
          logged_out_minutes = 0,
          productivity_score = EXCLUDED.productivity_score,
          updated_at = NOW()
        RETURNING employee_id, date, productive_minutes, locked_minutes, logged_out_minutes, productivity_score, updated_at
        """,
        (employee_id, target_date, productive_minutes, locked_minutes, score),
    )
