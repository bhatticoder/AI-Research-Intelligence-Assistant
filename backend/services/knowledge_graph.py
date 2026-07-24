"""
Knowledge Graph Service - Entity extraction, relationship mapping, and graph operations.
Uses LLM for NER and NetworkX for graph computation.
"""

import logging
from typing import Optional
from uuid import UUID
import networkx as nx

from services.llm_service import LLMService

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Builds and queries knowledge graphs from document entities."""

    def __init__(self):
        self.llm = LLMService()
        self._graph = nx.Graph()

    async def extract_and_link(
        self,
        text: str,
        document_id: str,
        owner_id: str,
        db_session=None,
    ) -> dict:
        """Extract entities from text and create graph nodes/edges."""
        # 1. Extract entities via LLM
        entities = await self.llm.extract_entities(text)

        nodes_created = 0
        edges_created = 0
        all_entity_labels = []

        # 2. Create nodes for each entity type
        for entity_type, entity_list in entities.items():
            for entity_name in entity_list:
                entity_name = entity_name.strip()
                if not entity_name or len(entity_name) < 2:
                    continue

                all_entity_labels.append((entity_name, entity_type))
                self._graph.add_node(
                    entity_name,
                    node_type=entity_type,
                    document_id=document_id,
                    owner_id=owner_id,
                )
                nodes_created += 1

        # 3. Create edges between co-occurring entities (within same document)
        for i, (label_a, type_a) in enumerate(all_entity_labels):
            for label_b, type_b in all_entity_labels[i + 1:]:
                if label_a != label_b:
                    if self._graph.has_edge(label_a, label_b):
                        self._graph[label_a][label_b]["weight"] += 1
                    else:
                        self._graph.add_edge(
                            label_a, label_b,
                            relation_type="co_occurs",
                            weight=1,
                            document_id=document_id,
                        )
                        edges_created += 1

        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "entities": entities,
        }

    async def load_from_db(self, db_session, owner_id: Optional[str] = None):
        """Load graph nodes and edges from database or auto-build from documents."""
        if not db_session:
            return

        from sqlalchemy import select
        from models.graph_node import GraphNode, GraphEdge
        from models.document import Document
        from uuid import UUID

        owner_uuid = UUID(owner_id) if owner_id and isinstance(owner_id, str) else owner_id

        # Query nodes from DB
        stmt = select(GraphNode)
        if owner_uuid:
            stmt = stmt.where(GraphNode.owner_id == owner_uuid)
        res = await db_session.execute(stmt)
        nodes = res.scalars().all()

        if not nodes:
            # If no nodes exist in DB, check for uploaded documents and auto-extract
            doc_stmt = select(Document)
            if owner_uuid:
                doc_stmt = doc_stmt.where(Document.owner_id == owner_uuid)
            doc_res = await db_session.execute(doc_stmt)
            docs = doc_res.scalars().all()

            for doc in docs:
                if doc.content:
                    await self.extract_and_link(
                        text=doc.content[:5000],
                        document_id=str(doc.id),
                        owner_id=str(doc.owner_id),
                        db_session=db_session,
                    )
            return

        node_map = {}
        for n in nodes:
            node_map[n.id] = n.label
            self._graph.add_node(
                n.label,
                node_type=n.node_type,
                document_id=str(n.document_id) if n.document_id else None,
                owner_id=str(n.owner_id) if n.owner_id else None,
            )

        edge_stmt = select(GraphEdge)
        if owner_uuid:
            edge_stmt = edge_stmt.where(GraphEdge.owner_id == owner_uuid)
        edge_res = await db_session.execute(edge_stmt)
        edges = edge_res.scalars().all()
        for e in edges:
            src_label = node_map.get(e.source_id)
            tgt_label = node_map.get(e.target_id)
            if src_label and tgt_label:
                self._graph.add_edge(
                    src_label,
                    tgt_label,
                    relation_type=e.relation_type,
                    weight=e.weight,
                    document_id=str(e.document_id) if e.document_id else None,
                )

    async def get_graph_data_async(self, db_session=None, owner_id: Optional[str] = None) -> dict:
        """Export graph as nodes + edges, loading from DB if empty."""
        if self._graph.number_of_nodes() == 0 and db_session:
            await self.load_from_db(db_session, owner_id=owner_id)
        return self.get_graph_data(owner_id=owner_id)

    def get_graph_data(self, owner_id: Optional[str] = None) -> dict:
        """Export graph as nodes + edges for visualization."""
        nodes = []
        for node_id, attrs in self._graph.nodes(data=True):
            if owner_id and attrs.get("owner_id") and attrs.get("owner_id") != owner_id:
                continue
            nodes.append({
                "id": node_id,
                "label": node_id,
                "type": attrs.get("node_type", "unknown"),
                "document_id": attrs.get("document_id"),
                "degree": self._graph.degree(node_id),
            })

        edges = []
        for source, target, attrs in self._graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "relation": attrs.get("relation_type", "related"),
                "weight": attrs.get("weight", 1),
            })

        return {"nodes": nodes, "edges": edges}

    def get_connections(self, entity_label: str, depth: int = 2) -> dict:
        """Find all connections for an entity up to N hops."""
        if entity_label not in self._graph:
            return {"entity": entity_label, "connections": [], "error": "Entity not found"}

        # BFS to find connections up to depth
        connections = []
        visited = {entity_label}
        queue = [(entity_label, 0)]

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue

            for neighbor in self._graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    edge_data = self._graph[current][neighbor]
                    connections.append({
                        "entity": neighbor,
                        "type": self._graph.nodes[neighbor].get("node_type", "unknown"),
                        "connected_via": current,
                        "relation": edge_data.get("relation_type", "related"),
                        "weight": edge_data.get("weight", 1),
                        "depth": d + 1,
                    })
                    queue.append((neighbor, d + 1))

        # Sort by weight (strongest connections first)
        connections.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "entity": entity_label,
            "type": self._graph.nodes[entity_label].get("node_type", "unknown"),
            "connections": connections,
            "total": len(connections),
        }

    def get_central_entities(self, top_n: int = 20) -> list[dict]:
        """Find most important entities by centrality measures."""
        if not self._graph.nodes:
            return []

        # Compute centrality metrics
        try:
            degree_cent = nx.degree_centrality(self._graph)
            betweenness = nx.betweenness_centrality(self._graph)
        except Exception:
            degree_cent = {}
            betweenness = {}

        entities = []
        for node_id, attrs in self._graph.nodes(data=True):
            entities.append({
                "label": node_id,
                "type": attrs.get("node_type", "unknown"),
                "degree_centrality": round(degree_cent.get(node_id, 0), 4),
                "betweenness_centrality": round(betweenness.get(node_id, 0), 4),
                "connections": self._graph.degree(node_id),
            })

        entities.sort(key=lambda x: x["degree_centrality"], reverse=True)
        return entities[:top_n]

    def suggest_related(self, document_id: str, top_n: int = 10) -> list[dict]:
        """Suggest documents related to a given document via shared entities."""
        # Find all entities in the given document
        doc_entities = [
            n for n, d in self._graph.nodes(data=True)
            if d.get("document_id") == document_id
        ]

        # Find other documents sharing entities
        related_docs = {}
        for entity in doc_entities:
            for neighbor in self._graph.neighbors(entity):
                neighbor_doc = self._graph.nodes[neighbor].get("document_id")
                if neighbor_doc and neighbor_doc != document_id:
                    if neighbor_doc not in related_docs:
                        related_docs[neighbor_doc] = {"shared_entities": [], "score": 0}
                    related_docs[neighbor_doc]["shared_entities"].append(entity)
                    related_docs[neighbor_doc]["score"] += 1

        results = [
            {"document_id": doc_id, **info}
            for doc_id, info in related_docs.items()
        ]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]
