from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
import base64
from datetime import datetime, time as datetime_time, timezone
import hashlib
import json
import mimetypes
import os
import secrets
import socket
import struct
import threading
import time
import urllib.parse

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - surfaced through /health when dependency is missing.
    psycopg = None
    dict_row = None


ROOT = Path(__file__).resolve().parent
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "28800"))
SESSIONS = {}
RBAC_ROLES = ("ADMIN", "MANAGER", "SUPERVISOR")
EVENT_TYPES = ("LOGIN", "LOGOUT", "LOGOFF", "LOCK", "UNLOCK", "HEARTBEAT", "SHIFT_START", "SHIFT_END")
WEBSOCKET_CLIENTS = set()
WEBSOCKET_LOCK = threading.Lock()


def normalize_role(role_name):
    return str(role_name or "").strip().upper()


def database_url():
    return os.environ.get("DATABASE_URL", "")


def db_ready():
    return bool(database_url() and psycopg)


def connect():
    if not db_ready():
        raise RuntimeError("DATABASE_URL is required and psycopg must be installed")
    return psycopg.connect(database_url(), row_factory=dict_row)


def query(sql, params=()):
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount


def audit_event(session, action, target, details=""):
    actor = session["user"].get("username", "system") if session else "system"
    execute(
        """
        INSERT INTO audit_log (actor, action, target, details)
        VALUES (%s, %s, %s, %s)
        """,
        (actor, action, target, details),
    )


def audit_action_for_event(event_type):
    return {
        "SHIFT_START": "Shift Started",
        "SHIFT_END": "Shift Ended",
        "LOGIN": "Status Changed",
        "LOGOUT": "Status Changed",
        "LOGOFF": "Status Changed",
        "LOCK": "Status Changed",
        "UNLOCK": "Status Changed",
        "HEARTBEAT": "Status Changed",
    }[event_type]


def parse_event_timestamp(value):
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def today_utc():
    return datetime.now(timezone.utc).date()


def event_date_bounds(target_date):
    return (
        datetime.combine(target_date, datetime_time.min, tzinfo=timezone.utc),
        datetime.combine(target_date, datetime_time.max, tzinfo=timezone.utc),
    )


