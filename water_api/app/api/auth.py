import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import (
    ACCESS_EXPIRES_SECONDS,
    REFRESH_EXPIRES_SECONDS,
    hash_password,
    make_jwt,
    verify_password,
)

router = APIRouter()


class RegisterNewUser(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores and hyphens")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if v.islower() or v.isupper():
            raise ValueError("Password must contain both uppercase and lowercase letters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one letter")
        return v


class LoginIn(BaseModel):
    username: str
    password: str


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokensOut, status_code=201)
def register(data: RegisterNewUser, db: Session = Depends(get_db)):
    """Register a new user account."""
    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = db.query(User).filter(User.username == data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access = make_jwt(str(user.id), ACCESS_EXPIRES_SECONDS)
    refresh = make_jwt(str(user.id), REFRESH_EXPIRES_SECONDS, typ="refresh")
    return TokensOut(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokensOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    """Login with username and password."""
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = make_jwt(str(user.id), ACCESS_EXPIRES_SECONDS)
    refresh = make_jwt(str(user.id), REFRESH_EXPIRES_SECONDS, typ="refresh")
    return TokensOut(access_token=access, refresh_token=refresh)
