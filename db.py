import os

from psycopg import connect
from psycopg.rows import dict_row


DATABASE_URL = os.environ.get("DATABASE_URL")


class DatabaseConfigError(RuntimeError):
    pass


class DatabaseIntegrityError(RuntimeError):
    pass


class DatabaseError(RuntimeError):
    pass


def require_database_url():
    if not DATABASE_URL:
        raise DatabaseConfigError("DATABASE_URL is required for the cloud PostgreSQL backend.")
    return DATABASE_URL


def prepare_query(query):
    return query.replace("?", "%s")


def connection():
    return connect(require_database_url(), row_factory=dict_row)


def rows(query, parameters=()):
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(prepare_query(query), parameters)
                return cursor.fetchall()
    except Exception as error:
        raise DatabaseError(str(error)) from error


def row(query, parameters=()):
    result = rows(query, parameters)
    return result[0] if result else None


def scalar(query, parameters=(), default=0):
    result = row(query, parameters)
    if not result:
        return default
    value = next(iter(result.values()))
    return value if value is not None else default


def execute(query, parameters=()):
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(prepare_query(query), parameters)
    except Exception as error:
        if error.__class__.__name__ in ("IntegrityError", "UniqueViolation", "ForeignKeyViolation"):
            raise DatabaseIntegrityError(str(error)) from error
        raise DatabaseError(str(error)) from error


def execute_many(query, parameter_rows):
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(prepare_query(query), parameter_rows)
    except Exception as error:
        if error.__class__.__name__ in ("IntegrityError", "UniqueViolation", "ForeignKeyViolation"):
            raise DatabaseIntegrityError(str(error)) from error
        raise DatabaseError(str(error)) from error


def execute_script(script):
    statements = [statement.strip() for statement in script.split(";") if statement.strip()]
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
    except Exception as error:
        raise DatabaseError(str(error)) from error
