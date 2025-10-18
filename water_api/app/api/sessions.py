
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Session as GameSession, Build
from app.security import parse_jwt, current_user

router = APIRouter()

class AttestIn(BaseModel):
    token: str

class AttestOut(BaseModel):
    session_id: int

@router.post("/attest", response_model=AttestOut)
def attest(data: AttestIn, user = Depends(current_user), db: Session = Depends(get_db)):
    payload = parse_jwt(data.token)
    if payload.get("typ") != "launch":
        raise HTTPException(400, "Not a launch token")
    build_id = int(payload["build_id"])
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    s = GameSession(user_id=user.id, game_id=build.game_id, build_id=build.id)
    db.add(s)
    db.flush()
    return AttestOut(session_id=s.id)

class HeartbeatOut(BaseModel):
    ok: bool

@router.post("/{session_id}/heartbeat", response_model=HeartbeatOut)
def heartbeat(session_id: int, user = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(GameSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Session not found")
    s.last_heartbeat = datetime.utcnow()
    return HeartbeatOut(ok=True)
