from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, ORJSONResponse
from analyst_9000.backend.schemas.api_schemas import (
    ChatCompletionRequest,
    ChatSessionListResponse,
    ChatSessionDetailResponse,
    ChatSessionSummaryResponse,
)
from analyst_9000.backend.services.chatbot.chatbot_service import llm_chat_completion_stream
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.core.constants import ANALYST_LOGGER

logger = get_logger(ANALYST_LOGGER)

router = APIRouter(
    prefix="/chatbot",
    tags=["chatbot"],
)


@router.post(
    "/llm_chat_completion",
    response_class=StreamingResponse,
    summary="Chat completion via LLM (streaming)",
    description="Process user query through the Analyst-9000 agent with streaming response",
)
async def llm_chat_completion(request: ChatCompletionRequest):
    """
    LLM chat completion endpoint with streaming response.
    
    The response is Server-Sent Events (SSE) formatted:
    - "data: TITLE: <title>\\n\\n" - Session title (first message only)
    - "data: <token>\\n\\n" - Response tokens
    - "data: [DONE]\\n\\n" - Stream completion
    """
    return StreamingResponse(
        llm_chat_completion_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  
        }
    )


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    response_class=ORJSONResponse,
    summary="List all chat sessions",
    description="Get a list of all chat sessions ordered by last update",
)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum sessions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """List all chat sessions with pagination."""
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()
    
    store = settings.session_store
    if store is None:
        raise HTTPException(status_code=500, detail="Session store not initialized")
    
    try:
        sessions = await store.list_sessions(limit=limit, offset=offset)
        return ChatSessionListResponse(
            sessions=[
                ChatSessionSummaryResponse(
                    id=s.id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=s.message_count,
                )
                for s in sessions
            ],
            total=len(sessions),
        )
    except Exception as e:
        logger.error(f"❌ Failed to list sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    response_class=ORJSONResponse,
    summary="Get chat session details",
    description="Get full details of a specific chat session including all messages",
)
async def get_session(session_id: str):
    """Get detailed session information including all messages."""
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()
    
    store = settings.session_store
    if store is None:
        raise HTTPException(status_code=500, detail="Session store not initialized")
    
    try:
        session = await store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return ChatSessionDetailResponse(
            id=session.id,
            title=session.title,
            messages=[
                m.model_dump() if hasattr(m, 'model_dump') else m 
                for m in session.messages
            ],
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.delete(
    "/sessions/{session_id}",
    response_class=ORJSONResponse,
    summary="Delete a chat session",
    description="Soft delete a chat session (marks as inactive)",
)
async def delete_session(session_id: str):
    """Delete (deactivate) a chat session."""
    from analyst_9000.backend.core.config import get_settings
    settings = get_settings()
    
    store = settings.session_store
    if store is None:
        raise HTTPException(status_code=500, detail="Session store not initialized")
    
    try:
        success = await store.delete_session(session_id)
        if success:
            return {"status": "deleted", "session_id": session_id}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session")
