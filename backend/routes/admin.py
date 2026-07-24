"""
Admin Routes - System stats, model management, and news fetching.
"""

from fastapi import APIRouter, Depends
from models.user import User
from routes.auth import get_current_user
from services.llm_service import LLMService
from services.embeddings import EmbeddingService
from services.news_fetcher import NewsFetcher
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["Admin"])
llm_service = LLMService()
embedding_service = EmbeddingService()
news_fetcher = NewsFetcher()


class ModelDownloadRequest(BaseModel):
    model_name: str


class NewsSearchRequest(BaseModel):
    query: str
    max_results: int = 10


class BriefingRequest(BaseModel):
    topics: list[str]
    max_per_topic: int = 3


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    """List available Ollama models."""
    return await llm_service.list_models()


@router.post("/models/download")
async def download_model(
    request: ModelDownloadRequest,
    current_user: User = Depends(get_current_user),
):
    """Download/pull an Ollama model."""
    progress = []
    async for p in llm_service.pull_model(request.model_name):
        progress.append(p)
    return {"model": request.model_name, "progress": progress}


@router.get("/system")
async def system_stats(current_user: User = Depends(get_current_user)):
    """Get system health and stats."""
    ollama_health = await llm_service.health_check()
    chroma_stats = await embedding_service.get_stats()

    return {
        "ollama": ollama_health,
        "chromadb": chroma_stats,
        "status": "healthy" if ollama_health.get("status") == "healthy" else "degraded",
    }


@router.post("/news/search")
async def search_news(
    request: NewsSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Search for news articles."""
    return await news_fetcher.fetch_news(request.query, page_size=request.max_results)


@router.post("/news/arxiv")
async def search_arxiv(
    request: NewsSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Search arXiv papers."""
    return await news_fetcher.search_arxiv(request.query, max_results=request.max_results)


@router.post("/news/briefing")
async def generate_briefing(
    request: BriefingRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a daily briefing across topics."""
    return await news_fetcher.generate_daily_briefing(
        topics=request.topics,
        max_per_topic=request.max_per_topic,
    )
