from typing import Dict, Any
from langchain_core.tools import tool
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)


@tool
def execute_bigquery_sql(sql_query: str) -> Dict[str, Any]:
    """
    Execute a SQL query against BigQuery and return the results.
    
    This tool MUST be called with the generated SQL query to retrieve data
    from the TheLook eCommerce dataset.
    
    Args:
        sql_query: The SQL query to execute against BigQuery.
        
    Returns:
        A dictionary containing either:
        - {"success": True, "data": [...], "row_count": N} on success
        - {"success": False, "error": "error message"} on failure
    """
    from analyst_9000.backend.core.config import get_settings
    
    settings = get_settings()
    client = settings.bigquery_handler.client
    
    try:
        logger.info(f"🔍 Executing SQL query:\n{sql_query[:200]}...")
        
        # Execute the query
        query_job = client.query(sql_query)
        results = query_job.result()
        
        # Convert results to list of dicts
        rows = []
        for row in results:
            rows.append(dict(row.items()))
        
        logger.info(f"✅ Query executed successfully. Retrieved {len(rows)} rows.")
        
        return {
            "success": True,
            "data": rows,
            "row_count": len(rows),
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"⚠️ BigQuery execution failed: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
        }


# List of tools available to the SQL generator
SQL_TOOLS = [execute_bigquery_sql]

