"""Tests for games endpoints."""

import pytest
from decimal import Decimal

from app.models import Game, Build, Entitlement


@pytest.fixture
def game_with_build(db, test_user) -> tuple[Game, Build]:
    """Create a game with a build that test_user owns."""
    game = Game(
        name="Test Game",
        slug="test-game",
        description="A test game",
        price=Decimal("19.99"),
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    
    build = Build(
        game_id=game.id,
        version="1.0",
        s3_key="games/test-game/1.0/game.zip",
        sha256="abc123",
    )
    db.add(build)
    
    entitlement = Entitlement(user_id=test_user.id, game_id=game.id)
    db.add(entitlement)
    db.commit()
    db.refresh(build)
    
    return game, build


@pytest.fixture
def unowned_game(db) -> Game:
    """Create a game that no one owns."""
    game = Game(
        name="Unowned Game",
        slug="unowned-game",
        description="Nobody owns this",
        price=Decimal("29.99"),
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


class TestListGames:
    """Tests for GET /games/"""

    def test_list_games_empty(self, client, auth_headers):
        """Test listing games when user owns none."""
        response = client.get("/games/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_games_owned(self, client, auth_headers, game_with_build):
        """Test listing owned games."""
        game, _ = game_with_build
        response = client.get("/games/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Game"
        assert data[0]["slug"] == "test-game"

    def test_list_games_excludes_unowned(self, client, auth_headers, game_with_build, unowned_game):
        """Test that unowned games are not listed."""
        response = client.get("/games/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["slug"] == "test-game"

    def test_list_games_unauthenticated(self, client):
        """Test that unauthenticated request fails."""
        response = client.get("/games/")
        assert response.status_code == 401


class TestCreateGame:
    """Tests for POST /games/ (admin only)"""

    def test_create_game_as_admin(self, client, admin_headers):
        """Test admin can create games."""
        response = client.post(
            "/games/",
            headers=admin_headers,
            json={
                "name": "New Game",
                "slug": "new-game",
                "description": "A new game",
                "price": "14.99",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Game"
        assert data["slug"] == "new-game"

    def test_create_game_as_user_fails(self, client, auth_headers):
        """Test regular user cannot create games."""
        response = client.post(
            "/games/",
            headers=auth_headers,
            json={
                "name": "New Game",
                "slug": "new-game",
                "description": "A new game",
                "price": "14.99",
            },
        )
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_create_game_duplicate_slug(self, client, admin_headers, game_with_build):
        """Test creating game with duplicate slug fails."""
        response = client.post(
            "/games/",
            headers=admin_headers,
            json={
                "name": "Another Game",
                "slug": "test-game",  # Already exists
                "description": "Should fail",
                "price": "9.99",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestAdminPermissions:
    """Tests for admin-only functionality."""

    def test_regular_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """Test that regular users get 403 on admin endpoints."""
        response = client.post(
            "/games/",
            headers=auth_headers,
            json={"name": "Game", "slug": "game", "price": "10"},
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_admin_endpoints(self, client):
        """Test that unauthenticated requests get 401."""
        response = client.post(
            "/games/",
            json={"name": "Game", "slug": "game", "price": "10"},
        )
        assert response.status_code == 401
