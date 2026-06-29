import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Same centralized-settings pattern used in prompt-service and
    review-service. Everything from .env is read once, here."""
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8002"))

    # Parsed once into a real Python list, e.g.
    # ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct:free", "openrouter/free"]
    # The first entry is tried first; later entries are fallbacks tried
    # only if everything before them fails (after retries).
    MODEL_CHAIN: list[str] = [
        m.strip() for m in os.getenv("MODEL_CHAIN", "openrouter/free").split(",") if m.strip()
    ]


settings = Settings()
