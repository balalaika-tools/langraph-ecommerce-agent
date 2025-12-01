from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, ORJSONResponse
import asyncio
from analyst_9000.backend.schemas.api_schemas import ChatCompletionRequest

router = APIRouter(
    prefix="/chatbot",
    tags=["chatbot"],
)


async def fake_llm_stream(user_message: str, session_id: str, is_first_message: bool = False):
    # TODO: Implement the actual LLM streaming logic, implement real LLM streaming logic here
    # Dummy generator — "stream"
    # If this is the first message, send a title
    if is_first_message:
        # Generate a simple title based on the first few words of the message
        title = user_message[:50].strip()
        if len(user_message) > 50:
            title += "..."
        yield f"data: TITLE: {title}\n\n"
    
    reply = f"Echo: {user_message[::-1]}"  
    for ch in reply:
        yield f"data: {ch}\n\n"
        await asyncio.sleep(0.05)  
    yield "data: [DONE]\n\n"

# In-memory store to track if session is new (for demo purposes)
session_store = set()
 
@router.post("/llm_chat_completion", response_class=StreamingResponse, summary="Chat completion via LLM (streaming)")
async def llm_chat_completion(request: ChatCompletionRequest):
    user_msg = request.prompt
    session_id = request.id

    # Check if this is the first message for this session
    is_first_message = session_id not in session_store
    if is_first_message:
        session_store.add(session_id)
    
    return StreamingResponse(
        fake_llm_stream(user_msg, session_id, is_first_message),
        media_type="text/event-stream"
    )
