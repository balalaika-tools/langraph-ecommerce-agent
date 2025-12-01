from functools import lru_cache, cached_property
from typing import Optional, List
from pydantic import Field, AnyHttpUrl, computed_field, SecretStr
from pydantic_settings import BaseSettings
from analyst_9000.backend.core.bigquery_handler import BigQueryHandler
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # General
    webhook_uri: Optional[AnyHttpUrl] = Field(None, description="The URI of the webhook to send error logs to.", alias="WEBHOOK_URI")
    #gemini_api_key: SecretStr = Field(..., description="The API key for the Gemini API.", alias="GEMINI_API_KEY")


    # BigQuery Settings 
    big_query_dataset: str = Field(default="bigquery-public-data.thelook_ecommerce", description="The dataset to use for the bigquery client.", alias="BIG_QUERY_DATASET")
    big_query_table_names: List[str] = Field(default=["orders", "order_items", "products", "users"], description="The table names to use for the bigquery client.", alias="BIG_QUERY_TABLE_NAMES")

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
        return BigQueryHandler(dataset_name=self.big_query_dataset, table_names=self.big_query_table_names)



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        # 1. instantiate settings (load from .env)
        settings = Settings()
    
        logger.info(f"✅ Loaded settings")
        return settings
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        raise
