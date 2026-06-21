import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Centralized configuration. Everything that comes from .env is read
    ONCE here, not scattered across database.py, main.py, etc. with
    individual os.getenv() calls. Anything needing config imports
    `settings` from this module instead.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8000"))


settings = Settings()
