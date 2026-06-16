from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
import hashlib
import json
import mimetypes
import os
import secrets
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


def hash_password(password):
    iterations = 260000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


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
    if roles and session["user"]["role_name"] not in roles:
        handler.send_json(403, response(False, message="Access denied"))
        return None
    return session


def employee_scope(session):
    return session["user"].get("employee_id")


def dashboard_payload():
    totals = query_one(
        """
        SELECT
          COUNT(*) AS employees,
          COALESCE(ROUND(AVG(productivity_score)), 0) AS productivity_score,
          COALESCE(SUM(productive_hours), 0) AS productive_hours,
          COALESCE(SUM(non_productive_hours), 0) AS non_productive_hours
        FROM employees e
        LEFT JOIN productivity p ON p.employee_id = e.employee_id
        """
    ) or {}
    attendance = query_one(
        """
        SELECT
          COUNT(*) AS records,
          COALESCE(SUM(worked_hours), 0) AS worked_hours
        FROM attendance
        """
    ) or {}
    trend = query(
        """
        SELECT report_date::text AS label, ROUND(AVG(productivity_score))::int AS value
        FROM productivity
        GROUP BY report_date
        ORDER BY report_date DESC
        LIMIT 10
        """
    )
    return {
        "metrics": {
            "employees": int(totals.get("employees") or 0),
            "productivity_score": int(totals.get("productivity_score") or 0),
            "productive_hours": float(totals.get("productive_hours") or 0),
            "non_productive_hours": float(totals.get("non_productive_hours") or 0),
            "attendance_records": int(attendance.get("records") or 0),
            "worked_hours": float(attendance.get("worked_hours") or 0),
        },
        "trend": list(reversed(trend)),
    }


class Handler(SimpleHTTPRequestHandler):
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
            user = query_one(
                """
                SELECT u.user_id, u.username, u.password_hash, u.active, u.employee_id, r.role_name
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE u.username = %s
                """,
                (username,),
            )
            if not user or not user["active"] or not verify_password(password, user["password_hash"]):
                self.send_json(401, response(False, message="Invalid username or password"))
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

        session = require_roles(self, "Admin", "Manager", "Supervisor", "Agent")
        if not session:
            return

        if parsed.path == "/api/v1/attendance":
            payload = self.read_json()
            employee_id = payload.get("employee_id") or employee_scope(session)
            if session["user"]["role_name"] == "Agent" and employee_id != employee_scope(session):
                self.send_json(403, response(False, message="Access denied"))
                return
            execute(
                """
                INSERT INTO attendance (employee_id, attendance_date, status, worked_hours)
                VALUES (%s, %s, %s, %s)
                """,
                (employee_id, payload.get("attendance_date"), payload.get("status"), payload.get("worked_hours")),
            )
            self.send_json(201, response(True, message="Attendance saved"))
            return

        if parsed.path == "/api/v1/employees":
            session = require_roles(self, "Admin", "Manager", "Supervisor")
            if not session:
                return
            payload = self.read_json()
            employee = query_one(
                """
                INSERT INTO employees (employee_id, employee_name, department, manager_id, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING employee_id, employee_name, department, manager_id, status, created_at
                """,
                (
                    payload.get("employee_id"),
                    payload.get("employee_name"),
                    payload.get("department"),
                    payload.get("manager_id"),
                    payload.get("status") or "ACTIVE",
                ),
            )
            self.send_json(201, response(True, employee, "Employee saved"))
            return

        if parsed.path == "/api/v1/productivity":
            session = require_roles(self, "Admin", "Manager", "Supervisor", "Agent")
            if not session:
                return
            payload = self.read_json()
            employee_id = payload.get("employee_id") or employee_scope(session)
            if session["user"]["role_name"] == "Agent" and employee_id != employee_scope(session):
                self.send_json(403, response(False, message="Access denied"))
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

        if parsed.path == "/api/v1/reports":
            session = require_roles(self, "Admin", "Manager", "Supervisor")
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

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/api/v1/health", "/agent/v1/health"):
            self.send_json(200, {"status": "ok", "database": "configured" if db_ready() else "not_configured"})
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

        if parsed.path == "/api/live-dashboard" or parsed.path == "/api/v1/dashboard":
            if not require_roles(self, "Admin", "Manager", "Supervisor"):
                return
            self.send_json(200, response(True, dashboard_payload()))
            return

        if parsed.path == "/api/v1/employees":
            session = require_roles(self, "Admin", "Manager", "Supervisor")
            if not session:
                return
            self.send_json(200, response(True, query(
                """
                SELECT employee_id, employee_name, department, manager_id, status, created_at
                FROM employees
                ORDER BY created_at DESC, employee_name
                """
            )))
            return

        if parsed.path == "/api/v1/attendance":
            session = require_roles(self, "Admin", "Manager", "Supervisor", "Agent")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            if session["user"]["role_name"] == "Agent":
                employee_id = employee_scope(session)
            if employee_id:
                data = query(
                    """
                    SELECT attendance_id, employee_id, attendance_date, status, worked_hours, created_at
                    FROM attendance
                    WHERE employee_id = %s
                    ORDER BY attendance_date DESC
                    """,
                    (employee_id,),
                )
            else:
                data = query(
                    """
                    SELECT attendance_id, employee_id, attendance_date, status, worked_hours, created_at
                    FROM attendance
                    ORDER BY attendance_date DESC
                    """
                )
            self.send_json(200, response(True, data))
            return

        if parsed.path == "/api/v1/productivity":
            session = require_roles(self, "Admin", "Manager", "Supervisor", "Agent")
            if not session:
                return
            params = urllib.parse.parse_qs(parsed.query)
            employee_id = params.get("employee_id", [None])[0]
            if session["user"]["role_name"] == "Agent":
                employee_id = employee_scope(session)
            if employee_id:
                data = query(
                    """
                    SELECT productivity_id, employee_id, productive_hours, non_productive_hours, productivity_score, report_date
                    FROM productivity
                    WHERE employee_id = %s
                    ORDER BY report_date DESC
                    """,
                    (employee_id,),
                )
            else:
                data = query(
                    """
                    SELECT productivity_id, employee_id, productive_hours, non_productive_hours, productivity_score, report_date
                    FROM productivity
                    ORDER BY report_date DESC
                    """
                )
            self.send_json(200, response(True, data))
            return

        if parsed.path == "/api/v1/reports":
            if not require_roles(self, "Admin", "Manager", "Supervisor"):
                return
            self.send_json(200, response(True, query(
                """
                SELECT report_id, report_name, report_type, generated_at
                FROM reports
                ORDER BY generated_at DESC
                """
            )))
            return

        if parsed.path == "/agent/v1/profile":
            session = require_roles(self, "Agent")
            if not session:
                return
            employee_id = employee_scope(session)
            employee = query_one(
                """
                SELECT employee_id, employee_name, department, manager_id, status, created_at
                FROM employees
                WHERE employee_id = %s
                """,
                (employee_id,),
            )
            self.send_json(200, response(True, employee or {}))
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
