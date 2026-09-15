# Uses PEP 8
# Tools: black, flake8, mypy

import logging
import os

logger = logging.getLogger(__name__)

# In Docker: http://backend:8083. When running bot on host: set BACKEND_URL=http://127.0.0.1:8083
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8083").rstrip("/")
# Public frontend URL shown in bot (registration hint). Dev default: local Vite.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
REGISTER_URL = f"{FRONTEND_URL}/register"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SERVICE_NAME = os.getenv("SERVICE_NAME", "telegram-frontend")
HEALTH_PORT = int(os.getenv("SERVICE_PORT", "8090"))


def log_bot_config() -> None:
    """Log resolved backend and frontend URLs at startup."""
    logger.info("FRONTEND_URL (site registration): %s", FRONTEND_URL)
    logger.info("BACKEND_URL: %s", BACKEND_URL)
