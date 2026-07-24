"""
Graph Routes - Knowledge graph visualization and entity connections.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from models.user import User
from routes.auth import get_current_user
from services.knowledge_graph import KnowledgeGraphService

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])
graph_service = KnowledgeGraphService()


@router.get("/nodes")
async def get_graph_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all graph nodes and edges for visualization."""
    return await graph_service.get_graph_data_async(db_session=db, owner_id=str(current_user.id))


@router.get("/connections/{entity_label}")
async def get_connections(
    entity_label: str,
    depth: int = Query(2, ge=1, le=5),
    current_user: User = Depends(get_current_user),
):
    """Find connections for an entity."""
    return graph_service.get_connections(entity_label, depth=depth)


@router.get("/central")
async def get_central_entities(
    top_n: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get most important entities by centrality."""
    if graph_service._graph.number_of_nodes() == 0:
        await graph_service.load_from_db(db_session=db, owner_id=str(current_user.id))
    return graph_service.get_central_entities(top_n=top_n)


@router.get("/related/{document_id}")
async def get_related_documents(
    document_id: str,
    top_n: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Find documents related to a given document via shared entities."""
    return graph_service.suggest_related(document_id, top_n=top_n)
