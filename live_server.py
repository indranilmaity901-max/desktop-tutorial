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
RBAC_ROLES = ("ADMIN", "MANAGER", "SUPERVISOR")


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


def dashboard_payload():
    totals = query_one(
        """
        SELECT
          COUNT(*) AS employees,
          ROUND(AVG(productivity_score)) AS productivity_score,
          COALESCE(SUM(productive_hours), 0) AS productive_hours,
          COALESCE(SUM(non_productive_hours), 0) AS non_productive_hours,
          COUNT(p.productivity_id) AS productivity_records
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
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            payload = self.read_json()
            employee_id = str(payload.get("employee_id", "")).strip()
            manager_id = str(payload.get("manager_id") or "").strip() or None
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
            if not employee_exists(employee_id):
                self.send_json(404, response(False, message="Employee not found"))
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
            if not require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR"):
                return
            self.send_json(200, response(True, dashboard_payload()))
            return

        if parsed.path == "/api/v1/employees":
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            self.send_json(200, response(True, query(
                """
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
                ORDER BY e.created_at DESC, e.employee_name
                """
            )))
            return

        if parsed.path == "/api/v1/employee-options":
            if not require_roles(self, "ADMIN", "MANAGER", "SUPERVISOR"):
                return
            self.send_json(200, response(True, query(
                """
                SELECT employee_id, employee_name, department, status
                FROM employees
                WHERE status = 'ACTIVE'
                ORDER BY employee_name
                """
            )))
            return

        if parsed.path == "/api/v1/managers":
            session = require_roles(self, "ADMIN", "MANAGER")
            if not session:
                return
            self.send_json(200, response(True, query(
                """
                SELECT u.user_id::text AS manager_id, u.username AS manager_name
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE UPPER(r.role_name) = 'MANAGER'
                  AND u.active = TRUE
                ORDER BY u.username
                """
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
                data = query(
                    """
                    SELECT a.attendance_id, a.employee_id, e.employee_name, a.attendance_date, a.status, a.worked_hours, a.created_at
                    FROM attendance a
                    JOIN employees e ON e.employee_id = a.employee_id
                    ORDER BY a.attendance_date DESC
                    """
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
                data = query(
                    """
                    SELECT p.productivity_id, p.employee_id, e.employee_name, p.productive_hours, p.non_productive_hours, p.productivity_score, p.report_date
                    FROM productivity p
                    JOIN employees e ON e.employee_id = p.employee_id
                    ORDER BY p.report_date DESC
                    """
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
