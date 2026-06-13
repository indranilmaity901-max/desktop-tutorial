from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from xml.sax.saxutils import escape
from db import (
    DatabaseConfigError,
    DatabaseError,
    DatabaseIntegrityError,
    execute,
    execute_many,
    row,
    rows,
    scalar,
)
import io
import json
import mimetypes
import os
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parent


def latest_metric_date():
    return scalar("SELECT MAX(metric_date) FROM productivity_logs", default="2026-06-05")


def dashboard_payload():
    metric_date = latest_metric_date()
    productivity_score = round(float(scalar(
        "SELECT AVG(productive_percentage) FROM productivity_logs WHERE metric_date = ?",
        (metric_date,),
        0,
    )))
    active_users = int(scalar("SELECT COUNT(*) FROM employees WHERE status = 'ACTIVE'"))
    attendance_total = int(scalar(
        "SELECT COUNT(*) FROM attendance_logs WHERE attendance_date = ?",
        (metric_date,),
        0,
    ))
    attendance_present = int(scalar(
        """
        SELECT COUNT(*)
        FROM attendance_logs
        WHERE attendance_date = ?
          AND attendance_status IN ('PRESENT', 'PARTIAL')
        """,
        (metric_date,),
        0,
    ))
    compliance_score = round((attendance_present / attendance_total) * 100) if attendance_total else 0
    conflicts_count = int(scalar("SELECT COUNT(*) FROM conflicts"))
    productive_minutes = int(scalar(
        "SELECT SUM(productive_minutes) FROM productivity_logs WHERE metric_date = ?",
        (metric_date,),
        0,
    ))
    non_productive_minutes = int(scalar(
        "SELECT SUM(non_productive_minutes) FROM productivity_logs WHERE metric_date = ?",
        (metric_date,),
        0,
    ))
    worked_minutes = int(scalar(
        "SELECT SUM(worked_minutes) FROM attendance_logs WHERE attendance_date = ?",
        (metric_date,),
        0,
    ))
    absent_count = int(scalar(
        "SELECT COUNT(*) FROM attendance_logs WHERE attendance_date = ? AND attendance_status = 'ABSENT'",
        (metric_date,),
        0,
    ))
    partial_count = int(scalar(
        "SELECT COUNT(*) FROM attendance_logs WHERE attendance_date = ? AND attendance_status = 'PARTIAL'",
        (metric_date,),
        0,
    ))

    metrics = [
        {"key": "productivity", "label": "Productivity", "value": f"{productivity_score}%", "trend": "30D live", "tone": "positive", "href": "#productivity"},
        {"key": "compliance", "label": "Compliance", "value": f"{compliance_score}%", "trend": "Attendance", "tone": "positive", "href": "#attendance"},
        {"key": "confidence", "label": "Confidence", "value": "96%", "trend": "Seeded", "tone": "neutral", "href": "#confidence"},
        {"key": "activeUsers", "label": "Active Users", "value": str(active_users), "trend": "SQL", "tone": "positive", "href": "#employees"},
        {"key": "conflicts", "label": "Conflicts", "value": str(conflicts_count), "trend": "Open", "tone": "negative", "href": "#conflicts"},
    ]
    evidence = {
        "productivity": [
            {"label": "Productive hrs", "value": f"{productive_minutes / 60:.1f}"},
            {"label": "Non-productive hrs", "value": f"{non_productive_minutes / 60:.1f}"},
            {"label": "Date", "value": metric_date},
        ],
        "compliance": [
            {"label": "Present/partial", "value": str(attendance_present)},
            {"label": "Absent", "value": str(absent_count)},
            {"label": "Partial", "value": str(partial_count)},
        ],
        "confidence": [
            {"label": "Attendance rows", "value": str(attendance_total)},
            {"label": "Productivity rows", "value": str(attendance_total)},
            {"label": "Source", "value": "SQL"},
        ],
        "activeUsers": [
            {"label": "Employees", "value": str(active_users)},
            {"label": "Worked hrs", "value": f"{worked_minutes / 60:.1f}"},
            {"label": "Window", "value": "30D"},
        ],
        "conflicts": [
            {"label": "Seed conflicts", "value": str(conflicts_count)},
            {"label": "Rules", "value": "Static"},
            {"label": "Queue", "value": "Prototype"},
        ],
    }

    readiness = rows("SELECT * FROM enterprise_readiness ORDER BY display_order")
    readiness_items = rows("SELECT * FROM enterprise_readiness_items ORDER BY readiness_key, display_order")
    items = {}
    for item in readiness_items:
        items.setdefault(item["readiness_key"], []).append(item["item"])

    agent_status = rows("SELECT * FROM workstation_agent_status LIMIT 1")[0]

    return {
        "metrics": [
            {
                "key": item["key"],
                "label": item["label"],
                "value": item["value"],
                "trend": item["trend"],
                "tone": item["tone"],
                "href": item["href"],
            }
            for item in metrics
        ],
        "evidenceBreakdown": evidence,
        "productivityTrend": [
            {"label": item["label"], "value": item["value"]}
            for item in rows("""
                SELECT
                  substr(metric_date, 9, 2) AS label,
                  ROUND(AVG(productive_percentage))::integer AS value
                FROM productivity_logs
                GROUP BY metric_date
                ORDER BY metric_date DESC
                LIMIT 10
            """)[::-1]
        ],
        "conflicts": [
            {
                "employee": item["employee"],
                "initials": item["initials"],
                "type": item["conflict_type"],
                "severity": item["severity"],
                "duration": item["duration"],
                "confidence": item["confidence"],
                "status": item["status"],
            }
            for item in rows("SELECT * FROM conflicts ORDER BY display_order")
        ],
        "alerts": [
            {
                "title": item["title"],
                "detail": item["detail"],
                "priority": item["priority"],
                "icon": item["icon"],
            }
            for item in rows("SELECT * FROM alerts ORDER BY display_order")
        ],
        "workstationAgent": {
            "service": {
                "name": agent_status["service_name"],
                "displayName": agent_status["display_name"],
                "version": agent_status["version"],
                "status": agent_status["status"],
                "heartbeat": agent_status["heartbeat"],
                "cpu": agent_status["cpu"],
                "memory": agent_status["memory"],
                "disk": agent_status["disk"],
            },
            "events": [item["event_type"] for item in rows("SELECT event_type FROM workstation_agent_events ORDER BY display_order")],
            "safeguards": [item["label"] for item in rows("SELECT label FROM workstation_agent_safeguards ORDER BY display_order")],
            "transport": rows("SELECT label, value FROM workstation_agent_transport ORDER BY display_order"),
            "buffer": rows("SELECT label, value FROM workstation_agent_buffer ORDER BY display_order"),
            "deployment": [item["label"] for item in rows("SELECT label FROM workstation_agent_deployment ORDER BY display_order")],
            "tamperSignals": [item["label"] for item in rows("SELECT label FROM workstation_agent_tamper ORDER BY display_order")],
        },
        "enterpriseReadinessSummary": rows("SELECT score, status, decision, blockers, next_gate AS nextGate FROM enterprise_readiness_summary LIMIT 1")[0],
        "enterpriseReadiness": [
            {
                "title": item["title"],
                "icon": item["icon"],
                "status": item["status"],
                "tone": item["tone"],
                "owner": item["owner"],
                "evidence": item["evidence"],
                "gap": item["gap"],
                "items": items.get(item["readiness_key"], []),
            }
            for item in readiness
        ],
        "explainabilityTrust": rows("SELECT label, value, target FROM explainability_trust ORDER BY display_order"),
        "stateCorrelation": rows("SELECT source, state, confidence FROM state_correlation ORDER BY display_order"),
    }


