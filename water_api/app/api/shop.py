from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Entitlement, Game, User
from app.security import current_user

router = APIRouter()


class GameListItem(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    price: Decimal
    owned: bool

    class Config:
        from_attributes = True


class PurchaseOut(BaseModel):
    message: str
    game_id: int
    game_name: str


@router.get("/", response_model=list[GameListItem])
def list_store_games(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """List all games in the store with ownership status."""
    games = db.query(Game).all()
    
    # Get user's owned game IDs
    owned_ids = {e.game_id for e in db.query(Entitlement).filter_by(user_id=user.id).all()}
    
    return [
        GameListItem(
            id=g.id,
            name=g.name,
            slug=g.slug,
            description=g.description,
            price=g.price,
            owned=g.id in owned_ids,
        )
        for g in games
    ]


@router.post("/purchase/{game_id}", response_model=PurchaseOut)
def purchase_game(game_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """
    Purchase a game and create an entitlement.
    
    In a real system, this would integrate with a payment provider.
    For now, it just creates the entitlement directly.
    """
    # Check if game exists
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if user already owns this game
    existing = db.query(Entitlement).filter_by(user_id=user.id, game_id=game_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already own this game")

    # Create entitlement (in real app, this would happen after payment confirmation)
    entitlement = Entitlement(user_id=user.id, game_id=game_id)
    db.add(entitlement)
    db.commit()

    return PurchaseOut(
        message=f"Successfully purchased {game.name}!",
        game_id=game.id,
        game_name=game.name,
    )
