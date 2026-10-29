from typing import Literal

from pydantic import BaseModel, Field


class JobAssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class JobAssistantChatRequest(BaseModel):
    messages: list[JobAssistantMessage] = Field(min_length=1, max_length=30)
    action: Literal["message", "generate"] = "message"


class JobAssistantChatResponse(BaseModel):
    assistant_message: str
    job_id: int | None = None
    status: Literal["chatting", "needs_details", "draft_created"]
