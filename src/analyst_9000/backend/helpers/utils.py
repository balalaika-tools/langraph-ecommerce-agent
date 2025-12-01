from datetime import datetime, timezone
from pathlib import Path
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER
import re

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
    except Exception as e:
        logger.error(f"Error loading query from file {filename}: {e}")
        raise e



def clean_sql_output(llm_output: str) -> str:
    """
    Strips markdown formatting (```sql ... ```) if the LLM includes it 
    despite instructions not to.
    """
    # Remove ```sql or ``` at start
    pattern = r"^```(?:sql)?\s*(.*)\s*```$"
    match = re.search(pattern, llm_output.strip(), re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return llm_output.strip()