def minutes_between(start_at, end_at):
    return max(0, int((end_at - start_at).total_seconds() // 60))


def derive_status(event_type):
    if event_type in ("LOGIN", "UNLOCK", "HEARTBEAT", "SHIFT_START"):
        return "ONLINE", "ONLINE"
    if event_type == "LOCK":
        return "LOCKED", "ONLINE"
    return "OFFLINE", "OFFLINE"


def derive_shift_state(event_type, previous_shift_state):
    if event_type == "SHIFT_START":
        return "ACTIVE"
    if event_type == "SHIFT_END":
        return "ENDED"
    return previous_shift_state or "NOT_STARTED"


def send_ws_frame(client, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    header = bytearray([0x81])
    length = len(body)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127)
        header.extend(struct.pack("!Q", length))
    client.sendall(header + body)


def broadcast_live_update(kind, payload):
    message = {"type": kind, "payload": payload}
    with WEBSOCKET_LOCK:
        clients = list(WEBSOCKET_CLIENTS)
    for client in clients:
        try:
            send_ws_frame(client, message)
        except OSError:
            with WEBSOCKET_LOCK:
                WEBSOCKET_CLIENTS.discard(client)


def calculate_productivity_for_day(employee_id, target_date):
    start_at, end_at = event_date_bounds(target_date)
    events = query(
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
    locked_minutes = 0
    open_lock = None

    for event in events:
        event_type = event["event_type"]
        timestamp = event["event_timestamp"]
        if event_type == "SHIFT_START":
            shift_start = timestamp
        elif event_type == "SHIFT_END":
            shift_end = timestamp
            if open_lock:
                locked_minutes += minutes_between(open_lock, timestamp)
                open_lock = None
        elif event_type == "LOCK" and shift_start and not shift_end and not open_lock:
            open_lock = timestamp
        elif event_type == "UNLOCK" and open_lock:
            locked_minutes += minutes_between(open_lock, timestamp)
            open_lock = None

    if not shift_start:
        productive_minutes = 0
        total_shift_minutes = 0
    else:
        effective_end = shift_end or datetime.now(timezone.utc)
        if open_lock:
            locked_minutes += minutes_between(open_lock, effective_end)
        total_shift_minutes = minutes_between(shift_start, effective_end)
        productive_minutes = max(0, total_shift_minutes - locked_minutes)

    productivity_score = round((productive_minutes / total_shift_minutes) * 100, 2) if total_shift_minutes else 0
    row = query_one(
        """
        INSERT INTO productivity_daily (
          employee_id,
          date,
          productive_minutes,
          locked_minutes,
          logged_out_minutes,
          productivity_score,
          updated_at
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
        (employee_id, target_date, productive_minutes, locked_minutes, 0, productivity_score),
    )
    return row


def sync_shift_attendance(employee_id, event_type, target_date, productivity=None):
    if event_type not in ("SHIFT_START", "SHIFT_END"):
        return None
    if event_type == "SHIFT_START":
        return query_one(
            """
            INSERT INTO attendance (employee_id, attendance_date, status, worked_hours)
            VALUES (%s, %s, 'PRESENT', 0)
            RETURNING attendance_id, employee_id, attendance_date, status, worked_hours, created_at
            """,
            (employee_id, target_date),
        )
    total_minutes = 0
    if productivity:
        total_minutes = int(productivity.get("productive_minutes") or 0)
        total_minutes += int(productivity.get("locked_minutes") or 0)
        total_minutes += int(productivity.get("logged_out_minutes") or 0)
    latest = query_one(
        """
        SELECT attendance_id
        FROM attendance
        WHERE employee_id = %s
          AND attendance_date = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (employee_id, target_date),
    )
    if latest:
        return query_one(
            """
            UPDATE attendance
            SET worked_hours = %s
            WHERE attendance_id = %s
            RETURNING attendance_id, employee_id, attendance_date, status, worked_hours, created_at
            """,
            (round(total_minutes / 60, 2), latest["attendance_id"]),
        )
    return query_one(
        """
        INSERT INTO attendance (employee_id, attendance_date, status, worked_hours)
        VALUES (%s, %s, 'PRESENT', %s)
        RETURNING attendance_id, employee_id, attendance_date, status, worked_hours, created_at
        """,
        (employee_id, target_date, round(total_minutes / 60, 2)),
    )


def hash_password(password):
    iterations = 260000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() not in ("false", "0", "inactive", "no")


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return secrets.compare_digest(digest.hex(), expected)
    except ValueError:
        return False


def now_epoch():
    return int(time.time())


def create_session(user):
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"user": user, "expires": now_epoch() + SESSION_TTL_SECONDS}
    return token


def get_session(cookie_header):
    cookie = SimpleCookie(cookie_header or "")
    token = cookie.get("wpacs_session")
    if not token:
        return None
    session = SESSIONS.get(token.value)
    if not session or session["expires"] < now_epoch():
        SESSIONS.pop(token.value, None)
        return None
    session["expires"] = now_epoch() + SESSION_TTL_SECONDS
    return session


def response(success=True, data=None, message="OK", errors=None):
    return {
        "success": success,
        "data": data if data is not None else {},
        "message": message,
        "errors": errors or [],
    }


def require_roles(handler, *roles):
    session = get_session(handler.headers.get("Cookie"))
    if not session:
        handler.send_json(401, response(False, message="Authentication required"))
        return None
    allowed_roles = {normalize_role(role) for role in roles}
    user_role = normalize_role(session["user"].get("role"))
    if allowed_roles and user_role not in allowed_roles:
        handler.send_json(403, response(False, message="Access denied"))
        return None
    return session


def employee_scope(session):
    return session["user"].get("employee_id")


def manager_exists(manager_id):
    if not manager_id:
        return True
    manager = query_one(
        """
        SELECT u.user_id
        FROM users u
        JOIN roles r ON r.role_id = u.role_id
        WHERE u.user_id::text = %s
          AND UPPER(r.role_name) = 'MANAGER'
          AND u.active = TRUE
        """,
        (str(manager_id),),
    )
    return bool(manager)


def employee_exists(employee_id):
    if not employee_id:
        return False
    return bool(query_one("SELECT employee_id FROM employees WHERE employee_id = %s", (employee_id,)))


def manager_employee_clause(session, employee_alias="e"):
    user = session["user"]
    if normalize_role(user.get("role")) == "MANAGER":
        return f" AND {employee_alias}.manager_id = %s", (str(user.get("user_id")),)
    return "", ()


def can_access_employee(session, employee_id):
    if normalize_role(session["user"].get("role")) != "MANAGER":
        return True
    employee = query_one(
        "SELECT employee_id FROM employees WHERE employee_id = %s AND manager_id = %s",
        (employee_id, str(session["user"].get("user_id"))),
    )
    return bool(employee)


def can_write_employee_event(session, employee_id):
    user = session["user"]
    role = normalize_role(user.get("role"))
    if role == "SUPERVISOR":
        return False
    if user.get("employee_id") and str(user.get("employee_id")) == str(employee_id):
        return True
    if role == "ADMIN":
        return True
    return can_access_employee(session, employee_id)


def upsert_agent_status(employee_id, event_type, event_timestamp):
    previous = query_one("SELECT shift_state FROM agent_status WHERE employee_id = %s", (employee_id,))
    current_status, connection_status = derive_status(event_type)
    shift_state = derive_shift_state(event_type, previous.get("shift_state") if previous else "NOT_STARTED")
    row = query_one(
        """
        INSERT INTO agent_status (
          employee_id,
          current_status,
          shift_state,
          last_event_type,
          last_activity_at,
          last_heartbeat_at,
          connection_status,
          updated_at
        )
        VALUES (
          %s, %s, %s, %s, %s,
          CASE WHEN %s = 'HEARTBEAT' THEN %s ELSE NULL END,
          %s,
          NOW()
        )
        ON CONFLICT (employee_id) DO UPDATE SET
          current_status = EXCLUDED.current_status,
          shift_state = EXCLUDED.shift_state,
          last_event_type = EXCLUDED.last_event_type,
          last_activity_at = EXCLUDED.last_activity_at,
          last_heartbeat_at = CASE WHEN EXCLUDED.last_event_type = 'HEARTBEAT' THEN EXCLUDED.last_activity_at ELSE agent_status.last_heartbeat_at END,
          connection_status = EXCLUDED.connection_status,
          updated_at = NOW()
        RETURNING employee_id, current_status, shift_state, last_event_type, last_activity_at, last_heartbeat_at, connection_status, updated_at
        """,
        (
            employee_id,
            current_status,
            shift_state,
            event_type,
            event_timestamp,
            event_type,
            event_timestamp,
            connection_status,
        ),
    )
    return row


def agent_status_rows(session, employee_id=None):
    role = normalize_role(session["user"].get("role"))
    params = []
    where = ["TRUE"]
    if employee_id:
        if not can_access_employee(session, employee_id):
            return None
        where.append("e.employee_id = %s")
        params.append(employee_id)
    elif role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(session["user"].get("user_id")))
    elif role == "SUPERVISOR" and session["user"].get("employee_id"):
        where.append("e.employee_id = %s")
        params.append(str(session["user"].get("employee_id")))
    elif role == "SUPERVISOR":
        where.append("FALSE")
    return query(
        f"""
        SELECT
          e.employee_id,
          e.employee_name,
          e.department,
          e.manager_id,
          COALESCE(s.current_status, 'OFFLINE') AS current_status,
          COALESCE(s.shift_state, 'NOT_STARTED') AS shift_state,
          s.last_event_type,
          s.last_activity_at,
          s.last_heartbeat_at,
          COALESCE(s.connection_status, 'OFFLINE') AS connection_status,
          s.updated_at
        FROM employees e
        LEFT JOIN agent_status s ON s.employee_id = e.employee_id
        WHERE {' AND '.join(where)}
        ORDER BY e.employee_name
        """,
        tuple(params),
    )


def productivity_rows(session, employee_id=None, target_date=None):
    role = normalize_role(session["user"].get("role"))
    params = []
    where = ["TRUE"]
    if employee_id:
        if not can_access_employee(session, employee_id):
            return None
        where.append("e.employee_id = %s")
        params.append(employee_id)
    elif role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(session["user"].get("user_id")))
    elif role == "SUPERVISOR" and session["user"].get("employee_id"):
        where.append("e.employee_id = %s")
        params.append(str(session["user"].get("employee_id")))
    elif role == "SUPERVISOR":
        where.append("FALSE")
    if target_date:
        where.append("p.date = %s")
        params.append(target_date)
    return query(
        f"""
        SELECT
          p.employee_id,
          e.employee_name,
          p.date,
          p.productive_minutes,
          p.locked_minutes,
          p.logged_out_minutes,
          p.productivity_score,
          p.updated_at
        FROM productivity_daily p
        JOIN employees e ON e.employee_id = p.employee_id
        WHERE {' AND '.join(where)}
        ORDER BY p.date DESC, e.employee_name
        """,
        tuple(params),
    )


