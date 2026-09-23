from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User message capped at 4000 chars.",
    )
    session_id: str = Field(..., min_length=1, max_length=128)
    model: str | None = "openai/gpt-oss-120b"
    deep_think: bool | None = True


class ChatResponse(BaseModel):
    answer: str
    used_metadata: dict
