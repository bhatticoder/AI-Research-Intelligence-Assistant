"""
Report model - Generated research reports.
"""

from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base, UUIDMixin, TimestampMixin
import uuid


class Report(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reports"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="markdown")  # markdown, pdf, html
    template: Mapped[str] = mapped_column(String(100), default="default")

    # Generation metadata
    query: Mapped[str] = mapped_column(Text, nullable=True)  # Original query/prompt
    sources_used: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)

    # File
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)

    # Owner
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report '{self.title}' [{self.format}]>"
