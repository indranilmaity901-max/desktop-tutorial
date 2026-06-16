from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json

from app.config import get_settings


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(payload: dict, minutes: int = 480) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is required")
    body = {
        **payload,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp()),
    }
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = _b64encode(json.dumps(body, separators=(",", ":"), default=str).encode())
    signing_input = f"{header}.{claims}".encode("ascii")
    signature = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{claims}.{_b64encode(signature)}"


def verify_token(token: str) -> dict:
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is required")
    header, claims, signature = token.split(".", 2)
    signing_input = f"{header}.{claims}".encode("ascii")
    expected = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64decode(signature), expected):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64decode(claims))
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Token expired")
    return payload
