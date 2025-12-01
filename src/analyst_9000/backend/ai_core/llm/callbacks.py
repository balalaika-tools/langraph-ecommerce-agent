from langchain_core.callbacks.base import AsyncCallbackHandler
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER
from typing import List, Optional

logger = get_logger(ANALYST_LOGGER)

# Our known component tags - used to filter out LangGraph internal tags
KNOWN_COMPONENT_TAGS: List[str] = []



def _extract_component_tag(tags: Optional[List[str]]) -> str:
    """
    Extract the component tag from the tags list.
    LangGraph adds its own tags like 'seq:step:1', so we need to find our custom tags.
    """
    if not tags:
        return "ChatModel"
    
    # First, try to find one of our known tags
    for tag in tags:
        if tag in KNOWN_COMPONENT_TAGS:
            return tag
    
    # If no known tag found, filter out LangGraph internal tags and return the first non-internal one
    for tag in tags:
        if not tag.startswith("seq:") and not tag.startswith("langgraph:"):
            return tag
    
    # Fallback
    return tags[0] if tags else "ChatModel"


class LoggingHandler(AsyncCallbackHandler):
    async def on_chat_model_start(
        self,
        serialized,
        messages,
        *,
        run_id,
        parent_run_id=None,
        tags=None,
        metadata=None,
        **kwargs
    ):
        component = _extract_component_tag(tags)
        try:
            last_msg = messages[-1][-1]
            user_query = getattr(last_msg, "content", None) or getattr(last_msg, "text", "")
        except Exception as e:
            logger.error(f"❌ {component} user query extraction failed: {type(e).__name__}", exc_info=True)
            raise

        logger.info(
            f"🤖 {component} started",
            extra={
                "component": component,
                "run_id": run_id,
                "user_query": user_query[:500],  # limit for logs
                "event": f"{component}_model_start"
            }
        )

    async def on_llm_end(
        self,
        response,
        *,
        run_id,
        parent_run_id=None,
        tags=None,
        metadata=None,
        **kwargs
    ):
        component = _extract_component_tag(tags)
        try:
            # Try first using .text
            response_text = response.generations[0][0].text
            if response_text is None:
                # fallback to underlying message content
                gen = response.generations[0][0]
                msg = getattr(gen, "message", None)
                response_text = getattr(msg, "content", None) or getattr(msg, "text", "")
        except Exception as e:
            logger.error(f"❌ {component} response extraction failed: {type(e).__name__}", exc_info=True)
            raise
        
        # Extract usage_metadata safely (may not exist for structured output fallbacks)
        try:
            usage_metadata = response.generations[0][0].message.usage_metadata
        except (AttributeError, KeyError, IndexError):
            usage_metadata = None
        
        # Extract model_name safely
        try:
            model_name = response.generations[0][0].message.response_metadata.get('model_name', 'unknown')
        except (AttributeError, KeyError, IndexError):
            model_name = 'unknown'
        

        logger.info(
            f"✅ {component} completed",
            extra={
                "component": component,
                "run_id": run_id,
                "response": response_text[:500] if response_text else "",  # limit for logs
                "model_name": model_name,
                "usage_metadata": usage_metadata,
                "event": f"{component}_model_end"
            }
        )

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id,
        parent_run_id=None,
        tags=None,
        metadata=None,
        **kwargs
    ):
        component = _extract_component_tag(tags)
        resp = kwargs.get("response", None)
        print(resp)
        logger.error(
            f"❌ {component} error occurred",
            extra={
                "component": component,
                "run_id": run_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "response_before_error": str(resp) if resp else None,
                "event": f"{component}_model_error"
            },
            exc_info=error
        )
