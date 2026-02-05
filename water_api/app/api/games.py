import hashlib
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Build, Entitlement, Game, User
from app.security import current_user, require_admin
from app.storage import get_download_url, upload_build_fileobj

router = APIRouter()


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str = ""
    price: Decimal


class GameCreate(BaseModel):
    name: str
    slug: str
    description: str = ""
    price: Decimal = Decimal("0.00")


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


class BuildListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    sha256: str


@router.get("/{game_id}/builds", response_model=list[BuildListOut])
def list_builds(game_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    """List all builds for a game (requires entitlement)."""
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check entitlement
    entitlement = db.query(Entitlement).filter_by(user_id=user.id, game_id=game_id).first()
    if not entitlement:
        raise HTTPException(status_code=403, detail="No entitlement for this game")

    builds = db.query(Build).filter(Build.game_id == game_id).order_by(Build.id.desc()).all()
    return builds


# ============ Admin Endpoints ============


@router.post("/", response_model=GameOut, status_code=201)
def create_game(data: GameCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Create a new game (admin only)."""
    # Check if slug already exists
    existing = db.query(Game).filter(Game.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Game with this slug already exists")

    game = Game(
        name=data.name,
        slug=data.slug,
        description=data.description,
        price=data.price,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


class BuildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    version: str
    s3_key: str
    sha256: str


@router.post("/{game_id}/builds", response_model=BuildOut, status_code=201)
def upload_build(
    game_id: int,
    version: str,
    file: UploadFile,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Upload a new build for a game (admin only)."""
    # Verify game exists
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if version already exists
    existing = db.query(Build).filter(Build.game_id == game_id, Build.version == version).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Build version {version} already exists for this game")

    # Read file content and compute SHA256
    content = file.file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()

    # Reset file position for upload
    file.file.seek(0)

    # Upload to MinIO
    s3_key = upload_build_fileobj(file.file, game.slug, version)

    # Create build record
    build = Build(
        game_id=game_id,
        version=version,
        s3_key=s3_key,
        sha256=sha256_hash,
    )
    db.add(build)
    db.commit()
    db.refresh(build)

    return build
