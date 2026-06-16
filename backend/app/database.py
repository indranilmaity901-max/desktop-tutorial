from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import get_settings


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
