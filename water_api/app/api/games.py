from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Build, Entitlement, Game
from app.security import current_user
from app.storage import get_download_url

router = APIRouter()


class GameOut(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal

    class Config:
        from_attributes = True


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int = 3600


@router.get("/", response_model=list[GameOut])
def list_games(user=Depends(current_user), db: Session = Depends(get_db)):
    games = (
        db.query(Game).join(Entitlement, Entitlement.game_id == Game.id).filter(Entitlement.user_id == user.id).all()
    )
    return games


@router.get("/builds/{build_id}/download", response_model=DownloadUrlOut)
def get_build_download(build_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    """Get presigned download URL for a game build"""
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    # Check entitlement
    entitlement = db.query(Entitlement).filter_by(user_id=user.id, game_id=build.game_id).first()
    if not entitlement:
        raise HTTPException(status_code=403, detail="No entitlement for this game")

    # Generate presigned URL
    download_url = get_download_url(build.s3_key, expires_in=3600)
    return DownloadUrlOut(url=download_url)