def workstation_event_rows(session, employee_id=None, limit=50):
    role = normalize_role(session["user"].get("role"))
    params = []
    where = ["TRUE"]
    if employee_id:
        if not can_access_employee(session, employee_id):
            return None
        where.append("e.employee_id = %s")
        params.append(employee_id)
    elif role == "MANAGER":
        where.append("e.manager_id = %s")
        params.append(str(session["user"].get("user_id")))
    elif role == "SUPERVISOR" and session["user"].get("employee_id"):
        where.append("e.employee_id = %s")
        params.append(str(session["user"].get("employee_id")))
    elif role == "SUPERVISOR":
        where.append("FALSE")
    params.append(max(1, min(int(limit or 50), 200)))
    return query(
        f"""
        SELECT
          w.id,
          w.employee_id,
          e.employee_name,
          w.event_type,
          w.event_timestamp,
          w.source,
          w.created_at
        FROM workstation_events w
        JOIN employees e ON e.employee_id = w.employee_id
        WHERE {' AND '.join(where)}
        ORDER BY w.event_timestamp DESC, w.id DESC
        LIMIT %s
        """,
        tuple(params),
    )


def todays_attendance_rows(session, employee_id):
    if not can_access_employee(session, employee_id):
        return None
    return query(
        """
        SELECT a.attendance_id, a.employee_id, e.employee_name, a.attendance_date, a.status, a.worked_hours, a.created_at
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.employee_id = %s
          AND a.attendance_date = CURRENT_DATE
        ORDER BY a.created_at DESC
        """,
        (employee_id,),
    )


