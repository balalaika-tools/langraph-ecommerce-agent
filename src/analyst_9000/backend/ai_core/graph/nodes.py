from typing import Literal, AsyncIterator
from langsmith import traceable
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from analyst_9000.backend.core.constants import ANALYST_LOGGER, MAX_ITERATIONS
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.ai_core.graph.states import AgentState, Attempt
from analyst_9000.backend.ai_core.prompts.router import get_router_prompt
from analyst_9000.backend.ai_core.prompts.qa_model import get_qa_assistant_prompt
from analyst_9000.backend.ai_core.prompts.sql_generator import get_sql_generator_prompt
from analyst_9000.backend.ai_core.prompts.response_synthesizer import get_response_synthesizer_prompt
from analyst_9000.backend.ai_core.graph.tools import execute_bigquery_sql
from analyst_9000.backend.helpers.utils import clean_sql_output
from analyst_9000.backend.ai_core.llm.llm_utils import handle_reasoning_budget

logger = get_logger(ANALYST_LOGGER)


def _get_model_config(state: AgentState, override_temp: float | None = None) -> dict:
    """Build the configurable dict for model invocation based on state."""
    config = {}
    model_name = state.get("model_name")
    temperature = override_temp if override_temp is not None else state.get("temperature")
    reasoning_budget = state.get("reasoning_budget")
    
    configurable = {}
    if model_name:
        configurable["model"] = model_name
    if temperature is not None:
        configurable["temperature"] = temperature
    if reasoning_budget:
        # Thinking budget
        target_model = model_name or "google_genai:gemini-2.5-flash"
        budget_config = handle_reasoning_budget(target_model, reasoning_budget)
        if "thinking_budget" in budget_config:
            configurable["thinking_budget"] = budget_config["thinking_budget"]
    
    if configurable:
        config["configurable"] = configurable
    return config


@traceable(name="Router Node", run_type="chain")
async def router_node(state: AgentState) -> AgentState:
    """
    Classifies the user's intent and reforms the query for context resolution.
    Uses temperature=0 for deterministic routing.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()

    try:
        model = settings.model_registry.router
        # Force temperature=0 for deterministic routing
        config = _get_model_config(state, override_temp=0)
        
        system_prompt = SystemMessage(content=get_router_prompt())
        response = await model.ainvoke([system_prompt] + state["messages"], config=config)

        logger.info(
            f"🎯 Router: intent={response.intent}, title={response.title}",
            extra={
                "component": "router",
                "session_id": state.get("session_id"),
                "intent": response.intent,
                "reformed_query": response.reformed_query[:100] if response.reformed_query else None,
            },
        )

        return {
            "intent": response.intent,
            "title": response.title,
            "reformed_query": response.reformed_query,
        }

    except Exception as e:
        logger.error(f"❌ Router node failed: {e}", exc_info=True)
        raise


@traceable(name="QA Node", run_type="chain")
async def qa_node(state: AgentState) -> AgentState:
    """
    Handles general QA interactions.
    This node streams its response.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()

    try:
        model = settings.model_registry.qa_model
        config = _get_model_config(state)
        
        system_prompt = SystemMessage(content=get_qa_assistant_prompt())
        
        # Non-streaming invocation - streaming will be handled at the graph level
        response_msg = await model.ainvoke([system_prompt] + state["messages"], config=config)

        logger.info(
            "💬 QA response generated",
            extra={
                "component": "qa_node",
                "session_id": state.get("session_id"),
                "response_length": len(response_msg.content) if response_msg.content else 0,
            },
        )

        return {
            "response": str(response_msg.content),
            "messages": [response_msg],
        }

    except Exception as e:
        logger.error(f"❌ QA node failed: {e}", exc_info=True)
        raise


