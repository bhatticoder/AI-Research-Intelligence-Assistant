"""
Chat Routes - RAG-powered chat with streaming and conversation history.
"""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.conversation import Conversation, Message
from routes.auth import get_current_user
from services.rag import RAGService

router = APIRouter(prefix="/api/chat", tags=["Chat"])
rag_service = RAGService()


# ── Schemas ───────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    model: Optional[str] = None
    n_results: int = 5

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    conversation_id: UUID
    model: Optional[str]
    tokens_used: Optional[int]

class ConversationResponse(BaseModel):
    id: UUID
    title: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get a RAG-powered response."""
    # Get or create conversation
    conversation = None
    if request.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.owner_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(
            title=request.message[:100],
            owner_id=current_user.id,
        )
        db.add(conversation)
        await db.flush()

    # Get conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    # Save user message
    user_msg = Message(
        role="user",
        content=request.message,
        conversation_id=conversation.id,
    )
    db.add(user_msg)

    # Run RAG pipeline
    result = await rag_service.query(
        question=request.message,
        n_results=request.n_results,
        model=request.model,
        conversation_history=history,
    )

    # Save assistant message
    assistant_msg = Message(
        role="assistant",
        content=result["answer"],
        sources=result["sources"],
        context_chunks=result.get("context_chunks", []),
        model_used=result.get("model"),
        tokens_used=result.get("tokens_used"),
        conversation_id=conversation.id,
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        conversation_id=conversation.id,
        model=result.get("model"),
        tokens_used=result.get("tokens_used"),
    )


@router.get("/history", response_model=list[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()

    responses = []
    for c in convos:
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == c.id)
        )
        msg_count = len(msg_result.scalars().all())
        responses.append(ConversationResponse(
            id=c.id,
            title=c.title,
            message_count=msg_count,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        ))
    return responses


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "model_used": m.model_used,
            "tokens_used": m.tokens_used,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/{conversation_id}/clear")
async def clear_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all messages in a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id == current_user.id,
        )
    )
    convo = result.scalar_one_or_none()
    if not convo:
        raise HTTPException(404, "Conversation not found")

    await db.delete(convo)
    return {"message": "Conversation cleared"}
