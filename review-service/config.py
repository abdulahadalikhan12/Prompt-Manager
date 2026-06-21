import os
from dotenv import load_dotenv

load_dotenv()

PROMPT_SERVICE_URL = os.getenv("PROMPT_SERVICE_URL")
SERVICE_PORT = os.getenv("SERVICE_PORT")
