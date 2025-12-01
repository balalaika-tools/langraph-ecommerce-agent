from typing import Dict, Any
from analyst_9000.backend.core.constants import THINKING_BUDGET_MAP



def handle_reasoning_budget(model_name: str, reasoning_budget: str = "low") -> Dict[str, Any]:
    """
    Selects the appropriate reasoning budget configuration based on
    the model name and requested reasoning_budget level ('low', 'medium', 'high').
    """
    if "2.5-pro" in model_name:
        if reasoning_budget == "low":
            return {"thinking_budget": THINKING_BUDGET_MAP["low"]}
        elif reasoning_budget == "medium":
            return {"thinking_budget": THINKING_BUDGET_MAP["medium"]}
        elif reasoning_budget == "high":
            return {"thinking_budget": THINKING_BUDGET_MAP["high"]}
    elif "2.5-flash" in model_name:
        if reasoning_budget == "low":
            return {"thinking_budget": 0}
        elif reasoning_budget == "medium":
            return {"thinking_budget": 2500}
        elif reasoning_budget == "high":
            return {"thinking_budget": 10000}
    return {}
