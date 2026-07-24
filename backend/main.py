"""
ARIA - AI Research & Intelligence Assistant
Main FastAPI Application Entry Point

Connects all routes, initializes services, and manages application lifecycle.
"""

import json
import logging
from contextlib import asynccontextmanager

import sys
import asyncio



from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import init_db, close_db
from routes import (
    auth_router,
    documents_router,
    chat_router,
    obsidian_router,
    graph_router,
    reports_router,
    admin_router,
)
from routes.overleaf import router as overleaf_router
from services.rag import RAGService

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aria")

from routes.obsidian import obsidian_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting ARIA - AI Research & Intelligence Assistant")
    await init_db()
    logger.info("✅ Database initialized")

    # Start Obsidian vault watcher & command runner daemon
    try:
        await obsidian_service.start_watching()
        # Trigger initial sync & dashboard render
        asyncio.create_task(obsidian_service.sync())
        logger.info("👁️ Obsidian Vault Watcher & Command Daemon active")
    except Exception as e:
        logger.error(f"Failed to start Obsidian watcher: {e}")

    yield

    logger.info("🛑 Shutting down ARIA")
    await obsidian_service.stop_watching()
    await close_db()

app = FastAPI(
    title="ARIA - AI Research & Intelligence Assistant",
    description="Full-stack AI system for research, knowledge management, and document analysis",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    err_str = f"{type(exc).__name__}: {str(exc)}"
    logger.error(f"Unhandled Exception on {request.url.path}: {err_str}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {err_str}", "traceback": traceback.format_exc()}
    )


# CORS - Allow Obsidian desktop app and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(obsidian_router)
app.include_router(graph_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(overleaf_router)  # Overleaf integration
class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()
rag_service = RAGService()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming RAG chat responses."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            question = request.get("message", "")

            if not question:
                await manager.send_json(websocket, {"type": "error", "content": "Empty message"})
                continue

            # Stream RAG response
            async for chunk in rag_service.query_stream(
                question=question,
                n_results=request.get("n_results", 5),
                model=request.get("model"),
            ):
                await manager.send_json(websocket, chunk)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await manager.send_json(websocket, {"type": "error", "content": str(e)})
        except Exception:
            pass
        manager.disconnect(websocket)


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "ARIA", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "ARIA - AI Research & Intelligence Assistant",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )