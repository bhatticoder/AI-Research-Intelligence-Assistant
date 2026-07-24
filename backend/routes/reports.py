"""
Report Routes - Generate, list, and download research reports.
"""

import os
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.report import Report
from routes.auth import get_current_user
from services.report_generator import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["Reports"])
report_generator = ReportGenerator()


class ReportRequest(BaseModel):
    query: str
    title: Optional[str] = None
    template: str = "default"
    format: str = "markdown"
    n_sources: int = 10


class ReportResponse(BaseModel):
    id: UUID
    title: str
    content: Optional[str]
    format: str
    template: str
    query: Optional[str]
    file_path: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a research report from a query."""
    result = await report_generator.generate(
        query=request.query,
        title=request.title,
        template=request.template,
        format=request.format,
        n_sources=request.n_sources,
    )

    report = Report(
        title=result["title"],
        content=result["content"],
        format=result["format"],
        template=result["template"],
        query=request.query,
        sources_used=result["sources_used"],
        model_used=result["model_used"],
        file_path=result.get("file_path"),
        owner_id=current_user.id,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    return ReportResponse(
        id=report.id,
        title=report.title,
        content=report.content,
        format=report.format,
        template=report.template,
        query=report.query,
        file_path=report.file_path,
        created_at=report.created_at.isoformat(),
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reports."""
    result = await db.execute(
        select(Report)
        .where(Report.owner_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=r.id, title=r.title, content=None, format=r.format,
            template=r.template, query=r.query, file_path=r.file_path,
            created_at=r.created_at.isoformat(),
        )
        for r in reports
    ]


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a generated report file."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.owner_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(404, "Report file not found")

    media_type = "application/pdf" if report.format == "pdf" else "text/markdown"
    return FileResponse(report.file_path, media_type=media_type, filename=f"{report.title}.{report.format}")


@router.get("/templates")
async def list_templates(current_user: User = Depends(get_current_user)):
    """List available report templates."""
    return report_generator.list_templates()
