"""
Unit tests for registration gate (ALLOW_REGISTRATION + INVITE_CODE).
Tests that registration can be disabled and optionally require an invite code.
"""
import uuid
import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset rate limiter storage before each test to avoid 429 in test suite."""
    from middleware.rate_limit import limiter
    try:
        limiter.reset()
    except Exception:
        # In-memory limiter may not support reset — clear storage directly
        try:
            limiter._storage.reset()
        except Exception:
            pass
    yield


def _unique(prefix: str) -> dict:
    """Generate unique registration payload to avoid collisions with shared DB."""
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"{prefix}_{uid}",
        "email": f"{prefix}_{uid}@test.example.com",
        "password": "securepass123",
    }


class TestRegistrationGate:
    """Tests for registration gate variables."""

    def test_registration_disabled(self, client, monkeypatch):
        """When ALLOW_REGISTRATION=false, register must return 403."""
        import routes.auth as auth_module
        monkeypatch.setattr(auth_module, "_ALLOW_REGISTRATION", False)

        resp = client.post("/auth/register", json=_unique("disabled"))
        assert resp.status_code == 403
        assert "Registration is disabled" in resp.json()["detail"]

    def test_registration_enabled_by_default(self, client):
        """When ALLOW_REGISTRATION is not set (default), registration works."""
        resp = client.post("/auth/register", json=_unique("default"))
        assert resp.status_code == 201

    def test_invite_code_required_wrong_code(self, client, monkeypatch):
        """When INVITE_CODE is set and wrong code provided, must return 403."""
        import routes.auth as auth_module
        monkeypatch.setattr(auth_module, "_ALLOW_REGISTRATION", True)
        monkeypatch.setattr(auth_module, "_INVITE_CODE", "correct-secret-code")

        payload = _unique("wrongcode")
        payload["invite_code"] = "wrong-code"
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 403
        assert "invite code" in resp.json()["detail"].lower()

    def test_invite_code_required_missing_code(self, client, monkeypatch):
        """When INVITE_CODE is set and no code provided, must return 403."""
        import routes.auth as auth_module
        monkeypatch.setattr(auth_module, "_ALLOW_REGISTRATION", True)
        monkeypatch.setattr(auth_module, "_INVITE_CODE", "correct-secret-code")

        resp = client.post("/auth/register", json=_unique("nocode"))
        assert resp.status_code == 403

    def test_invite_code_correct(self, client, monkeypatch):
        """When INVITE_CODE is set and correct code provided, registration succeeds."""
        import routes.auth as auth_module
        monkeypatch.setattr(auth_module, "_ALLOW_REGISTRATION", True)
        monkeypatch.setattr(auth_module, "_INVITE_CODE", "correct-secret-code")

        payload = _unique("invited")
        payload["invite_code"] = "correct-secret-code"
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201

    def test_no_invite_code_required(self, client, monkeypatch):
        """When INVITE_CODE is None, registration works without code."""
        import routes.auth as auth_module
        monkeypatch.setattr(auth_module, "_ALLOW_REGISTRATION", True)
        monkeypatch.setattr(auth_module, "_INVITE_CODE", None)

        resp = client.post("/auth/register", json=_unique("noinvite"))
        assert resp.status_code == 201
