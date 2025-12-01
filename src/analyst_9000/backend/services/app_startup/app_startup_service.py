from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from analyst_9000.backend.middleware.middleware import CorrelationIdMiddleware
from analyst_9000.backend.routers import chatbot, health
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER
from analyst_9000.backend.exceptions.api_exceptions import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

logger = get_logger(ANALYST_LOGGER)


def _setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


def _setup_middleware(app: FastAPI) -> None:
    '''Setup middleware for the FastAPI application.'''
    app.add_middleware(CorrelationIdMiddleware)


def _setup_routers(app: FastAPI) -> None:
    '''Setup routers for the FastAPI application.'''
    app.include_router(chatbot.router)
    app.include_router(health.router)

def _setup_static_files(app: FastAPI) -> None:
    '''Setup static files for the FastAPI application.'''
    static_dir = Path(__file__).resolve().parents[3] / "frontend"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI startup and shutdown."""
    # ==================== STARTUP ====================
    logger.info("🚀 Application startup...")
    try:
        # Add any startup logic here (e.g., connect to database, initialize services)
        logger.info("✅ Application startup completed")
        yield
    except Exception as e:
        logger.exception(f"❌ Error during application startup: {e}")
        raise
    finally:
        # ==================== SHUTDOWN ====================
        logger.info("🛑 Application shutdown...")
        # Add any cleanup logic here 
        logger.info("✅ Application shutdown completed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    try:
        # Create FastAPI app with lifespan
        app = FastAPI(
            lifespan=lifespan,
            default_response_class=ORJSONResponse,
        )

        # Configure the application
        _setup_exception_handlers(app)
        _setup_middleware(app)
        _setup_routers(app)
        _setup_static_files(app)

        logger.info("✅ FastAPI app configured successfully")
        return app

    except Exception as e:
        logger.exception(f"❌ Error during FastAPI app setup: {e}")
        raise
