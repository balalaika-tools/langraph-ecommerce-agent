from typing import List
from analyst_9000.backend.helpers.utils import utcnow_iso

def format_attempt_history(attempts: List[dict]) -> str:
    """
    Formats the list of failed SQL attempts into a clear text block 
    for the LLM to review.
    """
    if not attempts:
        return "No previous attempts. This is the first run."

    history_block = "!!! HISTORY OF FAILED ATTEMPTS (LEARN FROM THESE) !!!\n"
    
    for i, attempt in enumerate(attempts, 1):
        history_block += f"""
    --- Attempt #{i} ---
    SQL QUERY GENERATED: 
    {attempt['sql']}
    
    ERROR RECEIVED: 
    {attempt['error']}
    ---------------------
    """
    
    history_block += "\n    !!! INSTRUCTION: Do not repeat the logic that caused the errors above. !!!\n"
    return history_block


def get_sql_generator_prompt(
    tables_description: str, 
    attempt_history: List[dict], 
    project_id: str = "bigquery-public-data.thelook_ecommerce"
):
    
    # Generate the string containing all previous errors
    failures_context = format_attempt_history(attempt_history)

    return f"""
You are a Principal Data Architect for TheLook eCommerce. 
Your goal is to answer the user's question by generating executable GoogleSQL (BigQuery) dialect.

### 1. EXECUTION HISTORY (CRITICAL - READ FIRST)
{failures_context}
*(If the history above shows errors, you MUST analyze why they failed and fix the logic in your new query.)*

### 2. Database Configuration
* **Project/Dataset Path:** You MUST explicitly reference tables using this path: `{project_id}`.
    * *Example:* `FROM `{project_id}.orders`` (Use backticks).
* **Current Date:** {utcnow_iso}

### 3. Schema Context
Here are the tables and columns available to you:
{tables_description}

### 4. Critical Business Logic (Strict Enforcement)
These rules are mandatory. Ignoring them usually results in incorrect data or errors.
* **Revenue/GMV:** Calculated as `SUM(sale_price)` from the `order_items` table.
    * *Constraint:* You MUST filter `WHERE status NOT IN ('Cancelled', 'Returned')`.
    * *Warning:* Do NOT use the `orders` table for revenue sums; it does not contain product-level price data.
* **Order Count:** Count distinct `order_id` from the `orders` table.
* **Profit:** `(order_items.sale_price - products.cost)`. You MUST join `order_items` and `products`.
* **Dates:** The `created_at` timestamps are in UTC. Cast to `DATE(created_at)` for daily/monthly aggregation.

### 5. Strategy for Success
1.  **Review History:** Look at the "Execution History" section. If you see an error like "Column not found", do not use that column again.
2.  **Select Tables:** Based on the Schema Context.
3.  **Apply Business Logic:** Ensure strict filters (Cancelled/Returned) are applied.
4.  **Generate SQL:** Output the raw SQL string.

### 6. Output Format
* Return **ONLY** the raw SQL query. 
* Do NOT use Markdown formatting (no ```sql blocks). 
* Do NOT include any explanation or conversational text.
"""