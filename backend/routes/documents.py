"""
Document Routes - Upload, list, process, and manage documents.

Features:
- File upload with validation
- Background processing with detailed logging
- Document listing with filters
- Deletion with cleanup
- Reprocessing capability
"""

import os
import logging
import traceback
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
    BackgroundTasks,
)
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.document import Document, DocumentStatus, DocumentSource
from models.user import User
from routes.auth import get_current_user
from services.document_processor import DocumentProcessor
from services.embeddings import EmbeddingService
from services.knowledge_graph import KnowledgeGraphService
from services.rag import RAGService
from config import get_settings

# ── Setup ──
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()

logger = logging.getLogger(__name__)

# Singleton instances
doc_processor = DocumentProcessor()
embedding_service = EmbeddingService()
graph_service = KnowledgeGraphService()
rag_service = RAGService()


# ── Schemas ───────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Response schema for a document."""
    id: UUID
    title: str
    file_name: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    status: str
    source: str
    chunk_count: int
    page_count: Optional[int]
    ocr_applied: bool
    has_tables: bool
    summary: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class HealthCheckResponse(BaseModel):
    """Health check for document services."""
    timestamp: str
    services: dict
    file_system: dict
    python_packages: dict


# ── Health Check Endpoint ──────────────────────────────────────

@router.get("/debug/health", response_model=HealthCheckResponse)
async def document_health_check():
    """
    Check health of all document processing services.
    
    Returns:
        Health status of Ollama, ChromaDB, file system, and dependencies.
    """
    import requests
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "file_system": {},
        "python_packages": {}
    }
    
    # ✅ Check Ollama
    try:
        response = requests.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=5
        )
        if response.status_code == 200:
            models = response.json().get("models", [])
            status["services"]["ollama"] = {
                "status": "✅ RUNNING",
                "url": settings.ollama_base_url,
                "models": [m["name"] for m in models]
            }
        else:
            status["services"]["ollama"] = {
                "status": f"❌ ERROR: {response.status_code}"
            }
    except Exception as e:
        status["services"]["ollama"] = {
            "status": f"❌ FAILED: {str(e)}"
        }
    
    # ✅ Check ChromaDB
    try:
        response = requests.get(
            f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1",
            timeout=2
        )
        if response.status_code == 200:
            status["services"]["chroma"] = {
                "status": "✅ RUNNING (HttpClient)",
                "url": f"http://{settings.chroma_host}:{settings.chroma_port}"
            }
        else:
            raise ConnectionError("Server returned non-200")
    except Exception:
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            client.heartbeat()
            status["services"]["chroma"] = {
                "status": "✅ RUNNING (Local Embedded PersistentClient)",
                "mode": "local_fallback"
            }
        except Exception as e:
            status["services"]["chroma"] = {
                "status": f"❌ FAILED: {str(e)}"
            }
    
    # ✅ Check Upload Directory
    try:
        upload_dir = settings.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        test_file = os.path.join(upload_dir, ".test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        status["file_system"]["upload_dir"] = {
            "status": "✅ WRITABLE",
            "path": upload_dir
        }
    except Exception as e:
        status["file_system"]["upload_dir"] = {
            "status": f"❌ NOT WRITABLE: {str(e)}",
            "path": settings.upload_dir
        }
    
    # ✅ Check Python Packages
    packages = {
        "PyPDF2": "PyPDF2",
        "docx": "python-docx",
        "fitz": "pymupdf",
        "pdf2image": "pdf2image",
        "pytesseract": "pytesseract",
        "paddleocr": "paddleocr",
        "bs4": "beautifulsoup4"
    }
    
    for import_name, package_name in packages.items():
        try:
            if import_name == "fitz":
                try:
                    import fitz
                except Exception:
                    try:
                        import pymupdf
                    except Exception:
                        import PyMuPDF
            else:
                __import__(import_name)
            status["python_packages"][package_name] = "✅ INSTALLED"
        except Exception:
            status["python_packages"][package_name] = "❌ MISSING"
    
    return status


# ── Background Processing ────────────────────────────────────

