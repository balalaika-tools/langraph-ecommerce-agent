from datetime import datetime, timezone
from pathlib import Path
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)
SQL_QUERIES_DIR = Path(__file__).parent / "sql_queries"


def utcnow_iso() -> str:
    """ISO8601 UTC format with timezone (e.g. 2025-11-12T12:00:00+00:00)."""
    return datetime.now(timezone.utc).isoformat()



def load_query(filename: str) -> str:
    """
    Load a SQL query from a file.
    
    """
    try:
        query_path = SQL_QUERIES_DIR / filename
        return query_path.read_text(encoding="utf-8").strip()
    except exception as e:
        logger.error(f"Error loading query from file {filename}: {e}")
        raise e
