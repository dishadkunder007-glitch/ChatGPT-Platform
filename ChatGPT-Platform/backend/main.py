import os
import json
import uuid
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from database import init_db, get_db, SessionLocal, User, Conversation, Message, Document, DocumentChunk, PasswordResetToken
from models import (
    UserRegister, UserLogin, GoogleAuthRequest, TokenResponse, UserProfileUpdate,
    PasswordResetRequest, PasswordResetConfirm, PasswordChangeRequest,
    ConversationCreate, ConversationRename,
    ConversationOut, MessageOut, ChatStreamRequest, RegenerateRequest,
    EditMessageRequest, FeedbackRequest, DocumentOut
)
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_authenticated_user, verify_google_token,
    generate_reset_token
)
from rag import build_rag_context, get_user_vector_store, reload_user_vector_store, clear_user_vector_store, purge_all_vector_stores
from ollama_client import stream_ollama_or_fallback
from document_processor import extract_text_from_file
from email_service import send_password_reset_email
# Initialize DB schema
init_db()
# Flush any stale vector store caches on start
purge_all_vector_stores()

app = FastAPI(title="ChatGPT-Style AI Platform API", version="4.0.0")

# ─── CORS ─────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://chat-gpt-platform.vercel.app",
]

env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    ALLOWED_ORIGINS.extend([origin.strip() for origin in env_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health & Models ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ChatGPT-Style AI Platform",
        "version": "4.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


@app.get("/api/models")
def get_available_models():
    return [
        {
            "id": "Qwen/Qwen2.5-1.5B-Instruct",
            "name": "Qwen 2.5 1.5B Instruct",
            "badge": "🤖 Local",
            "provider": "Local (HuggingFace)",
            "description": "Best quality local model — accurate, multilingual, instruction-tuned. ~3GB RAM.",
            "context_length": 4096,
            "is_default": True
        },
        {
            "id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "name": "TinyLlama 1.1B Chat",
            "badge": "⚡ Fastest",
            "provider": "Local (HuggingFace)",
            "description": "Smallest and fastest local model. Great for quick answers. ~2GB RAM.",
            "context_length": 2048,
            "is_default": False
        },
        {
            "id": "gpt2",
            "name": "GPT-2 (124M)",
            "badge": "🟢 Tiny",
            "provider": "Local (HuggingFace)",
            "description": "OpenAI GPT-2 base model. Minimal RAM usage (~500MB). Good for testing.",
            "context_length": 1024,
            "is_default": False
        },
        {
            "id": "distilgpt2",
            "name": "DistilGPT-2 (82M)",
            "badge": "🔬 Micro",
            "provider": "Local (HuggingFace)",
            "description": "Distilled GPT-2. Ultra lightweight (~300MB). Best for low-RAM machines.",
            "context_length": 1024,
            "is_default": False
        }
    ]




# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        email=req.email.lower(),
        name=req.name.strip(),
        hashed_password=get_password_hash(req.password),
        is_guest=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_guest": False,
            "avatar_url": user.avatar_url,
            "preferred_model": user.preferred_model,
            "system_prompt": user.system_prompt,
        }
    }


@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_guest": user.is_guest,
            "avatar_url": user.avatar_url,
            "custom_api_key": user.custom_api_key,
            "preferred_model": user.preferred_model,
            "system_prompt": user.system_prompt,
        }
    }


