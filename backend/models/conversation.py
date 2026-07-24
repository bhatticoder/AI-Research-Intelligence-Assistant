"""
Conversation & Message models - RAG chat history with source tracking.
"""

from sqlalchemy import String, Text, Integer, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base, UUIDMixin, TimestampMixin
import uuid


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(500), default="New Conversation")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="conversations")

    # Messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation '{self.title}'>"


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    # Content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # RAG source tracking
    sources: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    context_chunks: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)

    # Metadata
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True)
    retrieval_score: Mapped[float] = mapped_column(nullable=True)

    # Conversation FK
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message [{self.role}] {self.content[:50]}>"
