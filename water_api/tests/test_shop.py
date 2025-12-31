"""Tests for shop endpoints."""

import pytest
from decimal import Decimal

from app.models import Game, Entitlement


@pytest.fixture
def sample_game(db) -> Game:
    """Create a sample game."""
    game = Game(
        name="Test Game",
        slug="test-game",
        description="A test game",
        price=Decimal("19.99"),
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@pytest.fixture
def owned_game(db, test_user) -> Game:
    """Create a game that test_user owns."""
    game = Game(
        name="Owned Game",
        slug="owned-game",
        description="A game the user owns",
        price=Decimal("9.99"),
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    
    entitlement = Entitlement(user_id=test_user.id, game_id=game.id)
    db.add(entitlement)
    db.commit()
    
    return game


class TestStoreList:
    """Tests for GET /shop/"""

    def test_list_store_empty(self, client, auth_headers):
        """Test listing empty store."""
        response = client.get("/shop/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_store_with_games(self, client, auth_headers, sample_game):
        """Test listing store with games."""
        response = client.get("/shop/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Game"
        assert data[0]["owned"] is False

    def test_list_store_shows_owned_status(self, client, auth_headers, owned_game, sample_game):
        """Test that owned games are marked as owned."""
        response = client.get("/shop/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        owned = next(g for g in data if g["slug"] == "owned-game")
        not_owned = next(g for g in data if g["slug"] == "test-game")
        
        assert owned["owned"] is True
        assert not_owned["owned"] is False

    def test_list_store_unauthenticated(self, client):
        """Test that unauthenticated requests fail."""
        response = client.get("/shop/")
        assert response.status_code == 401


class TestPurchase:
    """Tests for POST /shop/purchase/{game_id}"""

    def test_purchase_success(self, client, auth_headers, sample_game, db):
        """Test successful purchase."""
        response = client.post(
            f"/shop/purchase/{sample_game.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == sample_game.id
        assert data["game_name"] == "Test Game"
        assert "Successfully purchased" in data["message"]

    def test_purchase_creates_entitlement(self, client, auth_headers, sample_game, db, test_user):
        """Test that purchase creates entitlement record."""
        client.post(f"/shop/purchase/{sample_game.id}", headers=auth_headers)
        
        entitlement = db.query(Entitlement).filter_by(
            user_id=test_user.id,
            game_id=sample_game.id,
        ).first()
        assert entitlement is not None

    def test_purchase_duplicate_fails(self, client, auth_headers, owned_game):
        """Test that buying already owned game fails."""
        response = client.post(
            f"/shop/purchase/{owned_game.id}",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "already own" in response.json()["detail"]

    def test_purchase_nonexistent_game(self, client, auth_headers):
        """Test purchasing nonexistent game fails."""
        response = client.post(
            "/shop/purchase/9999",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_purchase_unauthenticated(self, client, sample_game):
        """Test that unauthenticated purchase fails."""
        response = client.post(f"/shop/purchase/{sample_game.id}")
        assert response.status_code == 401
