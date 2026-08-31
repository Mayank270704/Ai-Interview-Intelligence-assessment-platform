import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "AI Interview Intelligence API")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

def validate_llm_config() -> None:
    """Validate LLM settings at the LLM boundary."""
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        raise ValueError(
            "LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not configured. "
            "Please set the GEMINI_API_KEY environment variable."
        )
