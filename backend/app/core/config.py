import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AI Interview Intelligence API")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# Reasoning effort for the structured-output calls. Gemini 3 models reason before
# answering, which on a pure extraction task costs minutes of latency for no gain
# in the extracted fields. Set to an empty value to send no thinking configuration
# at all, which is required for models that do not accept one.
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low").strip().lower()
# Hard ceiling on one Gemini HTTP call, so a stalled upstream surfaces as a
# timeout the API can translate rather than holding a request open indefinitely.
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "120"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Supabase Storage Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_RESUME_BUCKET = os.getenv("SUPABASE_RESUME_BUCKET", "resumes")

# Supabase Auth Configuration
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Voice (Speech-to-Text / Text-to-Speech) Configuration
VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "gemini").lower()
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

# CORS Configuration
# Comma-separated list of browser origins allowed to call this API. Deployments
# must set this explicitly; the default only covers local frontend development.
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]


def validate_llm_config() -> None:
    """Validate LLM settings at the LLM boundary."""
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        raise ValueError(
            "LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not configured. "
            "Please set the GEMINI_API_KEY environment variable."
        )


def missing_required_settings() -> list[str]:
    """Names of the settings the product flow needs but this environment lacks.

    Names only, never values. Each of these is required by a user-facing step:
    without it that step fails at request time with an error the caller cannot
    act on, so startup reports them up front instead.
    """
    required = {
        "DATABASE_URL": DATABASE_URL,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
        "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    return sorted(name for name, value in required.items() if not value)
