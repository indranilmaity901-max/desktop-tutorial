import hashlib
import secrets

from app.config import get_settings
from app.database import query_one


def hash_password(password: str) -> str:
    iterations = 260000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def role_id(role_name: str):
    row = query_one("SELECT role_id FROM roles WHERE UPPER(role_name) = %s", (role_name.upper(),))
    if not row:
        raise RuntimeError(f"Required role missing: {role_name}")
    return row["role_id"]


def upsert_user(username: str, password: str, role_name: str, employee_id: str | None = None):
    if not username or not password:
        return None
    return query_one(
        """
        INSERT INTO users (username, password_hash, role_id, employee_id, active)
        VALUES (%s, %s, %s, %s, TRUE)
        ON CONFLICT (username) DO UPDATE SET
          password_hash = EXCLUDED.password_hash,
          role_id = EXCLUDED.role_id,
          employee_id = EXCLUDED.employee_id,
          active = TRUE
        RETURNING user_id, username, employee_id
        """,
        (username, hash_password(password), role_id(role_name), employee_id),
    )


def seed_from_environment() -> dict:
    settings = get_settings()
    seeded = {}
    admin = upsert_user(settings.admin_username, settings.admin_password, "ADMIN")
    if admin:
        seeded["admin"] = admin["username"]
    manager = upsert_user(settings.manager_username, settings.manager_password, "MANAGER")
    if manager:
        seeded["manager"] = manager["username"]
    if settings.agent_username and settings.agent_password and settings.agent_employee_id:
        manager_id = str(manager["user_id"]) if manager else None
        query_one(
            """
            INSERT INTO employees (employee_id, employee_name, department, manager_id, status)
            VALUES (%s, %s, 'Operations', %s, 'ACTIVE')
            ON CONFLICT (employee_id) DO UPDATE SET
              employee_name = EXCLUDED.employee_name,
              manager_id = EXCLUDED.manager_id,
              status = 'ACTIVE'
            RETURNING employee_id
            """,
            (
                settings.agent_employee_id,
                settings.agent_employee_name or settings.agent_username,
                manager_id,
            ),
        )
        agent = upsert_user(settings.agent_username, settings.agent_password, "AGENT", settings.agent_employee_id)
        if agent:
            seeded["agent"] = agent["username"]
    return seeded
