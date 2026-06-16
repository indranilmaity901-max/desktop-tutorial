from fastapi import Depends, Header, HTTPException

from app.auth.jwt import verify_token
from app.database import query_one


def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = verify_token(authorization.removeprefix("Bearer ").strip())
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    return payload


def require_roles(*roles: str):
    allowed = {role.upper() for role in roles}

    def dependency(user=Depends(current_user)):
        if allowed and str(user.get("role", "")).upper() not in allowed:
            raise HTTPException(status_code=403, detail="Access denied")
        return user

    return dependency


def can_access_employee(user: dict, employee_id: str) -> bool:
    role = str(user.get("role", "")).upper()
    if role == "ADMIN":
        return True
    if role == "MANAGER":
        row = query_one(
            "SELECT employee_id FROM employees WHERE employee_id = %s AND manager_id = %s",
            (employee_id, str(user.get("user_id"))),
        )
        return bool(row)
    return str(user.get("employee_id") or "") == str(employee_id)
