import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-please")
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
ACCESS_EXPIRES_SECONDS = int(os.getenv("ACCESS_EXPIRES_SECONDS", "900"))
REFRESH_EXPIRES_SECONDS = int(os.getenv("REFRESH_EXPIRES_SECONDS", "604800"))

security_scheme = HTTPBearer(auto_error=False)

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"])


def make_jwt(sub: str, expires_seconds: int, **claims: Any) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
        **claims,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def parse_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(security_scheme), db: Session = Depends(get_db)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing credentials")
    data = parse_jwt(creds.credentials)
    uid = int(data["sub"])
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
