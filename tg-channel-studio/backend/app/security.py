"""Auth: password hashing, JWT (user + org), Fernet encryption for stored secrets."""
import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: int
    org_id: int
    email: str


def hash_password(password: str) -> str:
    # bcrypt operates on at most 72 bytes; truncate defensively.
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def create_token(user_id: int, org_id: int, email: str) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "org": org_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=s.jwt_ttl_hours),
    }
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def create_purpose_token(user_id: int, purpose: str, ttl_hours: int = 24) -> str:
    """Stateless signed token for email verification / password reset."""
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    }
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def verify_purpose_token(token: str, purpose: str) -> int | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return int(payload["sub"])


async def require_org(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return Principal(user_id=int(payload["sub"]), org_id=int(payload["org"]), email=payload["email"])
