from dataclasses import dataclass
import os

# Optional: if you are using a .env file, enable this loader
try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except Exception:
    # If dotenv is not installed or .env file is missing, ignore
    pass


@dataclass
class AppConfig:
    """
    General application settings.
    Values are read from environment variables, falling back to defaults if not set.
    """
    MAX_TURNS: int = int(os.getenv("MAX_TURNS", "7"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.4"))
    # Default termination word if environment variable is missing
    TERMINATION_WORD: str = os.getenv("TERMINATION_WORD", "end")
    # Convert string to bool: "true", "1", "yes" → True
    RESPONSE_JSON: bool = os.getenv("RESPONSE_JSON", "true").lower() in {"1", "true", "yes"}


@dataclass
class GoogleConfig:
    """
    Gemini model settings through the OpenAI-compatible Google endpoint.
    GOOGLE_API_KEY must always be set, otherwise the program will raise an error.
    """
    API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    BASE_URL: str = os.getenv(
        "GOOGLE_OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    TIMEOUT: float = float(os.getenv("GEMINI_TIMEOUT", "30"))
    # Optional: reasoning effort level for Gemini (none|low|medium|high)
    REASONING_EFFORT: str = os.getenv("REASONING_EFFORT", "low")

@dataclass
class TavilyConfig:
    """
    Tavily API settings.
    """
    API_KEY: str = os.getenv("TAVILY_API_KEY", "")


app_cfg = AppConfig()
google_cfg = GoogleConfig()
tavily_cfg = TavilyConfig()

# Validation: API key must not be empty
if not (google_cfg.API_KEY and google_cfg.API_KEY.strip()):
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. "
        "Set it via environment variable or .env file, e.g. export GOOGLE_API_KEY='your_key'."
    )

if not (tavily_cfg.API_KEY and tavily_cfg.API_KEY.strip()):
    print("[WARN] TAVILY_API_KEY is not set. The Web Search tool will not be available.")