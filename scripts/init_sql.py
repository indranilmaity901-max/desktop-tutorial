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

with psycopg.connect(DATABASE_URL) as connection:
    with connection.cursor() as cursor:
        cursor.execute(schema)
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
                ON CONFLICT (username) DO NOTHING
                """,
                (admin_username, hash_password(admin_password), role_id),
            )

print("Initialized WPACS PostgreSQL schema.")
