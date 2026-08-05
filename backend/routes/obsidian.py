"""
Obsidian Routes v2.0 — Vault sync, IEEE paper generation, document conversion, RAG search.
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


class ConvertDocumentsRequest(BaseModel):
    folder_path: Optional[str] = "IEEE Reports"
    file_paths: Optional[List[str]] = None
    output_subfolder: Optional[str] = "Markdown Reports"


class GeneratePaperRequest(BaseModel):
    topic: str
    target_journal: Optional[str] = "IEEE Transactions on Neural Networks and Learning Systems"
    requirements: Optional[str] = ""
    proposal_file_path: Optional[str] = ""
    proposal_content: Optional[str] = ""
    n_sources: Optional[int] = 8


class ConvertToIEEEPDFRequest(BaseModel):
    file_path: Optional[str] = None
    markdown_content: Optional[str] = None
    output_filename: Optional[str] = None


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
    2. Generate full paper via local LLM (Markdown)
    3. Save Markdown to Obsidian vault's Generated Papers/ folder
    """
    try:
        vault_path = obsidian_service.vault_path or r"G:\Obsedian Files\ARIA"
        gen_dir = os.path.join(vault_path, "Generated Papers")

        # ── Step 0: Extract Proposal Text ───────────────────────────────
        proposal_text = req.proposal_content or ""
        if req.proposal_file_path:
            prop_full_path = req.proposal_file_path if os.path.isabs(req.proposal_file_path) else os.path.join(vault_path, req.proposal_file_path)
            if os.path.exists(prop_full_path):
                with open(prop_full_path, "r", encoding="utf-8", errors="replace") as pf:
                    proposal_text = pf.read() + "\n\n" + proposal_text

        combined_reqs = (req.requirements or "").strip()
        if proposal_text:
            combined_reqs = f"RESEARCH PROPOSAL CONTEXT:\n{proposal_text[:3500]}\n\nADDITIONAL TECHNICAL REQUIREMENTS:\n{combined_reqs}"

        # ── Step 1: Generate paper (Markdown + LaTeX) ─────────────────────
        result = await obsidian_service.paper_generator.generate_paper(
            topic=req.topic,
            journal=req.target_journal or "IEEE Transactions on Neural Networks and Learning Systems",
            requirements=combined_reqs,
            output_dir=gen_dir,
            n_sources=req.n_sources or 10,
        )

        # ── Step 2: Update Obsidian Dashboard ─────────────────────────────
        await obsidian_service.update_dashboard()

        # ── Build response ─────────────────────────────────────────────────
        return {
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


@router.post("/convert-documents")
async def convert_documents(req: ConvertDocumentsRequest):
    """
    Batch convert non-Markdown documents (PDF, DOCX, DOC, HTML, TXT) in vault
    to Markdown (.md) notes and auto-ingest them into ChromaDB.
    """
    try:
        result = await obsidian_service.convert_and_ingest_batch(
            folder_relative_path=req.folder_path,
            file_relative_paths=req.file_paths,
            output_subfolder=req.output_subfolder or "Markdown Reports"
        )
        return result
    except Exception as e:
        logger.error(f"[API] Batch document conversion failed: {e}", exc_info=True)
        raise HTTPException(500, f"Document conversion failed: {str(e)}")


@router.post("/convert-to-ieee-pdf")
async def convert_to_ieee_pdf(req: ConvertToIEEEPDFRequest):
    """
    Convert a Markdown research paper into an authentic 2-column IEEE PDF document.
    """
    try:
        result = await obsidian_service.convert_to_ieee_pdf(
            file_path=req.file_path,
            markdown_content=req.markdown_content,
            output_filename=req.output_filename
        )
        return result
    except Exception as e:
        logger.error(f"[API] IEEE PDF rendering failed: {e}", exc_info=True)
        raise HTTPException(500, f"IEEE PDF rendering failed: {str(e)}")


@router.post("/dashboard/refresh")
async def refresh_dashboard():
    """Manually update Dashboard.md in Obsidian vault."""
    try:
        await obsidian_service.update_dashboard()
        return {"message": "Dashboard updated successfully"}
    except Exception as e:
        raise HTTPException(500, f"Dashboard refresh failed: {str(e)}")
