"""Database schemas for chat history persistence."""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
from analyst_9000.backend.helpers.utils import utcnow


class Message(BaseModel):
    """Represents a single message in a chat session."""
    role: str
    content: Union[str, Dict[str, Any]]
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
    message_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except Exception:
            raise ValueError(f"Invalid ISO-8601 timestamp: {v}")


class ChatSession(BaseModel):
    """
    Represents a chat session with full history.
    
    Note: We only store `messages` - the effective chat history for LLM
    is computed by cropping the last N messages from this list.
    """
    id: str
    title: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    message_count: int = 0
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())
    is_active: bool = True

    @field_validator("created_at", "updated_at")
    def validate_isoformat(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except Exception:
            raise ValueError(f"Invalid ISO-8601 datetime: {v}")

    class Config:
        extra = "ignore"


class ChatSessionSummary(BaseModel):
    """Summary of a chat session for listing in sidebar."""
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    message_count: int
    is_active: bool = True
