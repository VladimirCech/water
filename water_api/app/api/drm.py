
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Build, Entitlement
from app.security import current_user, make_jwt

router = APIRouter()

class LaunchOut(BaseModel):
    token: str

@router.post("/launch/{build_id}", response_model=LaunchOut)
def launch(build_id: int, user = Depends(current_user), db: Session = Depends(get_db)):
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    ok = db.query(Entitlement).filter_by(user_id=user.id, game_id=build.game_id).first()
    if not ok:
        raise HTTPException(status_code=403, detail="No entitlement")
    token = make_jwt(str(user.id), 600, typ="launch", build_id=build_id)
    return LaunchOut(token=token)