def report_rows(report_type, metric_date):
    if report_type == "attendance-summary":
        return {
            "title": "Attendance Summary",
            "filename": f"wpacs-attendance-summary-{metric_date}",
            "columns": ["Metric Date", "Logged Employees", "Present", "Partial", "Absent", "Leave", "Worked Hours"],
            "rows": rows(
                """
                SELECT
                  ? AS metric_date,
                  COUNT(*) AS logged_employees,
                  SUM(CASE WHEN attendance_status = 'PRESENT' THEN 1 ELSE 0 END) AS present,
                  SUM(CASE WHEN attendance_status = 'PARTIAL' THEN 1 ELSE 0 END) AS partial,
                  SUM(CASE WHEN attendance_status = 'ABSENT' THEN 1 ELSE 0 END) AS absent,
                  SUM(CASE WHEN attendance_status = 'LEAVE' THEN 1 ELSE 0 END) AS leave_count,
                  ROUND((COALESCE(SUM(worked_minutes), 0) / 60.0)::numeric, 2)::float AS worked_hours
                FROM attendance_logs
                WHERE attendance_date = ?
                """,
                (metric_date, metric_date),
            ),
        }

    return {
        "title": "Daily Productive Report",
        "filename": f"wpacs-daily-productive-report-{metric_date}",
        "columns": ["Metric Date", "Employee ID", "Employee Name", "Department", "Productive Hours", "Non-Productive Hours", "Productive %"],
        "rows": rows(
            """
            SELECT
              p.metric_date,
              p.employee_id,
              e.employee_name,
              e.department,
              ROUND((p.productive_minutes / 60.0)::numeric, 2)::float AS productive_hours,
              ROUND((p.non_productive_minutes / 60.0)::numeric, 2)::float AS non_productive_hours,
              p.productive_percentage
            FROM productivity_logs p
            JOIN employees e ON e.employee_id = p.employee_id
            WHERE p.metric_date = ?
            ORDER BY p.productive_percentage DESC, e.employee_name
            """,
            (metric_date,),
        ),
    }


