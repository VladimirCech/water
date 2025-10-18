from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import ACCESS_EXPIRES_SECONDS, REFRESH_EXPIRES_SECONDS, make_jwt, verify_password

router = APIRouter()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokensOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = make_jwt(str(user.id), ACCESS_EXPIRES_SECONDS)
    refresh = make_jwt(str(user.id), REFRESH_EXPIRES_SECONDS, typ="refresh")
    return TokensOut(access_token=access, refresh_token=refresh)