async def _process_document_background(
    doc_id: str,
    file_path: str,
    owner_id: str,
    db_session_factory
):
    """
    Background task: Process document with detailed error handling.
    
    Stages:
    1. Validate file
    2. Extract content (PDF/DOCX/etc)
    3. Generate summary
    4. Create embeddings
    5. Extract entities for knowledge graph
    """
    from database import async_session
    
    doc_id_uuid = UUID(doc_id) if isinstance(doc_id, str) else doc_id
    
    logger.info("\n" + "=" * 70)
    logger.info(f"🚀 BACKGROUND PROCESSING STARTED: {doc_id}")
    logger.info("=" * 70)
    
    async with async_session() as db:
        try:
            # ── Load document ──
            result = await db.execute(
                select(Document).where(Document.id == doc_id_uuid)
            )
            doc = result.scalar_one_or_none()
            
            if not doc:
                logger.error(f"❌ Document not found in database: {doc_id}")
                return
            
            logger.info(f"📄 Document: {doc.title}")
            logger.info(f"📂 File: {file_path}")
            
            # ── Stage 1: File Validation ──
            logger.info(f"\n📋 Stage 1/5: Validating file...")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f"   ✅ File exists: {file_size:.2f} MB")
            
            # ── Stage 2: Extract Content ──
            logger.info(f"\n📋 Stage 2/5: Extracting content...")
            doc.status = DocumentStatus.PROCESSING
            await db.commit()
            
            processed = await doc_processor.process_file(file_path)
            
            if not processed.text:
                raise ValueError("No text extracted from file")
            
            logger.info(f"   ✅ Content extracted: {len(processed.text)} chars")
            logger.info(f"   ✅ Chunks created: {len(processed.chunks)}")
            
            # Update document metadata
            doc.content = processed.text
            doc.page_count = processed.page_count
            doc.ocr_applied = processed.ocr_applied
            doc.ocr_confidence = processed.ocr_confidence
            doc.has_tables = processed.has_tables
            doc.has_images = processed.has_images
            doc.metadata_ = processed.metadata or {}
            doc.error_message = None
            
            await db.commit()
            logger.info(f"   ✅ Metadata saved")
            
            # ── Stage 3: Generate Summary ──
            logger.info(f"\n📋 Stage 3/5: Generating summary...")
            try:
                if processed.text:
                    summary = await rag_service.summarize_document(
                        processed.text[:5000],  # Limit to first 5000 chars
                        doc.title
                    )
                    doc.summary = summary
                    logger.info(f"   ✅ Summary generated: {len(summary) if summary else 0} chars")
                else:
                    logger.info(f"   ⏭️  No text to summarize")
            except Exception as e:
                logger.warning(f"   ⚠️ Summary generation failed (non-fatal): {e}")
                doc.summary = None
            
            await db.commit()
            
            # ── Stage 4: Create Embeddings ──
            logger.info(f"\n📋 Stage 4/5: Creating embeddings...")
            doc.status = DocumentStatus.EMBEDDING
            await db.commit()
            
            if processed.chunks:
                try:
                    chunk_count = await embedding_service.add_documents(
                        doc_id=str(doc.id),
                        chunks=processed.chunks,
                        metadatas=[
                            {
                                "document_id": str(doc.id),
                                "title": doc.title,
                                "chunk_index": i
                            }
                            for i in range(len(processed.chunks))
                        ],
                    )
                    doc.chunk_count = chunk_count
                    doc.embedding_model = settings.ollama_embed_model
                    logger.info(f"   ✅ Embeddings created: {chunk_count} chunks")
                except Exception as e:
                    logger.error(f"   ❌ Embedding failed: {e}")
                    raise
            else:
                logger.warning(f"   ⚠️ No chunks to embed")
            
            await db.commit()
            
            # ── Stage 5: Extract Entities ──
            logger.info(f"\n📋 Stage 5/5: Extracting entities...")
            try:
                if processed.text:
                    await graph_service.extract_and_link(
                        text=processed.text[:10000],  # Limit to first 10000 chars
                        document_id=str(doc.id),
                        owner_id=str(owner_id),
                    )
                    logger.info(f"   ✅ Entities extracted and linked")
                else:
                    logger.info(f"   ⏭️  No text to extract entities from")
            except Exception as e:
                logger.warning(f"   ⚠️ Entity extraction failed (non-fatal): {e}")
            
            # ── Finalize ──
            logger.info(f"\n📋 Finalizing...")
            doc.status = DocumentStatus.COMPLETED
            doc.error_message = None
            await db.commit()
            
            logger.info("=" * 70)
            logger.info(f"✅ PROCESSING COMPLETED SUCCESSFULLY")
            logger.info("=" * 70 + "\n")
            
        except Exception as e:
            logger.error("\n" + "=" * 70)
            logger.error(f"❌ PROCESSING FAILED")
            logger.error("=" * 70)
            logger.error(f"Error: {e}")
            logger.error(traceback.format_exc())
            logger.error("=" * 70 + "\n")
            
            # Update status to FAILED
            try:
                result = await db.execute(
                    select(Document).where(Document.id == doc_id_uuid)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                    await db.commit()
            except:
                pass


# ── Upload Route ──────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for processing.
    
    Returns immediately with document record.
    Processing happens in background.
    """
    logger.info(f"\n📤 Upload request from user {current_user.id}")
    logger.info(f"   File: {file.filename}")
    
    # ── Validate file type ──
    allowed = {".pdf", ".docx", ".doc", ".md", ".markdown", ".txt", ".html", ".htm"}
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    
    if ext not in allowed:
        logger.warning(f"   ❌ Unsupported file type: {ext}")
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}"
        )
    
    # ── Read and validate size ──
    content = await file.read()
    max_size = settings.max_file_size_mb * 1024 * 1024
    
    if len(content) > max_size:
        logger.warning(f"   ❌ File too large: {len(content) / (1024*1024):.2f} MB")
        raise HTTPException(
            400,
            f"File too large. Maximum: {settings.max_file_size_mb}MB"
        )
    
    logger.info(f"   ✅ Validation passed: {len(content) / (1024*1024):.2f} MB")
    
    # ── Save file ──
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(
        settings.upload_dir,
        f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
    )
    
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"   ✅ File saved: {file_path}")
    except Exception as e:
        logger.error(f"   ❌ File save failed: {e}")
        raise HTTPException(500, f"Failed to save file: {e}")
    
    # ── Create document record ──
    doc = Document(
        title=os.path.splitext(file.filename)[0] if file.filename else "Untitled",
        file_path=file_path,
        file_name=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        source=DocumentSource.UPLOAD,
        owner_id=current_user.id,
        status=DocumentStatus.PENDING,
    )
    
    db.add(doc)
    # Commit (not just flush) so the row is durably visible to the
    # separate session opened by the background task. A flush alone keeps
    # the row inside this request's transaction; the background task runs
    # after the response is sent and queries a brand-new session, so it
    # would see no row and silently abort before Stage 1.
    await db.commit()
    await db.refresh(doc)
    logger.info(f"   ✅ Document record created: {doc.id}")
    
    # ── Start background processing ──
    background_tasks.add_task(
        _process_document_background,
        str(doc.id),
        file_path,
        str(current_user.id),
        None  # db_session_factory not needed, we create new session
    )
    logger.info(f"   ✅ Background task queued")
    
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status.value if isinstance(doc.status, DocumentStatus) else doc.status,
        source=doc.source.value if isinstance(doc.source, DocumentSource) else doc.source,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        ocr_applied=doc.ocr_applied,
        has_tables=doc.has_tables,
        summary=doc.summary,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat() if hasattr(doc.created_at, "isoformat") else str(doc.created_at),
        updated_at=doc.updated_at.isoformat() if hasattr(doc.updated_at, "isoformat") else str(doc.updated_at),
    )


# ── List Documents ────────────────────────────────────────────

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's documents with pagination and filters."""
    query = select(Document).where(Document.owner_id == current_user.id)

    if status:
        query = query.where(Document.status == status)
    if source:
        query = query.where(Document.source == source)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch page
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                title=d.title,
                file_name=d.file_name,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status.value if isinstance(d.status, DocumentStatus) else d.status,
                source=d.source.value if isinstance(d.source, DocumentSource) else d.source,
                chunk_count=d.chunk_count,
                page_count=d.page_count,
                ocr_applied=d.ocr_applied,
                has_tables=d.has_tables,
                summary=d.summary,
                error_message=d.error_message,
                created_at=d.created_at.isoformat() if hasattr(d.created_at, "isoformat") else str(d.created_at),
                updated_at=d.updated_at.isoformat() if hasattr(d.updated_at, "isoformat") else str(d.updated_at),
            )
            for d in docs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Get Document ──────────────────────────────────────────────

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document details."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.owner_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(404, "Document not found")

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status.value if isinstance(doc.status, DocumentStatus) else doc.status,
        source=doc.source.value if isinstance(doc.source, DocumentSource) else doc.source,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        ocr_applied=doc.ocr_applied,
        has_tables=doc.has_tables,
        summary=doc.summary,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat() if hasattr(doc.created_at, "isoformat") else str(doc.created_at),
        updated_at=doc.updated_at.isoformat() if hasattr(doc.updated_at, "isoformat") else str(doc.updated_at),
    )


# ── Delete Document ───────────────────────────────────────────

@router.delete("/{doc_id}")
@router.post("/{doc_id}/delete")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its embeddings."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.owner_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete embeddings
    try:
        await embedding_service.delete_document(str(doc.id))
    except Exception as e:
        logger.warning(f"Could not delete embeddings for {doc_id}: {e}")

    # Delete file
    try:
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except OSError as e:
        logger.warning(f"Could not delete file for {doc_id}: {e}")

    await db.delete(doc)
    await db.commit()
    
    return {"message": "Document deleted", "id": str(doc_id)}


# ── Reprocess Document ────────────────────────────────────────

@router.post("/{doc_id}/process")
async def reprocess_document(
    doc_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-process an existing document."""
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.owner_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.file_path:
        raise HTTPException(400, "No file to process")

    doc.status = DocumentStatus.PENDING
    await db.commit()

    background_tasks.add_task(
        _process_document_background,
        str(doc.id),
        doc.file_path,
        str(current_user.id),
        None
    )

    return {"message": "Reprocessing started", "id": str(doc_id)}


__all__ = ["router"]