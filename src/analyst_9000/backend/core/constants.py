# ============================================================
# General Constants
# ============================================================
LOCAL_DEV_PORT = 6757
ANALYST_LOGGER = "analyst-9000"
ANALYST_LOGS_DIR = "Analyst-9000Logs"
ANALYST_LOG_FILE = "app.log"
ANALYST_MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
ANALYST_BACKUP_COUNT = 5                   # 5 backup files circulating in the logs directory
ANALYST_CONSOLE_OUTPUT = True              # True to print the logs to the console


# ============================================================
# Reasoning Budget Mapping
# ============================================================
# This is an empirical mapping 
THINKING_BUDGET_MAP = {
    "low": 128,
    "medium": 2500,
    "high": 10000,
}


# ============================================================
# SQL Generator Constants
# ============================================================
MAX_ITERATIONS = 3 # Maximum number of iterations to try to generate a valid SQL query