def dashboard_payload(session):
    employee_filter, employee_params = manager_employee_clause(session, "e")
    totals = query_one(
        f"""
        SELECT
          COUNT(*) AS employees,
          ROUND(AVG(productivity_score)) AS productivity_score,
          COALESCE(SUM(productive_hours), 0) AS productive_hours,
          COALESCE(SUM(non_productive_hours), 0) AS non_productive_hours,
          COUNT(p.productivity_id) AS productivity_records
        FROM employees e
        LEFT JOIN productivity p ON p.employee_id = e.employee_id
        WHERE TRUE {employee_filter}
        """,
        employee_params,
    ) or {}
    attendance_filter, attendance_params = manager_employee_clause(session, "e")
    attendance = query_one(
        f"""
        SELECT
          COUNT(*) AS records,
          COALESCE(SUM(a.worked_hours), 0) AS worked_hours
        FROM attendance a
        JOIN employees e ON e.employee_id = a.employee_id
        WHERE TRUE {attendance_filter}
        """,
        attendance_params,
    ) or {}
    trend_filter, trend_params = manager_employee_clause(session, "e")
    trend = query(
        f"""
        SELECT p.report_date::text AS label, ROUND(AVG(p.productivity_score))::int AS value
        FROM productivity p
        JOIN employees e ON e.employee_id = p.employee_id
        WHERE TRUE {trend_filter}
        GROUP BY p.report_date
        ORDER BY p.report_date DESC
        LIMIT 10
        """,
        trend_params,
    )
    return {
        "metrics": {
            "employees": int(totals.get("employees") or 0),
            "productivity_score": int(totals["productivity_score"]) if totals.get("productivity_score") is not None else None,
            "productive_hours": float(totals.get("productive_hours") or 0),
            "non_productive_hours": float(totals.get("non_productive_hours") or 0),
            "productivity_records": int(totals.get("productivity_records") or 0),
            "attendance_records": int(attendance.get("records") or 0),
            "worked_hours": float(attendance.get("worked_hours") or 0),
        },
        "trend": list(reversed(trend)),
    }


