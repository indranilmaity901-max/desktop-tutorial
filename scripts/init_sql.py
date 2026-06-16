from pathlib import Path
import hashlib
import os
import secrets

import psycopg


ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("DATABASE_URL")


def hash_password(password):
    iterations = 260000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is required for WPACS production initialization.")


schema = (ROOT / "sql" / "postgres_schema.sql").read_text(encoding="utf-8")
LEGACY_TABLES = (
    "alerts",
    "app_roles",
    "app_users",
    "attendance_logs",
    "conflicts",
    "enterprise_readiness",
    "enterprise_readiness_items",
    "enterprise_readiness_summary",
    "explainability_trust",
    "managers",
    "productivity_logs",
    "state_correlation",
    "workstation_agent_buffer",
    "workstation_agent_deployment",
    "workstation_agent_events",
    "workstation_agent_safeguards",
    "workstation_agent_status",
    "workstation_agent_tamper",
    "workstation_agent_transport",
)

with psycopg.connect(DATABASE_URL) as connection:
    with connection.cursor() as cursor:
        cursor.execute(schema)
        cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_id TEXT REFERENCES employees(employee_id)")
        cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
        for role_name in ("Admin", "Manager", "Supervisor", "Agent"):
            cursor.execute(
                "INSERT INTO roles (role_name) VALUES (%s) ON CONFLICT (role_name) DO NOTHING",
                (role_name,),
            )

        admin_username = os.environ.get("WPACS_ADMIN_USERNAME")
        admin_password = os.environ.get("WPACS_ADMIN_PASSWORD")
        if admin_username and admin_password:
            cursor.execute("SELECT role_id FROM roles WHERE role_name = 'Admin'")
            role_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role_id, active)
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE SET
                  password_hash = EXCLUDED.password_hash,
                  role_id = EXCLUDED.role_id,
                  active = TRUE
                """,
                (admin_username, hash_password(admin_password), role_id),
            )

        cursor.execute("SELECT to_regclass('public.attendance_logs')")
        if cursor.fetchone()[0]:
            cursor.execute("DELETE FROM attendance_logs WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        cursor.execute("SELECT to_regclass('public.productivity_logs')")
        if cursor.fetchone()[0]:
            cursor.execute("DELETE FROM productivity_logs WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        cursor.execute("DELETE FROM attendance WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        cursor.execute("DELETE FROM productivity WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        cursor.execute("DELETE FROM users WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        cursor.execute("DELETE FROM employees WHERE employee_id ~ '^EMP-[0-9]{3}$'")
        for table_name in LEGACY_TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

print("Initialized WPACS PostgreSQL schema and removed legacy prototype data.")
