
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db import get_db
from app.models import Game, Entitlement
from app.security import current_user

router = APIRouter()

class GameOut(BaseModel):
    id: int
    name: str
    slug: str
    class Config:
        from_attributes = True

@router.get("/", response_model=list[GameOut])
def list_games(user = Depends(current_user), db: Session = Depends(get_db)):
    game_ids = [e.game_id for e in db.query(Entitlement).filter_by(user_id=user.id).all()]
    games = db.query(Game).filter(Game.id.in_(game_ids)).all() if game_ids else []
    return games