@app.post("/api/auth/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Accepts a Google ID token or Firebase authentication details.
    Verifies it if possible and creates/updates user.
    """
    email = req.email
    name = req.name or "Google User"
    avatar_url = req.avatar_url
    google_sub_id = None

    # If credential is provided (Google ID token, GSI, or Firebase ID token), verify and extract claims
    if req.credential and len(req.credential) > 20:
        try:
            payload = await verify_google_token(req.credential)
            if payload:
                email = payload.get("email", email)
                name = payload.get("name", name)
                avatar_url = payload.get("picture", avatar_url)
                google_sub_id = payload.get("sub") or payload.get("user_id")
        except Exception:
            try:
                unverified = jwt.decode(req.credential, options={"verify_signature": False})
                email = unverified.get("email", email)
                name = unverified.get("name", name)
                avatar_url = unverified.get("picture", avatar_url)
                google_sub_id = unverified.get("sub") or unverified.get("user_id")
            except Exception:
                pass

    if not email:
        raise HTTPException(status_code=400, detail="Email is required for Google sign-in")

    user = None
    if req.firebase_uid:
        user = db.query(User).filter(User.firebase_uid == req.firebase_uid).first()
    if not user and google_sub_id:
        user = db.query(User).filter(User.google_id == google_sub_id).first()
    if not user:
        user = db.query(User).filter(User.email == email.lower()).first()

    if not user:
        user = User(
            email=email.lower(),
            name=name,
            avatar_url=avatar_url,
            google_id=google_sub_id,
            firebase_uid=req.firebase_uid,
            is_guest=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update details if available
        updated = False
        if req.firebase_uid and not user.firebase_uid:
            user.firebase_uid = req.firebase_uid
            updated = True
        if google_sub_id and not user.google_id:
            user.google_id = google_sub_id
            updated = True
        if avatar_url and (not user.avatar_url or user.avatar_url != avatar_url):
            user.avatar_url = avatar_url
            updated = True
        if name and user.name in ["Google User", "Guest User", ""]:
            user.name = name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "firebase_uid": user.firebase_uid,
            "email": user.email,
            "name": user.name,
            "is_guest": False,
            "avatar_url": user.avatar_url,
            "preferred_model": user.preferred_model,
            "system_prompt": user.system_prompt,
        }
    }


@app.get("/api/auth/guest", response_model=TokenResponse)
def guest_login(db: Session = Depends(get_db)):
    guest = db.query(User).filter(User.email == "guest@chatgpt-platform.local").first()
    if not guest:
        guest = User(
            email="guest@chatgpt-platform.local",
            name="Guest User",
            is_guest=True,
            is_active=True
        )
        db.add(guest)
        db.commit()
        db.refresh(guest)

    token = create_access_token({"sub": str(guest.id), "email": guest.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": guest.id,
            "email": guest.email,
            "name": guest.name,
            "is_guest": True,
            "avatar_url": None,
            "preferred_model": guest.preferred_model,
        }
    }


@app.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "firebase_uid": user.firebase_uid,
        "email": user.email,
        "name": user.name,
        "is_guest": user.is_guest,
        "avatar_url": user.avatar_url,
        "custom_api_key": user.custom_api_key,
        "preferred_model": user.preferred_model,
        "system_prompt": user.system_prompt,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.put("/api/auth/profile")
def update_profile(
    req: UserProfileUpdate,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    if req.name is not None:
        user.name = req.name.strip()
    if req.custom_api_key is not None:
        user.custom_api_key = req.custom_api_key or None
    if req.preferred_model is not None:
        user.preferred_model = req.preferred_model
    if req.system_prompt is not None:
        user.system_prompt = req.system_prompt
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url or None
    db.commit()
    db.refresh(user)
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "firebase_uid": user.firebase_uid,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "preferred_model": user.preferred_model,
            "system_prompt": user.system_prompt,
        }
    }


@app.put("/api/auth/change-password")
@app.post("/api/auth/change-password")
def change_password(
    req: PasswordChangeRequest,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password changed successfully"}


@app.post("/api/auth/password-reset/request")
@app.post("/api/auth/reset-password/request")
def request_password_reset(req: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()

    # Always return success (don't leak whether email exists)
    if not user or user.is_guest:
        return {"status": "success", "message": "If the email exists, a reset link has been sent."}

    # Expire old tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})
    db.commit()

    # Create new token (1 hour expiry)
    token_str = generate_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_str,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    )
    db.add(reset_token)
    db.commit()

    # Send email
    send_password_reset_email(user.email, user.name, token_str)

    return {"status": "success", "message": "If the email exists, a reset link has been sent."}


@app.post("/api/auth/password-reset/confirm")
@app.post("/api/auth/reset-password/confirm")
def confirm_password_reset(req: PasswordResetConfirm, db: Session = Depends(get_db)):
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if reset_token.expires_at < datetime.datetime.utcnow():
        reset_token.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(req.new_password)
    reset_token.used = True
    db.commit()

    return {"status": "success", "message": "Password has been reset successfully. You can now log in."}


@app.delete("/api/auth/account")
def delete_account(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    db.delete(user)
    db.commit()
    return {"status": "success", "message": "Account deleted successfully"}


# ─── Conversations ────────────────────────────────────────────────────────────

@app.get("/api/conversations")
def list_conversations(
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Conversation).filter(Conversation.user_id == user.id)
    if search:
        query = query.filter(
            or_(
                Conversation.title.ilike(f"%{search}%"),
            )
        )

    convs = query.order_by(desc(Conversation.updated_at)).all()

    result = []
    for c in convs:
        last_msg = db.query(Message).filter(
            Message.conversation_id == c.id
        ).order_by(desc(Message.created_at)).first()
        result.append({
            "id": c.id,
            "title": c.title,
            "model": c.model,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": len(c.messages),
            "preview": (last_msg.content[:80] if last_msg else "New chat...")
        })
    return result


@app.post("/api/conversations")
def create_conversation(
    req: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = Conversation(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=req.title or "New Chat",
        model=req.model or "qwen2.5:1.5b"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "model": conv.model,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "message_count": 0,
        "preview": "New chat..."
    }


@app.put("/api/conversations/{conv_id}")
def rename_conversation(
    conv_id: str,
    req: ConversationRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = req.title.strip()[:200]
    db.commit()
    return {"status": "success", "id": conv.id, "title": conv.title}


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(
    conv_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"status": "success", "deleted_id": conv_id}


@app.get("/api/conversations/{conv_id}/messages")
def get_messages(
    conv_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = db.query(Message).filter(
        Message.conversation_id == conv_id
    ).order_by(Message.created_at).all()

    return [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "model": m.model,
            "citations": json.loads(m.citations) if m.citations else None,
            "feedback": m.feedback,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]


# ─── Streaming Chat ───────────────────────────────────────────────────────────

@app.post("/api/chat/stream")
async def chat_stream(
    req: ChatStreamRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Resolve or create conversation
    conv_id = req.conversation_id

    if not conv_id:
        title_snippet = req.message.strip()[:50] or "New Chat"
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title=title_snippet,
            model=req.model or "qwen2.5:1.5b"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id
    else:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.user_id == user.id
        ).first()

        if not conv:
            conv = Conversation(
                id=conv_id,
                user_id=user.id,
                title=req.message.strip()[:50] or "New Chat",
                model=req.model or "qwen2.5:1.5b"
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
        elif conv.title in ["New Chat", ""] and len(conv.messages) <= 2:
            conv.title = req.message.strip()[:50]
            db.commit()

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=req.message
    )
    db.add(user_msg)
    db.commit()

    # Build history
    history_messages = db.query(Message).filter(
        Message.conversation_id == conv_id
    ).order_by(Message.created_at).all()

    formatted_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages
    ]

    # RAG retrieval
    rag_context, citations = "", []

    if req.use_rag:
        rag_context, citations = build_rag_context(
            user.id,
            req.message,
            top_k=3,
            db=db
        )

    assistant_msg_id = str(uuid.uuid4())

    # Generate complete Qwen response
    full_response_parts = []

    async for chunk_json in stream_ollama_or_fallback(
        messages=formatted_history,
        model_name=req.model or conv.model or "qwen2.5:1.5b",
        custom_api_key=user.custom_api_key,
        system_prompt=req.system_prompt or user.system_prompt,
        rag_context=rag_context,
        temperature=req.temperature or 0.7
    ):
        try:
            parsed = json.loads(chunk_json)
            token = parsed.get("token", "")
            full_response_parts.append(token)
        except Exception:
            continue

    full_content = "".join(full_response_parts)

    # Save assistant message
    with SessionLocal() as db_session:
        assistant_msg = Message(
            id=assistant_msg_id,
            conversation_id=conv_id,
            role="assistant",
            content=full_content,
            model=req.model or conv.model or "qwen2.5:1.5b",
            citations=json.dumps(citations) if citations else None
        )

        db_session.add(assistant_msg)

        conv_obj = db_session.query(Conversation).filter(
            Conversation.id == conv_id
        ).first()

        if conv_obj:
            conv_obj.updated_at = datetime.datetime.utcnow()

        db_session.commit()

    return {
        "conversation_id": conv_id,
        "user_msg_id": user_msg.id,
        "assistant_msg_id": assistant_msg_id,
        "citations": citations,
        "full_content": full_content
    }


@app.post("/api/chat/regenerate")
async def regenerate_response(
    req: RegenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the last assistant message and re-stream a fresh response."""
    conv = db.query(Conversation).filter(
        Conversation.id == req.conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete the specified assistant message (and any after it)
    target_msg = db.query(Message).filter(Message.id == req.message_id).first()
    if target_msg:
        msgs_to_delete = db.query(Message).filter(
            Message.conversation_id == req.conversation_id,
            Message.created_at >= target_msg.created_at
        ).all()
        for m in msgs_to_delete:
            db.delete(m)
        db.commit()

    # Rebuild history
    history_messages = db.query(Message).filter(
        Message.conversation_id == req.conversation_id
    ).order_by(Message.created_at).all()
    formatted_history = [{"role": m.role, "content": m.content} for m in history_messages]

    # RAG
    last_user_msg = next((m for m in reversed(history_messages) if m.role == "user"), None)
    rag_context, citations = "", []
    if last_user_msg:
        rag_context, citations = build_rag_context(user.id, last_user_msg.content, top_k=3, db=db)

    new_assistant_msg_id = str(uuid.uuid4())
    full_response_parts = []

    async for chunk_json in stream_ollama_or_fallback(
        messages=formatted_history,
        model_name=req.model or conv.model or "qwen2.5:1.5b",
        custom_api_key=user.custom_api_key,
        system_prompt=req.system_prompt or user.system_prompt,
        rag_context=rag_context,
        temperature=req.temperature or 0.7
    ):
        try:
            parsed = json.loads(chunk_json)
            token = parsed.get("token", "")
            if token:
                full_response_parts.append(token)
        except Exception:
            continue

    full_content = "".join(full_response_parts)

    with SessionLocal() as db_session:
        assistant_msg = Message(
            id=new_assistant_msg_id,
            conversation_id=req.conversation_id,
            role="assistant",
            content=full_content,
            model=req.model or conv.model or "qwen2.5:1.5b",
            citations=json.dumps(citations) if citations else None
        )
        db_session.add(assistant_msg)
        conv_obj = db_session.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if conv_obj:
            conv_obj.updated_at = datetime.datetime.utcnow()
        db_session.commit()

    return {
        "conversation_id": req.conversation_id,
        "assistant_msg_id": new_assistant_msg_id,
        "citations": citations,
        "full_content": full_content
    }


@app.post("/api/chat/edit")
async def edit_and_resubmit(
    req: EditMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a user message and delete all subsequent messages, then re-generate."""
    conv = db.query(Conversation).filter(
        Conversation.id == req.conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    target_msg = db.query(Message).filter(Message.id == req.message_id).first()
    if not target_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # Update the user message content
    target_msg.content = req.new_content

    # Delete all messages after the edited message
    msgs_after = db.query(Message).filter(
        Message.conversation_id == req.conversation_id,
        Message.created_at > target_msg.created_at
    ).all()
    for m in msgs_after:
        db.delete(m)
    db.commit()

    # Rebuild history including the edited message
    history_messages = db.query(Message).filter(
        Message.conversation_id == req.conversation_id
    ).order_by(Message.created_at).all()
    formatted_history = [{"role": m.role, "content": m.content} for m in history_messages]

    rag_context, citations = build_rag_context(user.id, req.new_content, top_k=3, db=db)

    new_assistant_msg_id = str(uuid.uuid4())
    full_response_parts = []

    async for chunk_json in stream_ollama_or_fallback(
        messages=formatted_history,
        model_name=req.model or conv.model or "qwen2.5:1.5b",
        custom_api_key=user.custom_api_key,
        system_prompt=req.system_prompt or user.system_prompt,
        rag_context=rag_context,
        temperature=req.temperature or 0.7
    ):
        try:
            parsed = json.loads(chunk_json)
            token = parsed.get("token", "")
            if token:
                full_response_parts.append(token)
        except Exception:
            continue

    full_content = "".join(full_response_parts)

    with SessionLocal() as db_session:
        assistant_msg = Message(
            id=new_assistant_msg_id,
            conversation_id=req.conversation_id,
            role="assistant",
            content=full_content,
            model=req.model or conv.model or "qwen2.5:1.5b",
            citations=json.dumps(citations) if citations else None
        )
        db_session.add(assistant_msg)
        conv_obj = db_session.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if conv_obj:
            conv_obj.updated_at = datetime.datetime.utcnow()
        db_session.commit()

    return {
        "conversation_id": req.conversation_id,
        "assistant_msg_id": new_assistant_msg_id,
        "citations": citations,
        "full_content": full_content
    }


@app.post("/api/chat/feedback")
def set_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(Message).filter(Message.id == req.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = req.feedback
    db.commit()
    return {"status": "success", "message_id": msg.id, "feedback": msg.feedback}


# ─── Documents ────────────────────────────────────────────────────────────────

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    allowed = ["pdf", "docx", "doc", "txt", "csv", "json", "md", "png", "jpg", "jpeg", "webp", "bmp"]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{ext}'. Allowed: {', '.join(allowed)}"
        )

    content = await file.read()
    file_size = len(content)

    # Max 50MB
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")

    chunks = extract_text_from_file(content, filename)
    chunk_count = len(chunks)
    if chunk_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract any readable text from '{filename}'. Scanned or image-only documents cannot be indexed without selectable text."
        )

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=filename,
        file_type=ext,
        file_size=file_size,
        chunk_count=chunk_count
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Persist extracted chunks for RAG analysis
    for c in chunks:
        chunk_rec = DocumentChunk(
            document_id=doc.id,
            user_id=user.id,
            filename=filename,
            chunk_index=c.get("chunk_id", 0),
            page_number=c.get("page", 1),
            content=c.get("text", "")
        )
        db.add(chunk_rec)
    db.commit()

    # Index in vector store
    store = get_user_vector_store(user.id, db=db)
    store.remove_document(filename)
    store.add_chunks(chunks)

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "status": "ready"
    }


@app.get("/api/documents")
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    docs = db.query(Document).filter(
        Document.user_id == user.id
    ).order_by(desc(Document.created_at)).all()

    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@app.delete("/api/documents")
def delete_all_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes ALL documents and chunks uploaded by the user, and clears the user's vector store.
    """
    db.query(DocumentChunk).filter(DocumentChunk.user_id == user.id).delete()
    db.query(Document).filter(Document.user_id == user.id).delete()
    db.commit()
    clear_user_vector_store(user.id)
    return {"status": "success", "message": "All documents successfully deleted"}


@app.delete("/api/documents/{doc_id}")
def delete_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up chunks and vector store
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    db.delete(doc)
    db.commit()

    # Force reload of vector store from DB so removed document is completely gone
    reload_user_vector_store(user.id, db=db)
    return {"status": "success", "deleted_id": doc_id}


@app.post("/api/documents/purge-all")
def purge_all_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Completely purges all document chunks and documents across the system and flushes all vector caches.
    """
    db.query(DocumentChunk).delete()
    db.query(Document).delete()
    db.commit()
    purge_all_vector_stores()
    return {"status": "success", "message": "All documents and vector stores have been completely purged"}



# ─── Static Frontend (optional unified build) ─────────────────────────────────
static_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nextjs-frontend", "out")
if os.path.exists(static_dist_path):
    app.mount("/", StaticFiles(directory=static_dist_path, html=True), name="frontend")
