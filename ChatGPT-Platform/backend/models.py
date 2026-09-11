from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


# ─── Auth ───────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = ""  # Google/Firebase ID token
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    firebase_uid: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    custom_api_key: Optional[str] = None
    preferred_model: Optional[str] = None
    system_prompt: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# ─── Conversations ──────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = "qwen2.5:1.5b"


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0
    preview: Optional[str] = ""


# ─── Messages ───────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    model: Optional[str] = None
    citations: Optional[list] = None
    feedback: Optional[int] = 0
    created_at: Optional[str] = None


class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = "qwen2.5:1.5b"
    use_rag: Optional[bool] = True
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None


class RegenerateRequest(BaseModel):
    conversation_id: str
    message_id: str  # The assistant message to regenerate
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None


class EditMessageRequest(BaseModel):
    conversation_id: str
    message_id: str  # The user message to edit
    new_content: str
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: str
    feedback: int  # 1 = thumbs up, -1 = thumbs down, 0 = reset


# ─── Documents ──────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: str
