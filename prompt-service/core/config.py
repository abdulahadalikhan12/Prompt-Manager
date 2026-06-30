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
    # Week 2: where to reach llm-service for execute/follow-up/summary calls.
    LLM_SERVICE_URL: str = os.getenv("LLM_SERVICE_URL", "http://localhost:8002")
    # If true, alembic upgrade head runs automatically at startup
    # (see run_migrations.py) -- useful for deployments with no
    # interactive terminal. Defaults to false so local development
    # keeps explicit, manual control over when migrations apply.
    AUTO_MIGRATE: bool = os.getenv("AUTO_MIGRATE", "false").lower() == "true"


settings = Settings()
