from fastapi import Request, FastAPI
from typing import Sequence, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from analyst_9000.backend.core.logger import CorrelationCtx, get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER
import uuid

logger = get_logger(ANALYST_LOGGER)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        inbound = request.headers.get("Request-ID")
        cid = inbound or str(uuid.uuid4())

        token = CorrelationCtx.set(cid)
        try:
            response: Response = await call_next(request)
        except Exception as e:
            logger.error(f"Error in CorrelationIdMiddleware: {e}")
            raise
        finally:
            CorrelationCtx.reset(token)

        response.headers["Request-ID"] = cid
        return response