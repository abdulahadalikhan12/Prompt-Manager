from typing import Optional, Literal
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class GenerateRequest(BaseModel):
    messages: list[ChatMessage]
    model: Optional[str] = None       # overrides the .env model chain if provided
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False              # if true, /generate returns an SSE stream instead of JSON


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class GenerateResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage
    finish_reason: Optional[str] = None


class SummarizeRequest(BaseModel):
    messages: list[ChatMessage]


class SummarizeResponse(BaseModel):
    summary: str
    model: str
