from pydantic import BaseModel, Field


class CandidateChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class CandidateChatResponse(BaseModel):
    reply: str
