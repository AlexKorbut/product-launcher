"""JWT auth (single admin) + Fernet encryption for stored secrets (bot tokens)."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def _fernet() -> Fernet:
    # Derive a stable Fernet key from SECRET_KEY so operators manage one secret.
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def create_token(email: str) -> str:
    s = get_settings()
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=s.jwt_ttl_hours),
    }
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def verify_credentials(email: str, password: str) -> bool:
    s = get_settings()
    return email == s.admin_email and password == s.admin_password


async def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload["sub"]
