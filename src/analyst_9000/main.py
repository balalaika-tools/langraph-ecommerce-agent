from analyst_9000.backend.core.setup import *
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import LOCAL_DEV_PORT
from analyst_9000.backend.services.app_startup.app_startup_service import create_app
import uvicorn
import sys


def run_app():
    """Run the FastAPI application on Azure."""
    return create_app()


def run_app_locally():
    """Run the FastAPI application locally."""
    try:
        logger.info(f"🔄 Starting Uvicorn server on localhost:{LOCAL_DEV_PORT}")
        uvicorn.run(
            "analyst_9000.backend.services.app_startup.app_startup_service:create_app",
            host="0.0.0.0",
            port=LOCAL_DEV_PORT,
            reload=True,
            factory=True,
        )
    except:
        sys.exit(1)


if __name__ == "__main__":
    run_app_locally()