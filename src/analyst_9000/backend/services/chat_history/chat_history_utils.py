import uuid
from typing import List
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from analyst_9000.backend.helpers.utils import utcnow
from analyst_9000.backend.schemas.db_schemas import Message


def format_new_message(content: str, role: str = "user") -> Message:
    """Format a new message with metadata."""
    return Message(
        role=role,
        content=content,
        timestamp=utcnow().isoformat(),
        message_id=str(uuid.uuid4()),
    )


def convert_memory_to_langchain_messages(messages: List[Message]) -> List[AnyMessage]:
    """Convert stored messages to LangChain message objects."""
    lc_messages: List[AnyMessage] = []
    for m in messages:
        content = m.content if isinstance(m, Message) else m.get("content", "")
        role = m.role if isinstance(m, Message) else m.get("role", "")
        
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
    return lc_messages
