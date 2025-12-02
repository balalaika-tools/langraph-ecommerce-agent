"""Model registry for Analyst-9000 LLM models."""
from typing import Optional
from langchain.chat_models import BaseChatModel, init_chat_model
from analyst_9000.backend.ai_core.llm.callbacks import LoggingHandler, KNOWN_COMPONENT_TAGS
from analyst_9000.backend.schemas.llm_output import RouterResponse
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)

# Configurable fields for dynamic model configuration
CONFIGURABLE_FIELDS = ["model", "temperature", "thinking_budget"]


class ModelRegistry:
    """
    Central registry for all LLM models used in Analyst-9000.
    
    Models:
    - router: Intent classification and query reformation (structured output)
    - qa_model: General QA assistant
    - sql_generator: SQL query generation
    - response_synthesizer: Data-to-insight response generation
    """

    def __init__(self):
        self._router: Optional[BaseChatModel] = None
        self._qa_model: Optional[BaseChatModel] = None
        self._sql_generator: Optional[BaseChatModel] = None
        self._response_synthesizer: Optional[BaseChatModel] = None

    async def init_all(self) -> None:
        """Initialize all models."""
        logger.info("🔧 Initializing model registry...")
        
        self._router = await self._init_router()
        self._qa_model = await self._init_qa_model()
        self._sql_generator = await self._init_sql_generator()
        self._response_synthesizer = await self._init_response_synthesizer()
        
        logger.info("✅ All models initialized successfully")

    async def _init_router(self) -> BaseChatModel:
        """Initialize the router model with structured output."""
        KNOWN_COMPONENT_TAGS.append("Router")
        model = init_chat_model(
            model="google_genai:gemini-2.5-flash",
            callbacks=[LoggingHandler()],
            tags=["Router"],
            configurable_fields=CONFIGURABLE_FIELDS,
            streaming=False,  
        )
        model = model.with_structured_output(RouterResponse, method="json_schema")
        logger.info("✅ Router model initialized")
        return model

    async def _init_qa_model(self) -> BaseChatModel:
        """Initialize the QA model for general queries."""
        KNOWN_COMPONENT_TAGS.append("QA")
        model = init_chat_model(
            model="google_genai:gemini-2.5-flash",
            callbacks=[LoggingHandler()],
            tags=["QA"],
            configurable_fields=CONFIGURABLE_FIELDS,
            streaming=True,  # QA should stream 
        )
        logger.info("✅ QA model initialized")
        return model

    async def _init_sql_generator(self) -> BaseChatModel:
        """Initialize the SQL generator model."""
        KNOWN_COMPONENT_TAGS.append("SQLGenerator")
        model = init_chat_model(
            model="google_genai:gemini-2.5-flash",
            callbacks=[LoggingHandler()],
            tags=["SQLGenerator"],
            configurable_fields=CONFIGURABLE_FIELDS,
            streaming=False, 
        )
        logger.info("✅ SQL Generator model initialized")
        return model

    async def _init_response_synthesizer(self) -> BaseChatModel:
        """Initialize the response synthesizer model."""
        KNOWN_COMPONENT_TAGS.append("ResponseSynthesizer")
        model = init_chat_model(
            model="google_genai:gemini-2.5-flash",
            callbacks=[LoggingHandler()],
            tags=["ResponseSynthesizer"],
            configurable_fields=CONFIGURABLE_FIELDS,
            streaming=True,  # Response synthesizer should stream
        )
        logger.info("✅ Response Synthesizer model initialized")
        return model

    @property
    def router(self) -> BaseChatModel:
        """Get the router model."""
        if self._router is None:
            logger.error("❌ Router model not initialized")
            raise RuntimeError("Router model not initialized")
        return self._router

    @property
    def qa_model(self) -> BaseChatModel:
        """Get the QA model."""
        if self._qa_model is None:
            logger.error("❌ QA model not initialized")
            raise RuntimeError("QA model not initialized")
        return self._qa_model

    @property
    def sql_generator(self) -> BaseChatModel:
        """Get the SQL generator model."""
        if self._sql_generator is None:
            logger.error("❌ SQL Generator model not initialized")
            raise RuntimeError("SQL Generator model not initialized")
        return self._sql_generator

    @property
    def response_synthesizer(self) -> BaseChatModel:
        """Get the response synthesizer model."""
        if self._response_synthesizer is None:
            logger.error("❌ Response Synthesizer model not initialized")
            raise RuntimeError("Response Synthesizer model not initialized")
        return self._response_synthesizer
