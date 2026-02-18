"""
Unit tests for LLM Provider selection.
Tests get_available_providers(), provider routing in generate_analysis(),
and provider threading through ModuleAnalysisEngine.
"""
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from utils.llm_gateway import LLMGateway
from orchestrator.module_analysis_engine import ModuleAnalysisEngine


# ================================================================
# TestGetAvailableProviders
# ================================================================

class TestGetAvailableProviders:
    @pytest.mark.asyncio
    async def test_always_includes_auto(self):
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            providers = await gw.get_available_providers()
            ids = [p["id"] for p in providers]
            assert "auto" in ids

    @pytest.mark.asyncio
    async def test_includes_gemini_when_key_set(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            gw = LLMGateway()
            providers = await gw.get_available_providers()
            ids = [p["id"] for p in providers]
            assert "gemini" in ids

    @pytest.mark.asyncio
    async def test_excludes_gemini_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            providers = await gw.get_available_providers()
            ids = [p["id"] for p in providers]
            assert "gemini" not in ids

    @pytest.mark.asyncio
    async def test_each_provider_has_required_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            for p in await gw.get_available_providers():
                assert "id" in p
                assert "name" in p
                assert "name_es" in p

    @pytest.mark.asyncio
    async def test_ollama_shown_only_if_running(self):
        """Ollama should only appear if the local server responds."""
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            # Ollama is NOT running (default in test environment)
            providers = await gw.get_available_providers()
            ids = [p["id"] for p in providers]
            assert "ollama" not in ids


# ================================================================
# TestGenerateAnalysisProviderRouting
# ================================================================

class TestGenerateAnalysisProviderRouting:
    @pytest.fixture
    def gateway(self):
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            return gw

    @pytest.mark.asyncio
    async def test_ollama_direct_calls_ollama(self, gateway):
        gateway._call_ollama = AsyncMock(return_value="Ollama response")
        result = await gateway.generate_analysis("test prompt", provider="ollama")
        gateway._call_ollama.assert_called_once()
        assert result == "Ollama response"

    @pytest.mark.asyncio
    async def test_gemini_without_key_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            gw = LLMGateway()
            result = await gw.generate_analysis("test", provider="gemini")
            assert "Failed" in result or "Missing" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_auto_mode_tries_gemini_first(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            gw = LLMGateway()
            # Mock the gemini model's generate_content_async
            mock_response = MagicMock()
            mock_response.text = "Gemini analysis result"
            gw.gemini_flash.generate_content_async = AsyncMock(return_value=mock_response)
            result = await gw.generate_analysis("test prompt", provider="auto")
            gw.gemini_flash.generate_content_async.assert_called_once()
            assert result == "Gemini analysis result"

    @pytest.mark.asyncio
    async def test_auto_falls_back_to_ollama(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            gw = LLMGateway()
            # Make Gemini fail
            gw.gemini_flash.generate_content_async = AsyncMock(side_effect=Exception("Gemini down"))
            # Make Ollama succeed
            gw._call_ollama = AsyncMock(return_value="Ollama fallback result")
            result = await gw.generate_analysis("test prompt", provider="auto")
            assert result == "Ollama fallback result"


# ================================================================
# TestModuleAnalysisEngineProviderThreading
# ================================================================

class TestModuleAnalysisEngineProviderThreading:
    def test_package_includes_provider_used(self):
        engine = ModuleAnalysisEngine()
        analysis = {"agent": "well_engineer", "role": "Well Engineer",
                     "analysis": "test", "confidence": "HIGH"}
        result = engine._package(analysis, "torque_drag", {}, "WELL-1", "en", "gemini")
        assert result["provider_used"] == "gemini"

    def test_package_default_provider_is_auto(self):
        engine = ModuleAnalysisEngine()
        analysis = {"agent": "well_engineer", "role": "Well Engineer",
                     "analysis": "test", "confidence": "HIGH"}
        result = engine._package(analysis, "torque_drag", {}, "WELL-1", "en")
        assert result["provider_used"] == "auto"
