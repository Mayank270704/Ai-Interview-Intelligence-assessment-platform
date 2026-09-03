"""Tests for LLM configuration."""

import importlib

import pytest
from unittest.mock import patch

import app.core.config as config_module


@pytest.fixture(autouse=True)
def restore_config():
    """Reload the real config afterwards.

    Every test here reloads app.core.config against a doctored environment, and
    the reloaded module stays in sys.modules for the rest of the session.
    """
    yield
    importlib.reload(config_module)


@pytest.fixture
def isolated_env(monkeypatch):
    """Reload config against an environment containing only the given variables.

    config calls load_dotenv() on import, which would otherwise repopulate the
    real .env values into the cleared environment and make these assertions
    vacuous. The reload re-executes `from dotenv import load_dotenv`, so the
    stub has to be installed on dotenv itself rather than on config.
    """
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)

    def reload_with(**env):
        with patch.dict("os.environ", env, clear=True):
            importlib.reload(config_module)
        return config_module

    return reload_with


def test_config_loads_defaults():
    """Test that config loads with default values."""
    with patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-key",
        },
        clear=False,
    ):
        importlib.reload(config_module)

        assert config_module.LLM_PROVIDER == "gemini"
        assert config_module.GEMINI_API_KEY == "test-key"
        assert config_module.GEMINI_MODEL is not None


def test_config_import_does_not_require_gemini_key(isolated_env):
    """Database tooling can import config without unrelated LLM secrets."""
    config = isolated_env(LLM_PROVIDER="gemini")

    assert config.GEMINI_API_KEY is None
    assert config.LLM_PROVIDER == "gemini"


def test_llm_validation_still_requires_gemini_key(isolated_env):
    """Application LLM usage should still validate provider configuration."""
    config = isolated_env(LLM_PROVIDER="gemini")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        config.validate_llm_config()


def test_llm_validation_passes_when_gemini_key_is_present(isolated_env):
    config = isolated_env(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key")

    config.validate_llm_config()


def test_config_loads_custom_provider():
    """Test that config loads custom provider from env."""
    with patch.dict(
        "os.environ",
        {
            "LLM_PROVIDER": "gemini",
            "GEMINI_API_KEY": "test-key",
            "GEMINI_MODEL": "custom-model",
        },
        clear=False,
    ):
        importlib.reload(config_module)

        assert config_module.LLM_PROVIDER == "gemini"
        assert config_module.GEMINI_MODEL == "custom-model"


def test_config_provider_case_insensitive():
    """Test that provider name is case-insensitive."""
    with patch.dict(
        "os.environ",
        {
            "LLM_PROVIDER": "GEMINI",
            "GEMINI_API_KEY": "test-key",
        },
        clear=False,
    ):
        importlib.reload(config_module)

        assert config_module.LLM_PROVIDER == "gemini"


def test_config_default_gemini_model():
    """Test that default Gemini model is set."""
    with patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-key",
            # Not setting GEMINI_MODEL to test default
        },
        clear=False,
    ):
        importlib.reload(config_module)

        # Should have a default model
        assert config_module.GEMINI_MODEL is not None
        assert config_module.GEMINI_MODEL.startswith("gemini-")

