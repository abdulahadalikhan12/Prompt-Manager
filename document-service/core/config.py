import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """One place reads .env, everything else imports `settings` from here --
    same pattern as the other services."""
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))


settings = Settings()
