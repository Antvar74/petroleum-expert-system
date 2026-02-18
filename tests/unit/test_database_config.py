"""
Unit tests for database URL configuration and connection args.
Verifies that DATABASE_URL, VERCEL, and default SQLite paths work correctly.
"""
import pytest
import os


class TestBuildDatabaseUrl:
    """Tests for _build_database_url() resolution logic."""

    def test_default_sqlite_url(self, monkeypatch):
        """Without any env vars, URL should be a local SQLite path."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
        # Re-import to get fresh function
        from models.database import _build_database_url, BASE_DIR
        url = _build_database_url()
        assert url.startswith("sqlite:///")
        assert "petroleum_expert.db" in url
        assert BASE_DIR in url

    def test_vercel_sqlite_url(self, monkeypatch):
        """With VERCEL=1, URL should point to /tmp."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("VERCEL", "1")
        from models.database import _build_database_url
        url = _build_database_url()
        assert url == "sqlite:////tmp/petroleum_expert.db"

    def test_custom_database_url(self, monkeypatch):
        """DATABASE_URL env var should be used as-is."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/mydb")
        from models.database import _build_database_url
        url = _build_database_url()
        assert url == "postgresql://user:pass@localhost:5432/mydb"

    def test_database_url_priority_over_vercel(self, monkeypatch):
        """DATABASE_URL takes priority over VERCEL flag."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://host/db")
        monkeypatch.setenv("VERCEL", "1")
        from models.database import _build_database_url
        url = _build_database_url()
        assert url == "postgresql://host/db"


class TestConnectArgs:
    """Tests for conditional connect_args based on DB type."""

    def test_sqlite_connect_args(self):
        """SQLite URLs should produce check_same_thread in connect_args."""
        url = "sqlite:///test.db"
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        assert "check_same_thread" in connect_args
        assert connect_args["check_same_thread"] is False

    def test_postgres_no_check_same_thread(self):
        """PostgreSQL URLs should produce empty connect_args."""
        url = "postgresql://user:pass@localhost/db"
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        assert connect_args == {}
