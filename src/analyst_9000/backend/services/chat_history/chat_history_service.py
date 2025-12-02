
from typing import Dict, Any, Tuple, List, Optional
from langchain_core.messages import AnyMessage, HumanMessage
from analyst_9000.backend.core.constants import MAX_HISTORY_MESSAGES, ANALYST_LOGGER
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.schemas.db_schemas import ChatSession, Message
from analyst_9000.backend.services.chat_history.chat_history_utils import (
    format_new_message,
    convert_memory_to_langchain_messages,
)
from analyst_9000.backend.helpers.utils import utcnow

logger = get_logger(ANALYST_LOGGER)


async def get_or_create_chat_session(session_id: Optional[str]) -> ChatSession:
    """
    Get or create a chat session.
    If session_id is None, creates a new session.
    If session_id is provided but not found, creates a new session with that ID.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()
    
    store = settings.session_store
    if store is None:
        raise RuntimeError("Session store not initialized")
    
    try:
        return await store.get_or_create_session(session_id)
    except Exception as e:
        logger.error(f"❌ Error getting/creating chat session: {e}", exc_info=True)
        raise


async def get_conversation_history(
    session: ChatSession, 
    user_query: str
) -> Tuple[List[Message], List[AnyMessage], int, bool]:
    """
    Build conversation history and prepare memory for LLM invocation.
    
    Simplified approach: We just crop the last N messages from the full
    message history - no separate memory field needed.
    
    Returns:
        - messages: Full list of messages (for storage, including new user message)
        - memory: LangChain messages for LLM context (cropped to MAX_HISTORY_MESSAGES)
        - message_count: Updated message count
        - is_first_message: Whether this is the first message in the session
    """
    messages = list(session.messages)
    message_count = session.message_count
    is_first_message = len(messages) == 0

    # Format the user query as a new message
    new_message = format_new_message(user_query, role="user")

    # If no previous messages, this is the first message
    if not messages:
        messages.append(new_message)
        message_count += 1
        memory = [HumanMessage(content=user_query)]
        return messages, memory, message_count, is_first_message

    # Crop messages to get effective memory (last N messages)
    cropped_messages = messages[-MAX_HISTORY_MESSAGES:] if len(messages) > MAX_HISTORY_MESSAGES else messages
    
    # Convert to LangChain messages
    memory = convert_memory_to_langchain_messages(cropped_messages)

    # Append the new user query to both lists
    messages.append(new_message)
    memory.append(HumanMessage(content=user_query))
    message_count += 1

    return messages, memory, message_count, is_first_message


async def save_conversation(
    session_id: str,
    messages: List[Message],
    user_query: str,
    response_text: str,
    title: Optional[str],
    message_count: int,
) -> None:
    """
    Save the conversation update to the database.
    
    Simple flow: Just append the assistant response to messages and save.
    """
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()
    
    store = settings.session_store
    if store is None:
        raise RuntimeError("Session store not initialized")
    
    try:
        # Add assistant response to messages
        assistant_message = format_new_message(response_text, role="assistant")
        messages.append(assistant_message)

        # Prepare update data
        update_data: Dict[str, Any] = {
            "messages": [m.model_dump() if hasattr(m, 'model_dump') else m for m in messages],
            "message_count": message_count + 1,
            "updated_at": utcnow().isoformat(),
        }

        if title:
            update_data["title"] = title

        # Update the session in store
        await store.update_session(session_id, update_data)
        logger.info(f"💾 Conversation saved for session {session_id}")

    except Exception as e:
        logger.error(f"❌ Failed to save conversation: {e}", exc_info=True)
        # Don't raise - we still want to return the response even if save fails
