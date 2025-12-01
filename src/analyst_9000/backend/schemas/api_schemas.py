from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import uuid
from datetime import datetime


class ReasoningBudget(str, Enum):
    """Enum for reasoning budget."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChatCompletionRequest(BaseModel):
    """Schema for LLM chat completion requests."""

    prompt: str = Field(..., description="The user's prompt for the LLM")
    id: Optional[str] = Field(
        default=str(uuid.uuid4()), description="The id of the chat session"
    )
    reasoning_budget: ReasoningBudget = Field(
        default=ReasoningBudget.LOW,
        description="The reasoning effort/budget allowed for the model.",
    )


class ChatCompletionResponse(BaseModel):
    """Schema for LLM chat completion responses."""

    response: str = Field(..., description="The LLM's response to the prompt")
    title: Optional[str] = Field(
        default=None, description="The title of the conversation (set on first message)"
    )


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    timestamp: datetime
    version: str
    python_version: str
    platform: str
