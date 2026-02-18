"""
Structural tests for Docker deployment files.
Verifies that Dockerfile and docker-compose.yml exist and contain expected content.
"""
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDockerFiles:
    """Verify Docker infrastructure files exist and are valid."""

    def test_dockerfile_exists_and_has_stages(self):
        """Dockerfile should exist and contain multi-stage build."""
        path = os.path.join(PROJECT_ROOT, "Dockerfile")
        assert os.path.isfile(path), "Dockerfile not found at project root"
        content = open(path).read()
        assert "FROM node:" in content, "Missing frontend build stage"
        assert "FROM python:" in content, "Missing Python backend stage"
        assert "EXPOSE 8000" in content, "Missing EXPOSE directive"
        assert "uvicorn" in content, "Missing uvicorn CMD"

    def test_docker_compose_exists_and_has_app_service(self):
        """docker-compose.yml should exist and define app service."""
        path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
        assert os.path.isfile(path), "docker-compose.yml not found at project root"
        content = open(path).read()
        assert "services:" in content, "Missing services key"
        assert "app:" in content, "Missing app service"
        assert "8000:8000" in content, "Missing port mapping"
        assert "DATABASE_URL" in content, "Missing DATABASE_URL env"
