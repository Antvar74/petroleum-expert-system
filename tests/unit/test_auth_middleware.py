"""
Unit tests for API Key authentication middleware.
Tests dev mode (no API_KEY) and protected mode (API_KEY set).
"""
import pytest


class TestAuthDevMode:
    """When API_KEY is NOT set, all requests should pass."""

    def test_no_api_key_env_allows_all(self, client):
        """Without API_KEY env, requests without header should pass."""
        resp = client.get("/wells")
        assert resp.status_code == 200


class TestAuthProtectedMode:
    """When API_KEY IS set, requests must include correct X-API-Key header."""

    def test_rejects_missing_header(self, db_session, monkeypatch):
        """With API_KEY set, missing header should return 401."""
        monkeypatch.setenv("API_KEY", "test-secret-key-123")
        from fastapi.testclient import TestClient
        from api_main import app
        from models.database import get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Do NOT override verify_api_key — let it run with API_KEY set
        app.dependency_overrides.pop(
            __import__("middleware.auth", fromlist=["verify_api_key"]).verify_api_key,
            None,
        )
        with TestClient(app) as c:
            resp = c.get("/wells")
        app.dependency_overrides.clear()
        assert resp.status_code == 401

    def test_rejects_wrong_key(self, db_session, monkeypatch):
        """With API_KEY set, wrong key should return 401."""
        monkeypatch.setenv("API_KEY", "correct-key")
        from fastapi.testclient import TestClient
        from api_main import app
        from models.database import get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(
            __import__("middleware.auth", fromlist=["verify_api_key"]).verify_api_key,
            None,
        )
        with TestClient(app) as c:
            resp = c.get("/wells", headers={"X-API-Key": "wrong-key"})
        app.dependency_overrides.clear()
        assert resp.status_code == 401

    def test_accepts_correct_key(self, db_session, monkeypatch):
        """With API_KEY set, correct key should return 200."""
        monkeypatch.setenv("API_KEY", "correct-key")
        from fastapi.testclient import TestClient
        from api_main import app
        from models.database import get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(
            __import__("middleware.auth", fromlist=["verify_api_key"]).verify_api_key,
            None,
        )
        with TestClient(app) as c:
            resp = c.get("/wells", headers={"X-API-Key": "correct-key"})
        app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_401_response_format(self, db_session, monkeypatch):
        """401 response should have correct error detail."""
        monkeypatch.setenv("API_KEY", "my-key")
        from fastapi.testclient import TestClient
        from api_main import app
        from models.database import get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(
            __import__("middleware.auth", fromlist=["verify_api_key"]).verify_api_key,
            None,
        )
        with TestClient(app) as c:
            resp = c.get("/wells")
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid or missing API key"
