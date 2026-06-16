from datetime import datetime, time, timezone
import os

from app.database import query, query_one


def _minutes(start_at, end_at) -> int:
    return max(0, int((end_at - start_at).total_seconds() // 60))


def calculate_daily(employee_id: str, target_date):
    heartbeat_gap_seconds = int(os.environ.get("WPACS_OFFLINE_HEARTBEAT_GAP_SECONDS", "90"))
    start_at = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(target_date, time.max, tzinfo=timezone.utc)
    rows = query(
        """
        SELECT event_type, event_timestamp
        FROM workstation_events
        WHERE employee_id = %s
          AND event_timestamp >= %s
          AND event_timestamp <= %s
        ORDER BY event_timestamp ASC, id ASC
        """,
        (employee_id, start_at, end_at),
    )
    shift_start = None
    shift_end = None
    lock_start = None
    locked_minutes = 0
    offline_minutes = 0
    last_heartbeat = None
    for row in rows:
        event_type = row["event_type"]
        event_time = row["event_timestamp"]
        if event_type == "SHIFT_START":
            shift_start = event_time
            last_heartbeat = None
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
        elif event_type == "HEARTBEAT" and shift_start and not shift_end:
            if last_heartbeat:
                gap_seconds = max(0, int((event_time - last_heartbeat).total_seconds()))
                if gap_seconds > heartbeat_gap_seconds:
                    offline_minutes += (gap_seconds - heartbeat_gap_seconds) // 60
            last_heartbeat = event_time
        elif event_type in {"LOGOFF", "LOGOUT"} and shift_start and not shift_end:
            if last_heartbeat:
                gap_seconds = max(0, int((event_time - last_heartbeat).total_seconds()))
                offline_minutes += gap_seconds // 60
    if not shift_start:
        total_minutes = 0
        productive_minutes = 0
    else:
        effective_end = shift_end or datetime.now(timezone.utc)
        if lock_start:
            locked_minutes += _minutes(lock_start, effective_end)
        if last_heartbeat and not shift_end:
            gap_seconds = max(0, int((effective_end - last_heartbeat).total_seconds()))
            if gap_seconds > heartbeat_gap_seconds:
                offline_minutes += (gap_seconds - heartbeat_gap_seconds) // 60
        total_minutes = _minutes(shift_start, effective_end)
        productive_minutes = max(0, total_minutes - locked_minutes - offline_minutes)
    score = round((productive_minutes / total_minutes) * 100, 2) if total_minutes else 0
    return query_one(
        """
        INSERT INTO productivity_daily (
          employee_id, date, productive_minutes, locked_minutes,
          logged_out_minutes, productivity_score, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (employee_id, date) DO UPDATE SET
          productive_minutes = EXCLUDED.productive_minutes,
          locked_minutes = EXCLUDED.locked_minutes,
          logged_out_minutes = EXCLUDED.logged_out_minutes,
          productivity_score = EXCLUDED.productivity_score,
          updated_at = NOW()
        RETURNING employee_id, date, productive_minutes, locked_minutes, logged_out_minutes, productivity_score, updated_at
        """,
        (employee_id, target_date, productive_minutes, locked_minutes, offline_minutes, score),
    )
