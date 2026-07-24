"""
Obsidian Routes v2.0 — Vault sync, IEEE paper generation + Overleaf push, RAG search.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging

from services.obsidian import ObsidianSyncService
from services.rag import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/obsidian", tags=["Obsidian"])
obsidian_service = ObsidianSyncService()
rag_service = RAGService()


class VaultConfigRequest(BaseModel):
    vault_path: str


class GeneratePaperRequest(BaseModel):
    topic: str
    target_journal: Optional[str] = "IEEE Transactions on Neural Networks and Learning Systems"
    requirements: Optional[str] = ""
    n_sources: Optional[int] = 8
    push_to_overleaf: Optional[bool] = True   # NEW: auto-push to Overleaf
    overleaf_browser: Optional[str] = "chrome"  # NEW: which browser has Overleaf session


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
    """
    Generate a complete IEEE research paper:
    1. Retrieve relevant literature from ChromaDB (researcher's own indexed papers)
    2. Generate full paper via local LLM (Markdown + IEEEtran LaTeX)
    3. Save Markdown to Obsidian vault's Generated Papers/ folder
    4. Optionally push LaTeX to Overleaf and return the project URL

    The Obsidian plugin displays a clickable 'Open in Overleaf' button
    with the returned project URL.
    """
    try:
        vault_path = obsidian_service.vault_path or r"G:\Obsedian Files\ARIA"
        gen_dir = os.path.join(vault_path, "Generated Papers")

        # ── Step 1: Generate paper (Markdown + LaTeX) ─────────────────────
        result = await obsidian_service.paper_generator.generate_paper(
            topic=req.topic,
            journal=req.target_journal or "IEEE Transactions on Neural Networks and Learning Systems",
            requirements=req.requirements or "",
            output_dir=gen_dir,
            n_sources=req.n_sources or 8,
        )

        # ── Step 2: Update Obsidian Dashboard ─────────────────────────────
        await obsidian_service.update_dashboard()

        # ── Step 3: Push to Overleaf (optional) ───────────────────────────
        overleaf_result = None
        if req.push_to_overleaf and result.get("tex_content"):
            try:
                from services.overleaf_service import OverleafService
                ov_svc = OverleafService(browser=req.overleaf_browser or "chrome")
                overleaf_result = await ov_svc.push_paper_to_overleaf(
                    title=result["title"],
                    tex_content=result["tex_content"],
                    bib_content=result.get("bib_content", ""),
                    journal=req.target_journal or "IEEE Transactions",
                )
                logger.info(
                    f"[API] Paper pushed to Overleaf: {overleaf_result.get('project_url')}"
                )
            except Exception as ov_exc:
                logger.warning(f"[API] Overleaf push failed (non-fatal): {ov_exc}")
                overleaf_result = {
                    "status": "failed",
                    "error": str(ov_exc),
                    "project_url": None,
                }

        # ── Build response ─────────────────────────────────────────────────
        response = {
            "status": "success",
            "message": "IEEE Paper generated successfully",
            "paper": {
                "title": result["title"],
                "filename": result["filename"],
                "file_path": result["file_path"],
                "journal": result["journal"],
                "topic": result["topic"],
                "generated_at": result["generated_at"],
                "sources_count": len(result.get("sources", [])),
                # Don't send full content in response — too large
                "content_preview": (result.get("content", "")[:500] + "…"),
            },
        }

        if overleaf_result:
            response["overleaf"] = {
                "status": overleaf_result.get("status"),
                "project_url": overleaf_result.get("project_url"),
                "project_id": overleaf_result.get("project_id"),
                "project_name": overleaf_result.get("project_name"),
                "error": overleaf_result.get("error"),
            }
        else:
            response["overleaf"] = None

        return response

    except Exception as e:
        logger.error(f"[API] Paper generation failed: {e}", exc_info=True)
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
