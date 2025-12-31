"""Tests for authentication endpoints."""

import pytest


class TestRegister:
    """Tests for POST /auth/register"""

    def test_register_success(self, client):
        """Test successful registration."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "different",
                "email": "test@example.com",  # Same as test_user
                "password": "NewPass123",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with existing username fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",  # Same as test_user
                "email": "different@example.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_register_weak_password(self, client):
        """Test registration with weak password fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "weak",  # Too short, no uppercase, no digit
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_invalid_username(self, client):
        """Test registration with invalid username fails."""
        response = client.post(
            "/auth/register",
            json={
                "username": "ab",  # Too short
                "email": "new@example.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login"""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "Test1234"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "WrongPass123"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/auth/login",
            json={"username": "nobody", "password": "SomePass123"},
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestRefresh:
    """Tests for POST /auth/refresh"""

    def test_refresh_success(self, client, test_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "Test1234"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_fails(self, client, test_user):
        """Test that access token cannot be used as refresh token."""
        login_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "Test1234"},
        )
        access_token = login_response.json()["access_token"]

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token fails."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401
