import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Same pattern as prompt-service/core/config.py -- one place
    reads .env, everything else imports `settings` from here."""
    PROMPT_SERVICE_URL: str = os.getenv("PROMPT_SERVICE_URL")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))


settings = Settings()
