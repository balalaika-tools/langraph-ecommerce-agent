from fastapi import Request, HTTPException, status
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import RequestValidationError
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
    """
    Handle FastAPI/Pydantic validation errors (422 Unprocessable Content).
    
    Logs the validation error details and returns a formatted error response.
    """
    # Log validation errors with details
    errors = exc.errors()
    error_details = ", ".join([f"{err['loc']}: {err['msg']}" for err in errors])
    
    logger.error(
        f"❌ Validation error in {request.url.path}: {error_details}",
        exc_info=False,  
    )
    
    # Return formatted error response
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Validation error: Please check your request parameters",
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> ORJSONResponse:
    """
    Handle HTTP exceptions and log them appropriately.
    
    This catches all HTTPExceptions that are raised but not caught by route handlers.
    Note: Auth errors (401) are already logged in auth_exceptions.py, so we skip logging them here.
    """

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
    # Auth-related HTTP errors 
        logger.error(
            f"❌ HTTP 401 Unauthorized in {request.url.path}: {exc.detail}",
            exc_info=False,
        )
    elif exc.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY:
        # All other non-validation HTTP errors
        logger.error(
            f"❌ HTTP {exc.status_code} error in {request.url.path}: {exc.detail}",
            exc_info=False,
        )
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "message": f"HTTP {exc.status_code} error",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
    """
    Handle any unhandled exceptions.
    
    This is a catch-all handler for exceptions that weren't caught by other handlers.
    """
    logger.error(
        f"❌ Unhandled exception in {request.url.path}: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )
    
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "message": "Internal server error",
        },
    )

