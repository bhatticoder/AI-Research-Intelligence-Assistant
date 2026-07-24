"""
Overleaf Integration Routes — ARIA v2.0
==========================================
Endpoints for pushing generated papers to Overleaf,
listing/deleting ARIA-created Overleaf projects.

All endpoints available at: /api/overleaf/...
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from services.overleaf_service import OverleafService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overleaf", tags=["Overleaf"])

# Singleton service (browser auth is cached in-process)
_overleaf_service: Optional[OverleafService] = None


def _get_service() -> OverleafService:
    global _overleaf_service
    if _overleaf_service is None:
        _overleaf_service = OverleafService(browser="chrome")
    return _overleaf_service


# ── Request Models ────────────────────────────────────────────────────────────

class PushToOverleafRequest(BaseModel):
    title: str
    tex_content: str
    bib_content: str
    journal: Optional[str] = "IEEE Transactions"


class SetBrowserRequest(BaseModel):
    browser: str  # 'chrome' or 'firefox'


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def overleaf_status():
    """Check Overleaf connection status (are browser cookies valid?)."""
    svc = _get_service()
    status = svc.get_connection_status()
    # Try connecting if not yet connected
    if not status["connected"]:
        svc.ensure_connected()
        status = svc.get_connection_status()
    return status


@router.post("/connect")
async def connect_overleaf(req: Optional[SetBrowserRequest] = None):
    """
    Force re-authentication from browser cookies.
    Optionally specify 'chrome' or 'firefox'.
    """
    global _overleaf_service
    browser = req.browser if req else "chrome"
    _overleaf_service = OverleafService(browser=browser)
    success = _overleaf_service.ensure_connected()
    if not success:
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not connect to Overleaf. "
                "Make sure you are logged into Overleaf in Chrome or Firefox, "
                "and that pyoverleaf is installed: pip install pyoverleaf"
            ),
        )
    return {
        "status": "connected",
        "browser": browser,
        "message": "Successfully authenticated with Overleaf via browser cookies.",
    }


@router.post("/push")
async def push_paper_to_overleaf(req: PushToOverleafRequest):
    """
    Push a generated LaTeX paper directly to Overleaf.
    Creates a new project, uploads main.tex and references.bib.
    Returns the Overleaf project URL.
    """
    svc = _get_service()
    try:
        result = await svc.push_paper_to_overleaf(
            title=req.title,
            tex_content=req.tex_content,
            bib_content=req.bib_content,
            journal=req.journal or "IEEE Transactions",
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Route] Overleaf push failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Push to Overleaf failed: {exc}")


@router.get("/projects")
async def list_aria_projects():
    """List all Overleaf projects created by ARIA ([ARIA] prefix)."""
    svc = _get_service()
    projects = svc.list_aria_projects()
    return {"projects": projects, "count": len(projects)}


@router.get("/projects/all")
async def list_all_projects():
    """List ALL Overleaf projects (not just ARIA ones)."""
    svc = _get_service()
    projects = svc.list_all_projects()
    return {"projects": projects, "count": len(projects)}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete an ARIA-generated Overleaf project by ID.
    Safety: only deletes projects prefixed with [ARIA].
    """
    svc = _get_service()
    try:
        result = svc.delete_project(project_id)
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"[Route] Overleaf delete failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}")


@router.get("/projects/{project_id}/download")
async def download_project(project_id: str):
    """Download an Overleaf project as a zip (saved to ./reports/)."""
    import os
    svc = _get_service()
    try:
        os.makedirs("./reports", exist_ok=True)
        out_path = f"./reports/overleaf_{project_id}.zip"
        svc.download_project(project_id, out_path)
        return {"status": "downloaded", "file_path": out_path, "project_id": project_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}")
