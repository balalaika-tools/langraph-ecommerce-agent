from typing import Optional
from analyst_9000.backend.ai_core.llm.callbacks import LoggingHandler, KNOWN_COMPONENT_TAGS
from langchain.chat_models import BaseChatModel, init_chat_model
from analyst_9000.backend.schemas.llm_output import RouterResponse
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)
CONFIGURABLE_FIELDS = ["model", "temperature", "reasoning_budget"]

class ModelRegistry:
    def __init__(self):
        self._router: Optional[BaseChatModel] = None

    async def init_all(self):
        """Initialize all models"""
        self._router = await self._init_router()


    async def _init_router(self) -> BaseChatModel:
        KNOWN_COMPONENT_TAGS.append("Router")
        model = init_chat_model(
            model="google_genai:gemini-2.5-flash", 
            callbacks=[LoggingHandler()],
            tags=["Router"],
            configurable_fields=CONFIGURABLE_FIELDS,
            streaming=True,
        )
        model = model.with_structured_output(RouterResponse, method="json_schema")
        return model


    @property
    def router(self) -> BaseChatModel:
        if self._router is None:
            logger.error("❌ Router model not initialized")
            raise RuntimeError("Router model not initialized")
        return self._router

    