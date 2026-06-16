from datetime import datetime, timezone

from app.database import query_one
from app.productivity.engine import calculate_daily


EVENT_TYPES = {"SHIFT_START", "SHIFT_END", "LOCK", "UNLOCK", "IDLE", "LOGIN", "LOGOFF", "LOGOUT", "HEARTBEAT"}


def parse_timestamp(value):
    if not value:
        return datetime.now(timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def derive_status(event_type: str):
    if event_type == "LOCK":
        return "LOCKED", "ONLINE"
    if event_type in {"SHIFT_START", "UNLOCK", "LOGIN", "HEARTBEAT"}:
        return "ONLINE", "ONLINE"
    if event_type == "IDLE":
        return "ONLINE", "ONLINE"
    return "OFFLINE", "OFFLINE"


def derive_shift(event_type: str, previous: str | None):
    if event_type == "SHIFT_START":
        return "ACTIVE"
    if event_type == "SHIFT_END":
        return "ENDED"
    return previous or "NOT_STARTED"


def process_event(employee_id: str, event_type: str, event_timestamp, source: str):
    event_type = event_type.upper()
    if event_type not in EVENT_TYPES:
        raise ValueError("Unsupported event type")
    event = query_one(
        """
        INSERT INTO workstation_events (employee_id, event_type, event_timestamp, source)
        VALUES (%s, %s, %s, %s)
        RETURNING id, employee_id, event_type, event_timestamp, source, created_at
        """,
        (employee_id, event_type, event_timestamp, source),
    )
    previous = query_one("SELECT shift_state FROM agent_status WHERE employee_id = %s", (employee_id,))
    current_status, connection_status = derive_status(event_type)
    shift_state = derive_shift(event_type, previous["shift_state"] if previous else None)
    status = query_one(
        """
        INSERT INTO agent_status (
          employee_id, current_status, shift_state, last_event_type,
          last_activity_at, last_heartbeat_at, connection_status, updated_at
        )
        VALUES (
          %s, %s, %s, %s, %s,
          CASE WHEN %s = 'HEARTBEAT' THEN %s ELSE NULL END,
          %s, NOW()
        )
        ON CONFLICT (employee_id) DO UPDATE SET
          current_status = EXCLUDED.current_status,
          shift_state = EXCLUDED.shift_state,
          last_event_type = EXCLUDED.last_event_type,
          last_activity_at = EXCLUDED.last_activity_at,
          last_heartbeat_at = CASE
            WHEN EXCLUDED.last_event_type = 'HEARTBEAT'
            THEN EXCLUDED.last_activity_at
            ELSE agent_status.last_heartbeat_at
          END,
          connection_status = EXCLUDED.connection_status,
          updated_at = NOW()
        RETURNING employee_id, current_status, shift_state, last_event_type,
                  last_activity_at, last_heartbeat_at, connection_status, updated_at
        """,
        (employee_id, current_status, shift_state, event_type, event_timestamp, event_type, event_timestamp, connection_status),
    )
    productivity = calculate_daily(employee_id, event_timestamp.date())
    return {"event": event, "status": status, "productivity": productivity}