def build_xlsx(report):
    rows_for_sheet = [report["columns"]] + [
        [str(row.get(column_key(column), "")) for column in report["columns"]]
        for row in report["rows"]
    ]

    sheet_rows = []
    for row_index, row_values in enumerate(rows_for_sheet, start=1):
        cells = []
        for column_index, value in enumerate(row_values, start=1):
            cell_ref = f"{xlsx_column(column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""")
        package.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        package.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets>
</workbook>""")
        package.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""")
        package.writestr("xl/worksheets/sheet1.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""")

    return output.getvalue()


def build_pdf(report):
    lines = [report["title"], "", " | ".join(report["columns"])]
    for row in report["rows"]:
        lines.append(" | ".join(str(row.get(column_key(column), "")) for column in report["columns"]))
    content_lines = []
    y = 760
    for line in lines[:32]:
        safe_line = str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 9 Tf 42 {y} Td ({safe_line}) Tj ET")
        y -= 18
    stream = "\n".join(content_lines)
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('utf-8'))} >> stream\n{stream}\nendstream endobj",
    ]
    pdf = "%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf.encode("utf-8")))
        pdf += obj + "\n"
    xref = len(pdf.encode("utf-8"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    return pdf.encode("utf-8")


def xlsx_column(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def column_key(label):
    if label == "Avg Productive %":
        return "average_productive_percentage"
    if label == "Leave":
        return "leave_count"
    return label.lower().replace(" %", "_percentage").replace(" ", "_").replace("-", "_")


class Handler(SimpleHTTPRequestHandler):
    def host_name(self):
        return self.headers.get("Host", "").split(":", 1)[0].lower()

    def is_agent_host(self):
        return self.host_name() == "agent.wpacs.com"

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def health_payload(self, surface):
        employee_count = scalar("SELECT COUNT(*) FROM employees")
        return {
            "success": True,
            "surface": surface,
            "api": "HEALTHY",
            "database": "HEALTHY",
            "database_engine": "postgresql",
            "employee_count": employee_count,
            "host": self.host_name() or "unknown",
        }

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/agent/v1/events":
            payload = self.read_json_body()
            agent_id = payload.get("agent_id") or payload.get("workstation_id") or "unknown"
            events = payload.get("events") if isinstance(payload.get("events"), list) else [payload]
            event_rows = [
                (
                    agent_id,
                    event.get("type") or event.get("event_type") or "UNKNOWN",
                    event.get("occurred_at") or event.get("timestamp"),
                    json.dumps(event),
                )
                for event in events
                if isinstance(event, dict)
            ]
            if event_rows:
                execute_many(
                    """
                    INSERT INTO agent_events (
                      agent_id,
                      event_type,
                      occurred_at,
                      payload
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    event_rows,
                )
            self.send_json(202, {
                "success": True,
                "data": {
                    "received": True,
                    "agent_id": agent_id,
                    "event_count": len(event_rows),
                },
                "message": "Agent event payload accepted",
                "errors": [],
            })
            return

        if parsed.path == "/api/v1/auth/login":
            payload = self.read_json_body()
            role_name = payload.get("role_name", "")
            username = payload.get("username", "")
            password_hash = payload.get("password_hash", "")

            user = row(
                """
                SELECT user_id, username, status, created_date
                FROM app_users
                WHERE username = ?
                  AND password_hash = ?
                """,
                (username, password_hash),
            )
            role = row("SELECT role_id, role_name FROM app_roles WHERE role_name = ?", (role_name,))

            if not role:
                body = json.dumps({
                    "success": False,
                    "data": {},
                    "message": "Role is required",
                    "errors": [{"field": "role_name", "error": "Invalid role"}],
                }).encode("utf-8")
                self.send_response(400)
            elif not user:
                body = json.dumps({
                    "success": False,
                    "data": {},
                    "message": "Invalid username or password hash",
                    "errors": [{"field": "credentials", "error": "Invalid"}],
                }).encode("utf-8")
                self.send_response(401)
            elif user["status"] != "ACTIVE":
                body = json.dumps({
                    "success": False,
                    "data": {},
                    "message": "User is not active",
                    "errors": [{"field": "status", "error": user["status"]}],
                }).encode("utf-8")
                self.send_response(403)
            else:
                body = json.dumps({
                    "success": True,
                    "data": {**user, **role},
                    "message": "Login successful",
                    "errors": [],
                }).encode("utf-8")
                self.send_response(200)

            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/employees":
            payload = self.read_json_body()
            required = ["employee_id", "employee_name", "department", "manager_id", "status"]
            missing = [field for field in required if not payload.get(field)]

            if missing:
                body = json.dumps({
                    "success": False,
                    "data": {},
                    "message": "Validation Failed",
                    "errors": [{"field": field, "error": "Required"} for field in missing],
                }).encode("utf-8")
                self.send_response(422)
            else:
                try:
                    manager = row("SELECT manager_id FROM managers WHERE manager_id = ?", (payload["manager_id"],))

                    if not manager:
                        body = json.dumps({
                            "success": False,
                            "data": {},
                            "message": "Manager not found",
                            "errors": [{"field": "manager_id", "error": "Not found"}],
                        }).encode("utf-8")
                        self.send_response(404)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return

                    execute(
                        """
                        INSERT INTO employees (
                          employee_id,
                          employee_name,
                          department,
                          manager_id,
                          status
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            payload["employee_id"],
                            payload["employee_name"],
                            payload["department"],
                            payload["manager_id"],
                            payload["status"],
                        ),
                    )
                    body = json.dumps({
                        "success": True,
                        "data": {
                            "employee_id": payload["employee_id"],
                            "employee_name": payload["employee_name"],
                            "department": payload["department"],
                            "manager_id": payload["manager_id"],
                            "status": payload["status"],
                        },
                        "message": "Employee created successfully",
                        "errors": [],
                    }).encode("utf-8")
                    self.send_response(201)
                except DatabaseIntegrityError:
                    body = json.dumps({
                        "success": False,
                        "data": {},
                        "message": "Employee already exists",
                        "errors": [{"field": "employee_id", "error": "Duplicate"}],
                    }).encode("utf-8")
                    self.send_response(409)

            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/attendance-logs":
            payload = self.read_json_body()
            required = ["employee_id", "attendance_date", "attendance_status", "worked_minutes"]
            missing = [field for field in required if payload.get(field) in (None, "")]

            if missing:
                self.send_json(422, {
                    "success": False,
                    "data": {},
                    "message": "Validation Failed",
                    "errors": [{"field": field, "error": "Required"} for field in missing],
                })
                return

            try:
                worked_minutes = int(payload["worked_minutes"])
            except ValueError:
                self.send_json(422, {
                    "success": False,
                    "data": {},
                    "message": "Worked minutes must be a valid number",
                    "errors": [{"field": "worked_minutes", "error": "Invalid number"}],
                })
                return

            attendance_date = payload["attendance_date"]
            attendance_id = payload.get("attendance_id") or f"ATT-{payload['employee_id']}-{attendance_date}"
            scheduled_minutes = int(payload.get("scheduled_minutes") or 480)
            marked_by_role = payload.get("marked_by_role") or "Admin"
            marked_by_user = payload.get("marked_by_user") or "admin"

            try:
                employee = row("SELECT employee_id FROM employees WHERE employee_id = ?", (payload["employee_id"],))

                if not employee:
                    self.send_json(404, {
                        "success": False,
                        "data": {},
                        "message": "Employee not found",
                        "errors": [{"field": "employee_id", "error": "Not found"}],
                    })
                    return

                execute(
                    """
                    INSERT INTO attendance_logs (
                      attendance_id,
                      employee_id,
                      attendance_date,
                      attendance_status,
                      scheduled_minutes,
                      worked_minutes,
                      marked_by_role,
                      marked_by_user,
                      created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(attendance_id) DO UPDATE SET
                      employee_id = excluded.employee_id,
                      attendance_date = excluded.attendance_date,
                      attendance_status = excluded.attendance_status,
                      scheduled_minutes = excluded.scheduled_minutes,
                      worked_minutes = excluded.worked_minutes,
                      marked_by_role = excluded.marked_by_role,
                      marked_by_user = excluded.marked_by_user,
                      created_at = excluded.created_at
                    """,
                    (
                        attendance_id,
                        payload["employee_id"],
                        attendance_date,
                        payload["attendance_status"],
                        scheduled_minutes,
                        worked_minutes,
                        marked_by_role,
                        marked_by_user,
                        f"{attendance_date}T09:00:00Z",
                    ),
                )

                self.send_json(201, {
                    "success": True,
                    "data": {
                        "attendance_id": attendance_id,
                        "employee_id": payload["employee_id"],
                        "attendance_date": attendance_date,
                        "attendance_status": payload["attendance_status"],
                        "scheduled_minutes": scheduled_minutes,
                        "worked_minutes": worked_minutes,
                        "marked_by_role": marked_by_role,
                        "marked_by_user": marked_by_user,
                    },
                    "message": "Attendance log saved successfully",
                    "errors": [],
                })
                return
            except DatabaseIntegrityError:
                self.send_json(409, {
                    "success": False,
                    "data": {},
                    "message": "Attendance log conflict",
                    "errors": [{"field": "attendance_id", "error": "Duplicate"}],
                })
                return

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/v1/employees/"):
            employee_id = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
            existing = row("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,))

            if not existing:
                self.send_json(404, {
                    "success": False,
                    "data": {},
                    "message": "Employee not found",
                    "errors": [{"field": "employee_id", "error": "Not found"}],
                })
                return

            execute("DELETE FROM productivity_logs WHERE employee_id = ?", (employee_id,))
            execute("DELETE FROM attendance_logs WHERE employee_id = ?", (employee_id,))
            execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))

            self.send_json(200, {
                "success": True,
                "data": {"employee_id": employee_id},
                "message": "Employee deleted successfully",
                "errors": [],
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/api/health", "/api/v1/health", "/agent/v1/health"):
            surface = "agent" if parsed.path.startswith("/agent/") or self.is_agent_host() else "dashboard"
            try:
                self.send_json(200, self.health_payload(surface))
            except (DatabaseConfigError, DatabaseError) as error:
                self.send_json(503, {
                    "success": False,
                    "surface": surface,
                    "api": "HEALTHY",
                    "database": "UNHEALTHY",
                    "database_engine": "postgresql",
                    "message": str(error),
                    "host": self.host_name() or "unknown",
                })
            return

        if self.is_agent_host() and not parsed.path.startswith("/agent/"):
            self.send_json(200, {
                "success": True,
                "surface": "agent",
                "message": "WPACS agent API service",
                "endpoints": ["/agent/v1/health", "/agent/v1/events"],
            })
            return

        if parsed.path == "/api/live-dashboard":
            body = json.dumps(dashboard_payload()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/users":
            body = json.dumps({
                "success": True,
                "data": rows("SELECT user_id, username, status, created_date FROM app_users ORDER BY created_date DESC, username"),
                "message": "Users retrieved successfully",
                "errors": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/roles":
            body = json.dumps({
                "success": True,
                "data": rows("SELECT role_id, role_name FROM app_roles ORDER BY role_name"),
                "message": "Roles retrieved successfully",
                "errors": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/managers":
            body = json.dumps({
                "success": True,
                "data": rows("SELECT manager_id, manager_name FROM managers ORDER BY manager_id"),
                "message": "Managers retrieved successfully",
                "errors": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/employees":
            body = json.dumps({
                "success": True,
                "data": rows("""
                    SELECT
                      e.employee_id,
                      e.employee_name,
                      e.department,
                      e.manager_id,
                      m.manager_name,
                      e.status
                    FROM employees e
                    LEFT JOIN managers m ON m.manager_id = e.manager_id
                    ORDER BY e.employee_name
                """),
                "message": "Employees retrieved successfully",
                "errors": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/attendance-logs":
            query = urllib.parse.parse_qs(parsed.query)
            metric_date = query.get("metric_date", [""])[0]
            where = "WHERE a.attendance_date = ?" if metric_date else ""
            parameters = (metric_date,) if metric_date else ()
            body = json.dumps({
                "success": True,
                "data": rows(f"""
                    SELECT
                      a.attendance_id,
                      p.productivity_id,
                      a.employee_id,
                      a.attendance_status,
                      a.scheduled_minutes,
                      a.worked_minutes,
                      COALESCE(p.productive_minutes, 0) AS productive_minutes,
                      COALESCE(p.non_productive_minutes, 0) AS non_productive_minutes,
                      COALESCE(p.productive_percentage, 0) AS productive_percentage,
                      a.attendance_date AS metric_date
                    FROM attendance_logs a
                    LEFT JOIN productivity_logs p
                      ON p.employee_id = a.employee_id
                     AND p.metric_date = a.attendance_date
                    {where}
                    ORDER BY a.attendance_date DESC, a.employee_id
                """, parameters),
                "message": "Attendance logs retrieved successfully",
                "errors": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/v1/reports/attendance-daily":
            query = urllib.parse.parse_qs(parsed.query)
            metric_date = query.get("metric_date", [latest_metric_date()])[0]
            summary = row(
                """
                SELECT
                  COUNT(*) AS logged_employees,
                  COALESCE(SUM(p.productive_minutes), 0) AS productive_minutes,
                  COALESCE(SUM(p.non_productive_minutes), 0) AS non_productive_minutes,
                  COALESCE(ROUND(AVG(p.productive_percentage)::numeric, 2), 0)::float AS average_productive_percentage
                FROM attendance_logs a
                LEFT JOIN productivity_logs p
                  ON p.employee_id = a.employee_id
                 AND p.metric_date = a.attendance_date
                WHERE a.attendance_date = ?
                """,
                (metric_date,),
            )

            self.send_json(200, {
                "success": True,
                "data": {"metric_date": metric_date, **summary},
                "message": "Daily attendance report retrieved successfully",
                "errors": [],
            })
            return

        if parsed.path == "/api/v1/reports/productivity-daily":
            query = urllib.parse.parse_qs(parsed.query)
            metric_date = query.get("metric_date", [latest_metric_date()])[0]
            items = rows(
                """
                SELECT
                  p.productivity_id,
                  p.employee_id,
                  e.employee_name,
                  e.department,
                  p.productive_minutes,
                  p.non_productive_minutes,
                  p.productive_percentage,
                  p.metric_date
                FROM productivity_logs p
                JOIN employees e ON e.employee_id = p.employee_id
                WHERE p.metric_date = ?
                ORDER BY p.productive_percentage DESC, e.employee_name
                """,
                (metric_date,),
            )

            self.send_json(200, {
                "success": True,
                "data": {"metric_date": metric_date, "items": items},
                "message": "Daily productivity report retrieved successfully",
                "errors": [],
            })
            return

        if parsed.path == "/api/v1/reports/download":
            query = urllib.parse.parse_qs(parsed.query)
            report_type = query.get("report_type", ["daily-productive"])[0]
            metric_date = query.get("metric_date", [latest_metric_date()])[0]
            file_format = query.get("format", ["xlsx"])[0]
            report = report_rows(report_type, metric_date)

            if file_format == "pdf":
                content = build_pdf(report)
                filename = f"{report['filename']}.pdf"
                content_type = "application/pdf"
            else:
                content = build_xlsx(report)
                filename = f"{report['filename']}.xlsx"
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        return super().do_GET()

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        target = parsed.path
        if target == "/":
            target = "/index.html"
        full_path = ROOT / "public" / target.lstrip("/")
        if full_path.exists():
            return str(full_path)
        src_path = ROOT / target.lstrip("/")
        if src_path.exists():
            return str(src_path)
        return str(ROOT / "public" / "index.html")


mimetypes.add_type("text/javascript", ".js")

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "4190"))
    public_url = os.environ.get("PUBLIC_URL", f"http://{host}:{port}")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"WPACS SQL live dashboard running at {public_url}")
    server.serve_forever()
