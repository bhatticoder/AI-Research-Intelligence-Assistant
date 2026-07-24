"""
LLM Service - Ollama client wrapper with streaming, model management, and fallbacks.
"""

import logging
from typing import AsyncGenerator, Optional
import ollama
import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_val(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_message_content(response) -> str:
    msg = _get_val(response, "message")
    if msg is None:
        return ""
    return _get_val(msg, "content", "") or ""


class LLMService:
    """Manages Ollama LLM interactions — chat, completions, embeddings, model management."""

    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        self.chat_model = settings.ollama_chat_model
        self.embed_model = settings.ollama_embed_model

    # ── Chat ──────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Send a chat request and return the full response."""
        model = model or get_settings().ollama_chat_model
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = await self.client.chat(
                model=model,
                messages=messages,
                options={"temperature": temperature},
            )
            return {
                "content": _get_message_content(response),
                "model": model,
                "tokens": _get_val(response, "eval_count", 0) or 0,
                "duration_ms": (_get_val(response, "total_duration", 0) or 0) / 1e6,
            }
        except Exception as e:
            logger.error(f"LLM chat error with {model}: {e}")
            if model != "llama3.2:1b":
                logger.info("Attempting fallback to lighter model llama3.2:1b...")
                try:
                    response = await self.client.chat(
                        model="llama3.2:1b",
                        messages=messages,
                        options={"temperature": temperature},
                    )
                    return {
                        "content": _get_message_content(response),
                        "model": "llama3.2:1b",
                        "tokens": _get_val(response, "eval_count", 0) or 0,
                        "duration_ms": (_get_val(response, "total_duration", 0) or 0) / 1e6,
                    }
                except Exception as fallback_err:
                    logger.error(f"Fallback model failed: {fallback_err}")
            raise

    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses token by token."""
        model = model or get_settings().ollama_chat_model
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            stream = await self.client.chat(
                model=model,
                messages=messages,
                stream=True,
                options={"temperature": temperature},
            )
            async for chunk in stream:
                content = _get_message_content(chunk)
                if content:
                    yield content
        except Exception as e:
            logger.error(f"LLM stream error with {model}: {e}")
            if model != "llama3.2:1b":
                logger.info("Attempting fallback stream to lighter model llama3.2:1b...")
                try:
                    stream = await self.client.chat(
                        model="llama3.2:1b",
                        messages=messages,
                        stream=True,
                        options={"temperature": temperature},
                    )
                    async for chunk in stream:
                        content = _get_message_content(chunk)
                        if content:
                            yield content
                    return
                except Exception as fallback_err:
                    logger.error(f"Fallback stream failed: {fallback_err}")
            yield f"\n\n[Error: {str(e)}]"

    # ── Completions ───────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Simple text generation (non-chat)."""
        model = model or self.chat_model
        response = await self.client.generate(
            model=model,
            prompt=prompt,
            options={"temperature": temperature},
        )
        return _get_val(response, "response", "") or ""

    # ── Entity Extraction ─────────────────────────────────────────

    async def extract_entities(self, text: str) -> dict:
        """Extract named entities from text using LLM."""
        prompt = f"""Extract all named entities from the following text. 
Return a JSON object with these categories:
- "persons": list of person names
- "organizations": list of organization names
- "locations": list of location names
- "concepts": list of key concepts/topics
- "dates": list of dates/time periods
- "technologies": list of technologies/tools mentioned

Return ONLY valid JSON, no other text.

Text:
{text[:3000]}"""

        response = await self.generate(prompt, temperature=0.1)
        try:
            import json
            # Try to parse JSON from response
            # Handle cases where LLM wraps in markdown code blocks
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse entity extraction response as JSON")
            return {"persons": [], "organizations": [], "locations": [],
                    "concepts": [], "dates": [], "technologies": []}

    async def summarize(self, text: str, max_length: int = 300) -> str:
        """Generate a concise summary of the text."""
        prompt = f"""Provide a concise summary of the following text in {max_length} words or less.
Focus on the key findings, arguments, and conclusions.

Text:
{text[:5000]}

Summary:"""
        return await self.generate(prompt, temperature=0.3)

    # ── Model Management ──────────────────────────────────────────

    async def list_models(self) -> list[dict]:
        """List all available Ollama models."""
        try:
            response = await self.client.list()
            models_list = _get_val(response, "models", []) or []
            out = []
            for m in models_list:
                details = _get_val(m, "details", {})
                out.append({
                    "name": _get_val(m, "name", "unknown"),
                    "size": _get_val(m, "size", 0),
                    "modified": str(_get_val(m, "modified_at", "")),
                    "family": _get_val(details, "family", "unknown"),
                    "parameters": _get_val(details, "parameter_size", "unknown"),
                })
            return out
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(self, model_name: str) -> AsyncGenerator[dict, None]:
        """Pull/download a model with progress updates."""
        try:
            stream = await self.client.pull(model_name, stream=True)
            async for progress in stream:
                yield {
                    "status": _get_val(progress, "status", ""),
                    "completed": _get_val(progress, "completed", 0),
                    "total": _get_val(progress, "total", 0),
                }
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield {"status": f"error: {str(e)}", "completed": 0, "total": 0}

    async def health_check(self) -> dict:
        """Check if Ollama is running and responsive."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
                models = resp.json().get("models", [])
                return {
                    "status": "healthy",
                    "models_available": len(models),
                    "chat_model": self.chat_model,
                    "embed_model": self.embed_model,
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
