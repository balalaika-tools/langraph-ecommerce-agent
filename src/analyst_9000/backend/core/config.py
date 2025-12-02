import os
from functools import lru_cache, cached_property
from typing import Optional, List, Any
from pydantic import Field, AnyHttpUrl, computed_field, SecretStr
from pydantic_settings import BaseSettings
from analyst_9000.backend.core.bigquery_handler import BigQueryHandler
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import (
    ANALYST_LOGGER, 
    DEFAULT_SQLITE_PATH, 
    DB_POOL_SIZE, 
    DB_MAX_OVERFLOW,
)

logger = get_logger(ANALYST_LOGGER)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ============================================================
    # General Settings
    # ============================================================
    webhook_uri: Optional[AnyHttpUrl] = Field(
        None, 
        description="The URI of the webhook to send error logs to.", 
        alias="WEBHOOK_URI"
    )
    gemini_api_key: SecretStr = Field(
        ..., 
        description="The API key for the Gemini API.", 
        alias="GEMINI_API_KEY"
    )

    # ============================================================
    # BigQuery Settings 
    # ============================================================
    big_query_dataset: str = Field(
        default="bigquery-public-data.thelook_ecommerce", 
        description="The dataset to use for the bigquery client.", 
        alias="BIG_QUERY_DATASET"
    )
    big_query_table_names: List[str] = Field(
        default=["orders", "order_items", "products", "users"], 
        description="The table names to use for the bigquery client.", 
        alias="BIG_QUERY_TABLE_NAMES"
    )

    # ============================================================
    # Session Store Settings (PostgreSQL/SQLite)
    # ============================================================
    session_store_url: Optional[str] = Field(
        default=None,
        description="Session store URL. Use postgresql:// for PostgreSQL or sqlite:// for SQLite",
        alias="DATABASE_URL"
    )
    pool_size: int = Field(
        default=DB_POOL_SIZE,
        description="Connection pool size",
        alias="DB_POOL_SIZE"
    )
    pool_max_overflow: int = Field(
        default=DB_MAX_OVERFLOW,
        description="Maximum overflow connections",
        alias="DB_MAX_OVERFLOW"
    )

    # ============================================================
    # Runtime Fields (set during initialization)
    # ============================================================
    session_store: Optional[Any] = Field(
        default=None,
        description="Session store instance (set at runtime)"
    )
    model_registry: Optional[Any] = Field(
        default=None,
        description="Model registry instance (set at runtime)"
    )
    analyst_graph: Optional[Any] = Field(
        default=None,
        description="AnalystGraph instance (set at runtime)"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "populate_by_name": True,
        "extra": "ignore",
        "arbitrary_types_allowed": True,
    }

    @computed_field
    @cached_property
    def bigquery_handler(self) -> BigQueryHandler:
        """Lazily initialize BigQuery handler."""
        return BigQueryHandler(
            dataset_name=self.big_query_dataset, 
            table_names=self.big_query_table_names
        )

    @computed_field
    @property
    def effective_session_store_url(self) -> str:
        """Get the effective session store URL, defaulting to SQLite for local dev."""
        if self.session_store_url:
            return self.session_store_url
        # Default to SQLite for local development
        return f"sqlite:///{DEFAULT_SQLITE_PATH}"

    def setup_google_credentials(self) -> None:
        """Set up Google API credentials for Gemini."""
        api_key = self.gemini_api_key.get_secret_value()
        os.environ["GOOGLE_API_KEY"] = api_key
        logger.info("✅ Google API credentials configured")

    async def setup_session_store(self) -> None:
        """Initialize the session store."""
        from analyst_9000.backend.core.session_store import AsyncSessionStore
        
        store_url = self.effective_session_store_url
        logger.info(f"🔧 Initializing session store: {'PostgreSQL' if 'postgresql' in store_url else 'SQLite'}")
        
        self.session_store = AsyncSessionStore(
            connection_url=store_url,
            pool_size=self.pool_size,
            max_overflow=self.pool_max_overflow,
        )
        await self.session_store.init()
        logger.info("✅ Session store initialized")

    async def setup_model_registry(self) -> None:
        """Initialize the model registry with all LLM models."""
        from analyst_9000.backend.ai_core.llm.registry import ModelRegistry
        
        # Ensure Google credentials are set
        self.setup_google_credentials()
        
        self.model_registry = ModelRegistry()
        await self.model_registry.init_all()
        logger.info("✅ Model registry initialized")

    async def setup_analyst_graph(self) -> None:
        """Initialize the Analyst graph."""
        from analyst_9000.backend.ai_core.graph.graph import AnalystGraph
        
        self.analyst_graph = AnalystGraph()
        logger.info("✅ Analyst graph initialized")

    async def close_session_store(self) -> None:
        """Close session store connections."""
        if self.session_store:
            await self.session_store.close()
            logger.info("🔒 Session store connections closed")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        settings = Settings()
        logger.info("✅ Loaded settings")
        return settings
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        raise
