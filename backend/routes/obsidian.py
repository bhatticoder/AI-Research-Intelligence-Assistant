"""
Obsidian Routes - Vault sync status, manual sync, IEEE paper generation, and RAG search.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from services.obsidian import ObsidianSyncService
from services.rag import RAGService

router = APIRouter(prefix="/api/obsidian", tags=["Obsidian"])
obsidian_service = ObsidianSyncService()
rag_service = RAGService()


class VaultConfigRequest(BaseModel):
    vault_path: str


class GeneratePaperRequest(BaseModel):
    topic: str
    target_journal: Optional[str] = "IEEE Transactions on Neural Networks and Learning Systems"
    requirements: Optional[str] = ""


class QueryRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5


@router.get("/status")
async def get_sync_status():
    """Get current Obsidian sync status."""
    return obsidian_service.get_status()


@router.post("/sync")
async def manual_sync():
    """Trigger a manual vault sync & command scan."""
    if not obsidian_service.vault_path:
        raise HTTPException(400, "Vault path not configured.")
    result = await obsidian_service.sync()
    return result


@router.get("/stats")
async def get_vault_stats():
    """Get vault statistics."""
    return obsidian_service.get_stats()


@router.post("/configure")
async def configure_vault(config: VaultConfigRequest):
    """Configure Obsidian vault path."""
    try:
        obsidian_service.set_vault_path(config.vault_path)
        return {"message": "Vault configured", "path": config.vault_path}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/watch/start")
async def start_watching():
    """Start automatic vault watching."""
    if not obsidian_service.vault_path:
        raise HTTPException(400, "Vault path not configured")
    await obsidian_service.start_watching()
    return {"message": "Vault watching started"}


@router.post("/watch/stop")
async def stop_watching():
    """Stop automatic vault watching."""
    await obsidian_service.stop_watching()
    return {"message": "Vault watching stopped"}


@router.post("/generate-paper")
async def generate_paper(req: GeneratePaperRequest):
    """Generate an IEEE Transactions research paper directly from Obsidian command or plugin."""
    try:
        vault_path = obsidian_service.vault_path or r"G:\Obsedian Files\ARIA"
        gen_dir = os.path.join(vault_path, "Generated Papers")
        result = await obsidian_service.paper_generator.generate_paper(
            topic=req.topic,
            journal=req.target_journal or "IEEE Transactions on Neural Networks and Learning Systems",
            requirements=req.requirements or "",
            output_dir=gen_dir
        )
        # Update Dashboard
        await obsidian_service.update_dashboard()
        return {
            "status": "success",
            "message": "IEEE Paper generated successfully",
            "paper": result
        }
    except Exception as e:
        raise HTTPException(500, f"Paper generation failed: {str(e)}")


@router.post("/query")
async def query_knowledge_base(req: QueryRequest):
    """Query indexed IEEE literature and notes from Obsidian."""
    try:
        results = await rag_service.query(question=req.query, n_results=req.n_results or 5)
        return results
    except Exception as e:
        raise HTTPException(500, f"Query failed: {str(e)}")


@router.post("/dashboard/refresh")
async def refresh_dashboard():
    """Manually update Dashboard.md in Obsidian vault."""
    try:
        await obsidian_service.update_dashboard()
        return {"message": "Dashboard updated successfully"}
    except Exception as e:
        raise HTTPException(500, f"Dashboard refresh failed: {str(e)}")