class Handler(SimpleHTTPRequestHandler):
    def handle_websocket(self, session):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_json(400, response(False, message="Missing WebSocket key"))
            return
        accept = base64.b64encode(
            hashlib.sha1(f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode("ascii")).digest()
        ).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        self.connection.settimeout(45)
        with WEBSOCKET_LOCK:
            WEBSOCKET_CLIENTS.add(self.connection)
        try:
            send_ws_frame(self.connection, {"type": "connected", "payload": {"role": session["user"].get("role")}})
            while True:
                try:
                    data = self.connection.recv(2)
                except socket.timeout:
                    send_ws_frame(self.connection, {"type": "heartbeat", "payload": {}})
                    continue
                if not data:
                    break
                opcode = data[0] & 0x0F
                masked_length = data[1] & 0x7F
                if masked_length == 126:
                    length_data = self.connection.recv(2)
                    masked_length = struct.unpack("!H", length_data)[0]
                elif masked_length == 127:
                    length_data = self.connection.recv(8)
                    masked_length = struct.unpack("!Q", length_data)[0]
                mask = self.connection.recv(4)
                payload = self.connection.recv(masked_length) if masked_length else b""
                if mask and payload:
                    payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
                if opcode == 0x8:
                    break
        finally:
            with WEBSOCKET_LOCK:
                WEBSOCKET_CLIENTS.discard(self.connection)

    def send_json(self, status, payload):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/v1/auth/login":
            if not db_ready():
                self.send_json(503, response(False, message="Database is not configured"))
                return
            payload = self.read_json()
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password_hash", ""))
            selected_role = normalize_role(payload.get("role", ""))
            if selected_role not in RBAC_ROLES:
                self.send_json(400, response(False, message="Valid role selection is required"))
                return
            user = query_one(
                """
                SELECT u.user_id, u.username, u.password_hash, u.active, u.employee_id, UPPER(r.role_name) AS role
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE u.username = %s
                """,
                (username,),
            )
            if not user or not user["active"] or not verify_password(password, user["password_hash"]):
                self.send_json(401, response(False, message="Invalid username or password"))
                return
            if normalize_role(user["role"]) != selected_role:
                self.send_json(403, response(False, message="Selected role is not assigned to this user"))
                return
            safe_user = {key: value for key, value in user.items() if key != "password_hash"}
            token = create_session(safe_user)
            body = json.dumps(response(True, safe_user, "Login successful")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"wpacs_session={token}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/auth/logout":
            cookie = SimpleCookie(self.headers.get("Cookie") or "")
            token = cookie.get("wpacs_session")
            if token:
                SESSIONS.pop(token.value, None)
            self.send_response(204)
            self.send_header("Set-Cookie", "wpacs_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
            self.end_headers()
            return

        if parsed.path == "/api/v2/events":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            payload = self.read_json()
            employee_id = str(payload.get("employee_id") or session["user"].get("employee_id") or "").strip()
            event_type = normalize_role(payload.get("event_type"))
            source = str(payload.get("source") or "web").strip()
            if event_type not in EVENT_TYPES:
                self.send_json(400, response(False, message="Unsupported event type"))
                return
            if not employee_id:
                self.send_json(400, response(False, message="Employee ID is required"))
                return
            if not employee_exists(employee_id):
                self.send_json(400, response(False, message="Selected employee does not exist"))
                return
            if not can_write_employee_event(session, employee_id):
                self.send_json(403, response(False, message="Access denied for this employee event"))
                return
            try:
                event_timestamp = parse_event_timestamp(payload.get("event_timestamp"))
            except ValueError:
                self.send_json(400, response(False, message="Invalid event timestamp"))
                return
            event = query_one(
                """
                INSERT INTO workstation_events (employee_id, event_type, event_timestamp, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id, employee_id, event_type, event_timestamp, source, created_at
                """,
                (employee_id, event_type, event_timestamp, source),
            )
            status = upsert_agent_status(employee_id, event_type, event_timestamp)
            productivity = calculate_productivity_for_day(employee_id, event_timestamp.date())
            attendance = sync_shift_attendance(employee_id, event_type, event_timestamp.date(), productivity)
            audit_event(session, audit_action_for_event(event_type), employee_id, f"{event_type} from {source}")
            broadcast_live_update("workstation_event", event)
            broadcast_live_update("agent_status", status)
            broadcast_live_update("productivity", productivity)
            if attendance:
                broadcast_live_update("attendance", attendance)
            self.send_json(201, response(True, {"event": event, "status": status, "productivity": productivity, "attendance": attendance}, "Event saved"))
            return

        session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
        if not session:
            return

        if parsed.path == "/api/v1/attendance":
            payload = self.read_json()
            employee_id = payload.get("employee_id")
            employee_count = query_one("SELECT COUNT(*) AS count FROM employees") or {}
            if int(employee_count.get("count") or 0) == 0:
                self.send_json(400, response(False, message="No employees available. Create an employee first."))
                return
            if not employee_id:
                self.send_json(400, response(False, message="Employee ID is required"))
                return
            if not employee_exists(employee_id):
                self.send_json(400, response(False, message="Selected employee does not exist"))
                return
            if not can_access_employee(session, employee_id):
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            execute(
                """
                INSERT INTO attendance (employee_id, attendance_date, status, worked_hours)
                VALUES (%s, %s, %s, %s)
                """,
                (employee_id, payload.get("attendance_date"), payload.get("status"), payload.get("worked_hours")),
            )
            audit_event(session, "Attendance Marked", employee_id, f"{payload.get('status')} on {payload.get('attendance_date')}")
            broadcast_live_update("attendance", {"employee_id": employee_id, "attendance_date": payload.get("attendance_date")})
            self.send_json(201, response(True, message="Attendance saved"))
            return

        if parsed.path == "/api/v1/employees":
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            payload = self.read_json()
            employee_id = str(payload.get("employee_id", "")).strip()
            manager_id = str(payload.get("manager_id") or "").strip() or None
            if normalize_role(session["user"].get("role")) == "MANAGER":
                manager_id = str(session["user"].get("user_id"))
            if not employee_id or not payload.get("employee_name") or not payload.get("department"):
                self.send_json(400, response(False, message="Employee ID, name, and department are required"))
                return
            if employee_exists(employee_id):
                self.send_json(409, response(False, message="Employee already exists"))
                return
            if not manager_exists(manager_id):
                self.send_json(400, response(False, message="Manager must be an active MANAGER user"))
                return
            employee = query_one(
                """
                INSERT INTO employees (employee_id, employee_name, department, manager_id, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING employee_id, employee_name, department, manager_id, status, created_at
                """,
                (
                    employee_id,
                    payload.get("employee_name"),
                    payload.get("department"),
                    manager_id,
                    payload.get("status") or "ACTIVE",
                ),
            )
            audit_event(session, "Employee Created", employee_id, f"Created employee {payload.get('employee_name')}")
            self.send_json(201, response(True, employee, "Employee saved"))
            return

        if parsed.path == "/api/v1/productivity":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            payload = self.read_json()
            employee_id = payload.get("employee_id")
            if not employee_id:
                self.send_json(400, response(False, message="Employee ID is required"))
                return
            if not employee_exists(employee_id):
                self.send_json(400, response(False, message="Selected employee does not exist"))
                return
            if not can_access_employee(session, employee_id):
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            productivity = query_one(
                """
                INSERT INTO productivity (
                  employee_id,
                  productive_hours,
                  non_productive_hours,
                  productivity_score,
                  report_date
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING productivity_id, employee_id, productive_hours, non_productive_hours, productivity_score, report_date
                """,
                (
                    employee_id,
                    payload.get("productive_hours") or 0,
                    payload.get("non_productive_hours") or 0,
                    payload.get("productivity_score") or 0,
                    payload.get("report_date"),
                ),
            )
            self.send_json(201, response(True, productivity, "Productivity saved"))
            return

        if parsed.path == "/api/v1/users":
            session = require_roles(self, "ADMIN")
            if not session:
                return
            payload = self.read_json()
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            role_name = normalize_role(payload.get("role_name", ""))
            employee_id = payload.get("employee_id") or None
            if not username or not role_name:
                self.send_json(400, response(False, message="Username and role are required"))
                return
            if role_name not in RBAC_ROLES:
                self.send_json(400, response(False, message="Invalid role"))
                return
            role = query_one("SELECT role_id FROM roles WHERE UPPER(role_name) = %s", (role_name,))
            if not role:
                self.send_json(400, response(False, message="Invalid role"))
                return
            existing_user = query_one("SELECT password_hash FROM users WHERE username = %s", (username,))
            if not password and not existing_user:
                self.send_json(400, response(False, message="Password is required for new users"))
                return
            password_hash = hash_password(password) if password else existing_user["password_hash"]
            user = query_one(
                """
                INSERT INTO users (username, password_hash, role_id, employee_id, active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                  password_hash = EXCLUDED.password_hash,
                  role_id = EXCLUDED.role_id,
                  employee_id = EXCLUDED.employee_id,
                  active = EXCLUDED.active
                RETURNING user_id, username, role_id, employee_id, active
                """,
                (username, password_hash, role["role_id"], employee_id, normalize_bool(payload.get("active", True))),
            )
            if existing_user:
                if not normalize_bool(payload.get("active", True)):
                    action = "User Disabled"
                elif password:
                    action = "Password Reset"
                else:
                    action = "User Updated"
            else:
                action = "User Created"
            audit_event(session, action, username, f"Role {role_name}")
            self.send_json(201, response(True, user, "User account saved"))
            return

        if parsed.path == "/api/v1/reports":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            payload = self.read_json()
            report = query_one(
                """
                INSERT INTO reports (report_name, report_type)
                VALUES (%s, %s)
                RETURNING report_id, report_name, report_type, generated_at
                """,
                (payload.get("report_name"), payload.get("report_type")),
            )
            self.send_json(201, response(True, report, "Report generated"))
            return

        self.send_json(404, response(False, message="Route not found"))

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/v1/employees/"):
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            employee_id = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
            payload = self.read_json()
            manager_id = str(payload.get("manager_id") or "").strip() or None
            if normalize_role(session["user"].get("role")) == "MANAGER":
                manager_id = str(session["user"].get("user_id"))
            if not employee_exists(employee_id):
                self.send_json(404, response(False, message="Employee not found"))
                return
            if not can_access_employee(session, employee_id):
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            if not payload.get("employee_name") or not payload.get("department"):
                self.send_json(400, response(False, message="Employee name and department are required"))
                return
            if not manager_exists(manager_id):
                self.send_json(400, response(False, message="Manager must be an active MANAGER user"))
                return
            employee = query_one(
                """
                UPDATE employees
                SET employee_name = %s,
                    department = %s,
                    manager_id = %s,
                    status = %s
                WHERE employee_id = %s
                RETURNING employee_id, employee_name, department, manager_id, status, created_at
                """,
                (
                    payload.get("employee_name"),
                    payload.get("department"),
                    manager_id,
                    payload.get("status") or "ACTIVE",
                    employee_id,
                ),
            )
            audit_event(session, "Employee Updated", employee_id, f"Updated employee {payload.get('employee_name')}")
            self.send_json(200, response(True, employee, "Employee updated"))
            return
        self.send_json(404, response(False, message="Route not found"))

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/v1/employees/"):
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            employee_id = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
            employee = query_one("SELECT employee_name FROM employees WHERE employee_id = %s", (employee_id,))
            if not employee:
                self.send_json(404, response(False, message="Employee not found"))
                return
            if not can_access_employee(session, employee_id):
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            execute("DELETE FROM users WHERE employee_id = %s", (employee_id,))
            execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
            audit_event(session, "Employee Deleted", employee_id, f"Deleted employee {employee.get('employee_name')}")
            self.send_json(200, response(True, message="Employee deleted"))
            return
        self.send_json(404, response(False, message="Route not found"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/api/v1/health", "/agent/v1/health"):
            self.send_json(200, {"status": "ok", "database": "configured" if db_ready() else "not_configured"})
            return

        if parsed.path == "/api/v2/live":
            if not db_ready():
                self.send_json(503, response(False, message="Database is not configured"))
                return
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            if self.headers.get("Upgrade", "").lower() != "websocket":
                self.send_json(400, response(False, message="WebSocket upgrade required"))
                return
            self.handle_websocket(session)
            return

        if parsed.path.startswith("/api/"):
            if not db_ready():
                self.send_json(503, response(False, message="Database is not configured"))
                return

        if parsed.path == "/api/v1/auth/me":
            session = get_session(self.headers.get("Cookie"))
            if not session:
                self.send_json(401, response(False, message="Authentication required"))
                return
            self.send_json(200, response(True, session["user"]))
            return

        if parsed.path == "/api/v2/agent-status":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            rows = agent_status_rows(session, employee_id)
            if rows is None:
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            self.send_json(200, response(True, rows))
            return

        if parsed.path == "/api/v2/events":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            limit = params.get("limit", [50])[0]
            try:
                rows = workstation_event_rows(session, employee_id, limit)
            except ValueError:
                self.send_json(400, response(False, message="Invalid event limit"))
                return
            if rows is None:
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            self.send_json(200, response(True, rows))
            return

        if parsed.path == "/api/v2/productivity":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            target_date = params.get("date", [None])[0]
            rows = productivity_rows(session, employee_id, target_date)
            if rows is None:
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            self.send_json(200, response(True, rows))
            return

        if parsed.path == "/api/v2/agent-dashboard":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            requested_employee_id = params.get("employee_id", [None])[0]
            employee_id = session["user"].get("employee_id") or requested_employee_id
            if not employee_id:
                self.send_json(403, response(False, message="Authenticated user is not assigned to an employee"))
                return
            if not can_access_employee(session, str(employee_id)):
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            status_rows = agent_status_rows(session, str(employee_id))
            productivity = productivity_rows(session, str(employee_id), today_utc())
            attendance = todays_attendance_rows(session, str(employee_id))
            if status_rows is None or attendance is None:
                self.send_json(403, response(False, message="Access denied for this employee"))
                return
            self.send_json(200, response(True, {
                "employee_id": employee_id,
                "status": status_rows[0] if status_rows else None,
                "attendance": attendance,
                "productivity": productivity[0] if productivity else None,
            }))
            return

        if parsed.path == "/api/live-dashboard" or parsed.path == "/api/v1/dashboard":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            self.send_json(200, response(True, dashboard_payload(session)))
            return

        if parsed.path == "/api/v1/employees":
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            employee_filter, employee_params = manager_employee_clause(session, "e")
            self.send_json(200, response(True, query(
                f"""
                SELECT
                  e.employee_id,
                  e.employee_name,
                  e.department,
                  e.manager_id,
                  manager.username AS manager_name,
                  e.status,
                  e.created_at
                FROM employees e
                LEFT JOIN users manager ON manager.user_id::text = e.manager_id
                WHERE TRUE {employee_filter}
                ORDER BY e.created_at DESC, e.employee_name
                """,
                employee_params,
            )))
            return

        if parsed.path == "/api/v1/employee-options":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            employee_filter, employee_params = manager_employee_clause(session, "e")
            self.send_json(200, response(True, query(
                f"""
                SELECT employee_id, employee_name, department, status
                FROM employees e
                WHERE status = 'ACTIVE' {employee_filter}
                ORDER BY employee_name
                """,
                employee_params,
            )))
            return

        if parsed.path == "/api/v1/managers":
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            manager_filter = "AND u.user_id = %s" if normalize_role(session["user"].get("role")) == "MANAGER" else ""
            manager_params = (session["user"].get("user_id"),) if manager_filter else ()
            self.send_json(200, response(True, query(
                f"""
                SELECT u.user_id::text AS manager_id, u.username AS manager_name
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE UPPER(r.role_name) = 'MANAGER'
                  AND u.active = TRUE
                  {manager_filter}
                ORDER BY u.username
                """,
                manager_params,
            )))
            return

        if parsed.path == "/api/v1/roles":
            session = require_roles(self, "ADMIN")
            if not session:
                return
            self.send_json(200, response(True, query(
                "SELECT role_id, UPPER(role_name) AS role_name FROM roles WHERE UPPER(role_name) = ANY(%s) ORDER BY role_name",
                (list(RBAC_ROLES),),
            )))
            return

        if parsed.path == "/api/v1/users":
            session = require_roles(self, "ADMIN")
            if not session:
                return
            self.send_json(200, response(True, query(
                """
                SELECT u.user_id, u.username, UPPER(r.role_name) AS role_name, u.employee_id, u.active
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                ORDER BY u.user_id DESC
                """
            )))
            return

        if parsed.path == "/api/v1/attendance":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            if employee_id:
                if not can_access_employee(session, employee_id):
                    self.send_json(403, response(False, message="Access denied for this employee"))
                    return
                data = query(
                    """
                    SELECT a.attendance_id, a.employee_id, e.employee_name, a.attendance_date, a.status, a.worked_hours, a.created_at
                    FROM attendance a
                    JOIN employees e ON e.employee_id = a.employee_id
                    WHERE a.employee_id = %s
                    ORDER BY a.attendance_date DESC
                    """,
                    (employee_id,),
                )
            else:
                employee_filter, employee_params = manager_employee_clause(session, "e")
                data = query(
                    f"""
                    SELECT a.attendance_id, a.employee_id, e.employee_name, a.attendance_date, a.status, a.worked_hours, a.created_at
                    FROM attendance a
                    JOIN employees e ON e.employee_id = a.employee_id
                    WHERE TRUE {employee_filter}
                    ORDER BY a.attendance_date DESC
                    """,
                    employee_params,
                )
            self.send_json(200, response(True, data))
            return

        if parsed.path == "/api/v1/productivity":
            session = require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            if employee_id:
                if not can_access_employee(session, employee_id):
                    self.send_json(403, response(False, message="Access denied for this employee"))
                    return
                data = query(
                    """
                    SELECT p.productivity_id, p.employee_id, e.employee_name, p.productive_hours, p.non_productive_hours, p.productivity_score, p.report_date
                    FROM productivity p
                    JOIN employees e ON e.employee_id = p.employee_id
                    WHERE p.employee_id = %s
                    ORDER BY p.report_date DESC
                    """,
                    (employee_id,),
                )
            else:
                employee_filter, employee_params = manager_employee_clause(session, "e")
                data = query(
                    f"""
                    SELECT p.productivity_id, p.employee_id, e.employee_name, p.productive_hours, p.non_productive_hours, p.productivity_score, p.report_date
                    FROM productivity p
                    JOIN employees e ON e.employee_id = p.employee_id
                    WHERE TRUE {employee_filter}
                    ORDER BY p.report_date DESC
                    """,
                    employee_params,
                )
            self.send_json(200, response(True, data))
            return

        if parsed.path == "/api/v1/audit-log":
            if not require_roles(self, "ADMIN"):
                return
            self.send_json(200, response(True, query(
                """
                SELECT id, timestamp, actor, action, target, details
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT 100
                """
            )))
            return

        if parsed.path == "/api/v1/reports":
            if not require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR"):
                return
            self.send_json(200, response(True, query(
                """
                SELECT report_id, report_name, report_type, generated_at
                FROM reports
                ORDER BY generated_at DESC
                """
            )))
            return

        return super().do_GET()

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        target = parsed.path
        if target == "/":
            target = "/index.html"
        public_path = ROOT / "public" / target.lstrip("/")
        if public_path.exists():
            return str(public_path)
        source_path = ROOT / target.lstrip("/")
        if source_path.exists():
            return str(source_path)
        return str(ROOT / "public" / "index.html")


mimetypes.add_type("text/javascript", ".js")

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "4190"))
    public_url = os.environ.get("PUBLIC_URL", f"http://{host}:{port}")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"WPACS V1 production server running at {public_url}")
    server.serve_forever()
