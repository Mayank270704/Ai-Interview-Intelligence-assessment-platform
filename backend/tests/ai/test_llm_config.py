"""Tests for LLM configuration."""

import pytest
from unittest.mock import patch


def test_config_loads_defaults():
    """Test that config loads with default values."""
    with patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-key",
        },
        clear=False,
    ):
        # Re-import to get fresh config with test env vars
        import importlib
        import app.core.config as config_module

        importlib.reload(config_module)

        assert config_module.LLM_PROVIDER == "gemini"
        assert config_module.GEMINI_API_KEY == "test-key"
        assert config_module.GEMINI_MODEL is not None


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
        import importlib
        import app.core.config as config_module

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
        import importlib
        import app.core.config as config_module

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
        import importlib
        import app.core.config as config_module

        importlib.reload(config_module)

        # Should have a default model
        assert config_module.GEMINI_MODEL is not None
        assert config_module.GEMINI_MODEL.startswith("gemini-")