@traceable(name="SQL Generator Node", run_type="chain")
async def sql_generator_node(state: AgentState) -> AgentState:
    """
    Generates SQL queries based on the user's reformed query.
    Uses temperature=0 for deterministic SQL generation.
    Calls the BigQuery tool to execute the query.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()

    try:
        model = settings.model_registry.sql_generator
        # Force temperature=0 for deterministic SQL generation
        config = _get_model_config(state, override_temp=0)
        
        # Get tables description from BigQuery handler
        tables_description = settings.bigquery_handler.tables_description
        attempt_history = state.get("attempt_history", [])
        
        system_prompt = SystemMessage(
            content=get_sql_generator_prompt(
                tables_description=tables_description,
                attempt_history=attempt_history,
            )
        )
        
        # Use the reformed query for SQL generation
        reformed_query = state.get("reformed_query") or state.get("query", "")
        user_message = HumanMessage(content=reformed_query)
        
        # Generate SQL
        response_msg = await model.ainvoke([system_prompt, user_message], config=config)
        
        # Clean the SQL output (remove markdown formatting if present)
        generated_sql = clean_sql_output(response_msg.content)
        
        logger.info(
            f"📝 SQL generated",
            extra={
                "component": "sql_generator",
                "session_id": state.get("session_id"),
                "sql_preview": generated_sql[:200] if generated_sql else None,
            },
        )
        
        # Execute the SQL using the tool
        result = execute_bigquery_sql.invoke({"sql_query": generated_sql})
        
        if result["success"]:
            return {
                "generated_sql": generated_sql,
                "sql_result": str(result["data"]),
                "n_iterations": state.get("n_iterations", 0) + 1,
            }
        else:
            # SQL execution failed - add to attempt history for retry
            new_attempt = Attempt(sql=generated_sql, error=result["error"])
            updated_history = list(attempt_history) + [new_attempt]
            
            return {
                "generated_sql": generated_sql,
                "sql_result": None,
                "attempt_history": updated_history,
                "n_iterations": state.get("n_iterations", 0) + 1,
            }

    except Exception as e:
        logger.error(f"❌ SQL generator node failed: {e}", exc_info=True)
        raise


@traceable(name="Response Synthesizer Node", run_type="chain")
async def response_synthesizer_node(state: AgentState) -> AgentState:
    """
    Synthesizes the final response from SQL results.
    Uses the user's temperature setting for response generation.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()

    try:
        model = settings.model_registry.response_synthesizer
        config = _get_model_config(state)
        
        system_prompt = SystemMessage(content=get_response_synthesizer_prompt())
        
        # Build context with query and data
        reformed_query = state.get("reformed_query") or state.get("query", "")
        sql_result = state.get("sql_result", "No data available")
        
        user_content = f"""
**User Question:** {reformed_query}

**Data Results:**
{sql_result}
"""
        user_message = HumanMessage(content=user_content)
        
        # Non-streaming invocation - streaming will be handled at the graph level
        response_msg = await model.ainvoke([system_prompt, user_message], config=config)

        logger.info(
            "📊 Response synthesized",
            extra={
                "component": "response_synthesizer",
                "session_id": state.get("session_id"),
                "response_length": len(response_msg.content) if response_msg.content else 0,
            },
        )

        return {
            "response": str(response_msg.content),
            "messages": [AIMessage(content=str(response_msg.content))],
        }

    except Exception as e:
        logger.error(f"❌ Response synthesizer node failed: {e}", exc_info=True)
        raise


@traceable(name="Error Handler Node", run_type="chain")
async def error_handler_node(state: AgentState) -> AgentState:
    """
    Handles cases where SQL generation has exhausted all retries.
    """
    attempt_history = state.get("attempt_history", [])
    
    error_response = (
        "I apologize, but I was unable to retrieve the data you requested after multiple attempts. "
        "The database query encountered errors. Please try rephrasing your question or contact support if the issue persists."
    )
    
    if attempt_history:
        last_error = attempt_history[-1].get("error", "Unknown error")
        error_response += f"\n\n**Last Error:** {last_error[:200]}"
    
    logger.warning(
        f"⚠️ SQL generation exhausted all retries",
        extra={
            "component": "error_handler",
            "session_id": state.get("session_id"),
            "attempts": len(attempt_history),
        },
    )
    
    return {
        "response": error_response,
        "messages": [AIMessage(content=error_response)],
    }


def route_by_intent(state: AgentState) -> Literal["qa_node", "sql_generator_node"]:
    """Router logic to decide the next node based on classified intent."""
    intent = state.get("intent")
    
    if intent == "sql_agent":
        return "sql_generator_node"
    elif intent == "qa_bot":
        return "qa_node"
    else:
        # Fallback to QA for unknown intents
        logger.warning(f"Unknown intent '{intent}', defaulting to qa_node")
        return "qa_node"


def should_retry_sql(state: AgentState) -> Literal["sql_generator_node", "response_synthesizer_node", "error_handler_node"]:
    """
    Determine if SQL generation should be retried or proceed to synthesis.
    """
    sql_result = state.get("sql_result")
    n_iterations = state.get("n_iterations", 0)
    
    # If we have a result, proceed to synthesis
    if sql_result is not None:
        return "response_synthesizer_node"
    
    # If we've exhausted retries, go to error handler
    if n_iterations >= MAX_ITERATIONS:
        return "error_handler_node"
    
    # Otherwise, retry SQL generation
    return "sql_generator_node"

