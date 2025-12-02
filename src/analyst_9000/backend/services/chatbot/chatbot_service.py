from typing import AsyncIterator, Optional
from analyst_9000.backend.schemas.api_schemas import ChatCompletionRequest
from analyst_9000.backend.services.chat_history.chat_history_service import (
    get_or_create_chat_session,
    get_conversation_history,
    save_conversation,
)
from analyst_9000.backend.schemas.db_schemas import Message
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)


async def llm_chat_completion_stream(
    request: ChatCompletionRequest,
) -> AsyncIterator[str]:
    """
    Main chat completion service with streaming response.
    
    This function orchestrates:
    1. Session management (get or create)
    2. Conversation history retrieval
    3. Graph execution with streaming
    4. Conversation persistence
    
    Yields:
        SSE-formatted string events:
        - "data: TITLE: <title>\\n\\n" for session title
        - "data: <token>\\n\\n" for response tokens
        - "data: [DONE]\\n\\n" for completion
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()

    # Step 1: Handle session creation/retrieval
    try:
        session = await get_or_create_chat_session(request.id)
    except Exception as e:
        logger.error(f"❌ Failed to get or create chat session: {e}")
        yield f"data: Error: Failed to initialize session\n\n"
        yield "data: [DONE]\n\n"
        return

    session_id = session.id

    # Step 2: Handle conversation history
    messages, memory, message_count, is_first_message = await get_conversation_history(
        session, request.prompt
    )

    # Step 3: Get model configuration from request
    model_name = request.model.value if request.model else None
    temperature = request.temperature
    reasoning_budget = request.reasoning_budget.value if request.reasoning_budget else None

    # Step 4: Execute graph with streaming
    title: Optional[str] = None
    response_text = ""

    try:
        graph = settings.analyst_graph
        
        async for event in graph.stream(
            query=request.prompt,
            session_id=session_id,
            messages=memory,
            model_name=model_name,
            temperature=temperature,
            reasoning_budget=reasoning_budget,
        ):
            event_type = event.get("type")
            
            if event_type == "router":
                # Capture title if this is the first message
                if is_first_message and event.get("title"):
                    title = event["title"]
                    yield f"data: TITLE: {title}\n\n"
                
                logger.debug(f"Router event: intent={event.get('intent')}")
            
            elif event_type == "token":
                # Stream individual tokens
                content = event.get("content", "")
                response_text += content
                yield f"data: {content}\n\n"
            
            elif event_type == "sql":
                # Log SQL events (could be used for debugging)
                logger.debug(
                    f"SQL event: success={event.get('success')}, "
                    f"error={event.get('error')}"
                )
            
            elif event_type == "final":
                # Capture final response for persistence
                if not response_text and event.get("response"):
                    response_text = event["response"]
                    # If we didn't stream tokens, send the full response
                    yield f"data: {response_text}\n\n"
                
                # Capture title if not already captured
                if not title and event.get("title"):
                    title = event["title"]
                    yield f"data: TITLE: {title}\n\n"
            
            elif event_type == "error":
                error_msg = event.get("error", "Unknown error occurred")
                yield f"data: Error: {error_msg}\n\n"

    except Exception as e:
        logger.error(f"❌ Graph execution failed: {e}", exc_info=True)
        yield f"data: Error: {str(e)}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Step 5: Save conversation to database
    try:
        await save_conversation(
            session_id=session_id,
            messages=messages,
            user_query=request.prompt,
            response_text=response_text,
            title=title,
            message_count=message_count,
        )
    except Exception as e:
        logger.error(f"❌ Failed to save conversation: {e}", exc_info=True)
        # Don't fail the request if save fails

    # Signal completion
    yield "data: [DONE]\n\n"

