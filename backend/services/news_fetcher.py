"""
News Fetcher - arXiv papers and NewsAPI integration with auto-embedding.
"""

import logging
from datetime import datetime
from typing import Optional
import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsFetcher:
    """Fetches news articles and research papers for the knowledge base."""

    def __init__(self):
        self.arxiv_max = settings.arxiv_max_results
        self.news_api_key = settings.news_api_key

    # ── arXiv ─────────────────────────────────────────────────────

    async def search_arxiv(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
    ) -> list[dict]:
        """Search arXiv for papers matching a query."""
        try:
            import arxiv

            search = arxiv.Search(
                query=query,
                max_results=min(max_results, self.arxiv_max),
                sort_by=arxiv.SortCriterion.Relevance if sort_by == "relevance"
                else arxiv.SortCriterion.SubmittedDate,
            )

            papers = []
            for result in search.results():
                papers.append({
                    "title": result.title,
                    "summary": result.summary,
                    "authors": [a.name for a in result.authors],
                    "published": result.published.isoformat(),
                    "updated": result.updated.isoformat() if result.updated else None,
                    "arxiv_id": result.entry_id.split("/")[-1],
                    "pdf_url": result.pdf_url,
                    "categories": result.categories,
                    "doi": result.doi,
                    "source": "arxiv",
                })
            return papers

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []

    async def download_arxiv_pdf(self, arxiv_id: str, save_dir: str) -> Optional[str]:
        """Download an arXiv paper PDF."""
        import os
        try:
            import arxiv

            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results())
            filename = f"arxiv_{arxiv_id.replace('/', '_')}.pdf"
            path = os.path.join(save_dir, filename)
            paper.download_pdf(dirpath=save_dir, filename=filename)
            logger.info(f"Downloaded arXiv paper: {path}")
            return path
        except Exception as e:
            logger.error(f"arXiv download failed: {e}")
            return None

    # ── News API ──────────────────────────────────────────────────

    async def fetch_news(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
    ) -> list[dict]:
        """Fetch news articles from NewsAPI."""
        if not self.news_api_key:
            return [{"error": "NEWS_API_KEY not configured"}]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "language": language,
                        "pageSize": page_size,
                        "sortBy": "relevancy",
                        "apiKey": self.news_api_key,
                    },
                    timeout=15,
                )
                data = resp.json()

            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "published_at": article.get("publishedAt", ""),
                    "author": article.get("author", ""),
                    "image_url": article.get("urlToImage", ""),
                    "type": "news",
                })
            return articles

        except Exception as e:
            logger.error(f"News API fetch failed: {e}")
            return []

    async def generate_daily_briefing(
        self, topics: list[str], max_per_topic: int = 3
    ) -> dict:
        """Generate a daily briefing across multiple topics."""
        briefing = {
            "generated_at": datetime.now().isoformat(),
            "topics": {},
        }

        for topic in topics:
            # Fetch from both sources
            arxiv_papers = await self.search_arxiv(topic, max_results=max_per_topic)
            news_articles = await self.fetch_news(topic, page_size=max_per_topic)

            briefing["topics"][topic] = {
                "papers": arxiv_papers,
                "news": news_articles,
                "total": len(arxiv_papers) + len(news_articles),
            }

        return briefing
