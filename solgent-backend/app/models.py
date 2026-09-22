from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal

RoleType = Literal["system", "user", "assistant"]

class MessageSchema(BaseModel):
    role: RoleType
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = "openai/gpt-oss-120b"
    deep_think: Optional[bool] = True

class ChatResponse(BaseModel):
    answer: str
    used_metadata: Dict[str, Any]