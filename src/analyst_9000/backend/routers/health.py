from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone
import sys
import platform
from analyst_9000.backend.schemas.api_schemas import HealthResponse


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",  
        python_version=sys.version,
        platform=platform.platform(),
    )
