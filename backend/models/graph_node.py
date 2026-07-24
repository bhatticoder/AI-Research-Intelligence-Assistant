"""
Knowledge Graph models - Nodes and Edges for document relationships.
"""

from sqlalchemy import String, Text, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base, UUIDMixin, TimestampMixin
import uuid


class GraphNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "graph_nodes"

    label: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)  # entity, concept, person, org, topic
    description: Mapped[str] = mapped_column(Text, nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Source document
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Frequency / importance
    mention_count: Mapped[int] = mapped_column(default=1)

    def __repr__(self):
        return f"<GraphNode '{self.label}' [{self.node_type}]>"


class GraphEdge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation_type", name="uq_edge"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graph_nodes.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("graph_nodes.id"), nullable=False)

    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)  # related_to, mentions, cites, etc.
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Source document where this relationship was found
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<GraphEdge {self.source_id} --[{self.relation_type}]--> {self.target_id}>"
