from pydantic import BaseModel, Field
from typing import Optional, Literal


class RouterResponse(BaseModel):

    intent: Literal["sql_agent", "qa_bot"] = Field(
        ..., description="Destination for the query: 'sql_agent' or 'qa_bot'"
    )
    reformed_query: str = Field(
        ...,
        description="The user’s last message rewritten as a standalone, self-contained question",
    )
    title: Optional[str] = Field(
        None,
        description="Short summary title (3–10 words), only present if this is the very first user message",
    )
