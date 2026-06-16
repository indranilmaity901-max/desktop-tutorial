import hashlib
import secrets

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth.jwt import create_token
from app.database import query_one


router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str
    role: str


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return secrets.compare_digest(digest.hex(), expected)
    except ValueError:
        return False


@router.post("/login")
def login(payload: LoginIn):
    user = query_one(
        """
        SELECT u.user_id, u.username, u.password_hash, u.active, u.employee_id, UPPER(r.role_name) AS role
        FROM users u
        JOIN roles r ON r.role_id = u.role_id
        WHERE u.username = %s
        """,
        (payload.username,),
    )
    if not user or not user["active"] or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if user["role"] != payload.role.upper():
        raise HTTPException(status_code=403, detail="Selected role is not assigned to this user")
    claims = {
        "user_id": str(user["user_id"]),
        "username": user["username"],
        "role": user["role"],
        "employee_id": user["employee_id"],
    }
    return {
        "success": True,
        "data": {"access_token": create_token(claims), "token_type": "bearer", "user": claims},
        "message": "Login successful",
        "errors": [],
    }
