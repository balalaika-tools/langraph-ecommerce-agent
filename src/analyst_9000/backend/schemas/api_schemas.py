from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
import uuid
from datetime import datetime


class ReasoningBudget(str, Enum):
    """Enum for reasoning budget levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelName(str, Enum):
    """Available model options."""
    GEMINI_2_5_FLASH = "google_genai:gemini-2.5-flash"
    GEMINI_2_5_PRO = "google_genai:gemini-2.5-pro"


class ChatCompletionRequest(BaseModel):
    """Schema for LLM chat completion requests."""
    prompt: str = Field(..., description="The user's prompt for the LLM")
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="The id of the chat session"
    )
    model: ModelName = Field(
        default=ModelName.GEMINI_2_5_FLASH,
        description="The model to use for the LLM",
    )
    reasoning_budget: ReasoningBudget = Field(
        default=ReasoningBudget.LOW,
        description="The reasoning effort/budget allowed for the model.",
    )
    temperature: float = Field(
        default=0.7,
        le=1.0,
        ge=0.0,
        description="The temperature of the model.",
    )


class ChatCompletionResponse(BaseModel):
    """Schema for LLM chat completion responses (non-streaming)."""
    response: str = Field(..., description="The LLM's response to the prompt")
    session_id: str = Field(..., description="The session ID for this conversation")
    title: Optional[str] = Field(
        default=None, 
        description="The title of the conversation (set on first message)"
    )


class ChatSessionSummaryResponse(BaseModel):
    """Schema for chat session summary in list responses."""
    id: str = Field(..., description="Session UUID")
    title: Optional[str] = Field(None, description="Session title")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    message_count: int = Field(..., description="Number of messages in session")


class ChatSessionListResponse(BaseModel):
    """Schema for listing chat sessions."""
    sessions: List[ChatSessionSummaryResponse] = Field(
        default_factory=list,
        description="List of chat sessions"
    )
    total: int = Field(default=0, description="Total number of sessions")


class ChatSessionDetailResponse(BaseModel):
    """Schema for detailed chat session with messages."""
    id: str = Field(..., description="Session UUID")
    title: Optional[str] = Field(None, description="Session title")
    messages: List[dict] = Field(default_factory=list, description="All messages in session")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    message_count: int = Field(..., description="Number of messages")


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    timestamp: datetime
    version: str
    python_version: str
    platform: str
