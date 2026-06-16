from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from .config import get_settings


ROOT = Path(__file__).resolve().parents[2]


def connect():
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    return psycopg.connect(settings.database_url, row_factory=dict_row)


@contextmanager
def cursor():
    with connect() as connection:
        with connection.cursor() as cur:
            yield cur


def query(sql: str, params: tuple = ()):
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql: str, params: tuple = ()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()):
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def ping_database() -> dict:
    row = query_one(
        """
        SELECT current_database() AS database_name,
               current_user AS database_user,
               version() AS version
        """
    )
    return row or {}


def apply_migrations() -> list[str]:
    applied = []
    migrations_dir = ROOT.parent / "database" / "migrations"
    with connect() as connection:
        with connection.cursor() as cur:
            for path in sorted(migrations_dir.glob("*.sql")):
                cur.execute(path.read_text(encoding="utf-8"))
                applied.append(path.name)
    return applied


def verify_schema() -> dict:
    required_tables = (
        "roles",
        "users",
        "employees",
        "agent_status",
        "workstation_events",
        "productivity_daily",
        "audit_log",
    )
    rows = query(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        """,
        (list(required_tables),),
    )
    present_tables = {row["table_name"] for row in rows}
    missing_tables = [table for table in required_tables if table not in present_tables]
    index_rows = query(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname = ANY(%s)
        """,
        (
            [
                "idx_workstation_events_employee_time",
                "idx_workstation_events_type_time",
                "idx_agent_status_activity",
                "idx_productivity_daily_date",
                "idx_employees_manager",
            ],
        ),
    )
    present_indexes = {row["indexname"] for row in index_rows}
    return {
        "missing_tables": missing_tables,
        "present_tables": sorted(present_tables),
        "present_indexes": sorted(present_indexes),
    }
