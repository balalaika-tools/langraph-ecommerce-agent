import os
from pathlib import Path
from typing import Optional
from logging import Logger
from dotenv import load_dotenv
from analyst_9000.backend.core.logger import configure_logging
from analyst_9000.backend.core.config import get_settings
from analyst_9000.backend.core.constants import (
    ANALYST_LOGS_DIR,
    ANALYST_LOG_FILE,
    ANALYST_MAX_FILE_SIZE,
    ANALYST_BACKUP_COUNT,
    ANALYST_CONSOLE_OUTPUT,
    ANALYST_LOGGER,
)

_SETUP_COMPLETED = False

def setup() -> Optional[Logger]:
    global _SETUP_COMPLETED
    if _SETUP_COMPLETED:
        return 
    _SETUP_COMPLETED = True
    # Find project root
    project_root = Path(__file__).resolve().parents[4]

    # Load .env file from project root
    load_dotenv(project_root / ".env")

    # Configure logging
    logger = configure_logging(
        log_file=Path(ANALYST_LOGS_DIR) / Path(ANALYST_LOG_FILE),
        max_file_size=ANALYST_MAX_FILE_SIZE,
        backup_count=ANALYST_BACKUP_COUNT,
        console_output=ANALYST_CONSOLE_OUTPUT,
        json_output=True,
        logger_name=ANALYST_LOGGER,
        webhook_url=os.getenv("WEBHOOK_URI"),
    )

    if not os.getenv("WEBHOOK_URI"):
        logger.warning("⚠️ WEBHOOK_URI is not set, no webhook will be utilized")

    # Set GOOGLE_APPLICATION_CREDENTIALS (always in secrets/credentials.json)
    credentials_path = project_root / "secrets" / "credentials.json"
    if not credentials_path.exists():
        logger.error(f"❌ Credentials file not found at: {credentials_path}")
        raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)

    # init settings
    get_settings() # this will cache the settings
    logger.info("✅ Setup completed successfully")

    return logger



# Auto-initialize setup when module is imported
logger = setup()