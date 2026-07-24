"""
Document model - Uploaded and synced documents with processing metadata.
"""

from sqlalchemy import String, Text, Integer, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base, UUIDMixin, TimestampMixin
import uuid
import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING_TEXT = "extracting_text"
    RUNNING_OCR = "running_ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentSource(str, enum.Enum):
    UPLOAD = "upload"
    OBSIDIAN = "obsidian"
    ARXIV = "arxiv"
    NEWS = "news"
    URL = "url"


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)

    # File info
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=True)  # pdf, md, docx, txt
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # bytes

    # Processing status
    status: Mapped[str] = mapped_column(
        SAEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Source tracking
    source: Mapped[str] = mapped_column(
        SAEnum(DocumentSource),
        default=DocumentSource.UPLOAD,
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(String(2000), nullable=True)

    # Processing metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=True)

    # OCR metadata
    ocr_applied: Mapped[bool] = mapped_column(default=False)
    ocr_confidence: Mapped[float] = mapped_column(nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    has_tables: Mapped[bool] = mapped_column(default=False)
    has_images: Mapped[bool] = mapped_column(default=False)

    # Obsidian sync
    obsidian_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    obsidian_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="documents")

    # ChromaDB collection reference
    collection_id: Mapped[str] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<Document '{self.title}' [{self.status}]>"
