"""
RAG Service - Retrieval-Augmented Generation pipeline using LangChain + ChromaDB + Ollama.

Pipeline: Query → Embed → Retrieve → Rerank → Augment → Generate → Cite Sources
"""

import logging
from typing import AsyncGenerator, Optional

from services.llm_service import LLMService
from services.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are ARIA, an AI Research & Intelligence Assistant. You help researchers, students, and professionals analyze their documents and knowledge base.

INSTRUCTIONS:
- Answer questions based ONLY on the provided context from the user's documents
- If the context doesn't contain enough information, say so clearly
- Always cite which document(s) your answer comes from
- Use clear, academic language appropriate for research
- If you find contradictions between sources, highlight them
- Format your response with markdown for readability

CONTEXT FROM USER'S DOCUMENTS:
{context}

IMPORTANT: Base your answer on the above context. If the answer isn't in the context, say "I couldn't find information about this in your documents." and suggest what the user might search for."""


class RAGService:
    """Orchestrates the full RAG pipeline with source citation."""

    def __init__(self):
        self.llm = LLMService()
        self.embeddings = EmbeddingService()

    async def query(
        self,
        question: str,
        n_results: int = 5,
        model: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> dict:
        """
        Full RAG pipeline: retrieve relevant chunks → augment prompt → generate answer.
        Returns answer with source citations.
        """
        # 1. Retrieve relevant chunks from ChromaDB
        retrieval = await self.embeddings.query(
            query_text=question,
            n_results=n_results,
        )

        documents = retrieval.get("documents", [])
        metadatas = retrieval.get("metadatas", [])
        distances = retrieval.get("distances", [])

        if not documents:
            return {
                "answer": "I couldn't find any relevant documents in your knowledge base. Try uploading some documents first.",
                "sources": [],
                "context_chunks": [],
            }

        # 2. Build context from retrieved chunks
        context_parts = []
        sources = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            similarity = 1 - dist  # Convert distance to similarity
            source_info = {
                "chunk_index": i,
                "document_id": meta.get("document_id", "unknown"),
                "chunk_text": doc[:200] + "..." if len(doc) > 200 else doc,
                "similarity_score": round(similarity, 4),
                "metadata": meta,
            }
            sources.append(source_info)
            context_parts.append(f"[Source {i + 1} | Relevance: {similarity:.0%}]\n{doc}")

        context = "\n\n---\n\n".join(context_parts)

        # 3. Build messages with conversation history
        messages = []
        if conversation_history:
            # Include last 6 messages for context
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": question})

        # 4. Generate response with context
        system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
        response = await self.llm.chat(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for factual answers
        )

        return {
            "answer": response["content"],
            "sources": sources,
            "context_chunks": documents,
            "model": response["model"],
            "tokens_used": response["tokens"],
        }

    async def query_stream(
        self,
        question: str,
        n_results: int = 5,
        model: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Streaming RAG — yields tokens as they're generated, then final sources.
        """
        # 1. Retrieve
        retrieval = await self.embeddings.query(query_text=question, n_results=n_results)
        documents = retrieval.get("documents", [])
        metadatas = retrieval.get("metadatas", [])
        distances = retrieval.get("distances", [])

        if not documents:
            yield {
                "type": "token",
                "content": "I couldn't find any relevant documents. Try uploading some documents first.",
            }
            yield {"type": "done", "sources": []}
            return

        # 2. Build context
        context_parts = []
        sources = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            similarity = 1 - dist
            sources.append({
                "chunk_index": i,
                "document_id": meta.get("document_id", "unknown"),
                "chunk_text": doc[:200] + "...",
                "similarity_score": round(similarity, 4),
                "metadata": meta,
            })
            context_parts.append(f"[Source {i + 1}]\n{doc}")

        context = "\n\n---\n\n".join(context_parts)

        # Yield sources first so UI can show them
        yield {"type": "sources", "sources": sources}

        # 3. Stream generation
        messages = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": question})

        system_prompt = RAG_SYSTEM_PROMPT.format(context=context)

        async for token in self.llm.chat_stream(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3,
        ):
            yield {"type": "token", "content": token}

        yield {"type": "done", "sources": sources}

    async def summarize_document(self, text: str, doc_title: str = "") -> str:
        """Generate a comprehensive summary of a document."""
        prompt = f"""Provide a comprehensive research summary of the following document.

Document Title: {doc_title}

Include:
1. **Main Topic/Thesis**: What is this document about?
2. **Key Findings**: The most important points and discoveries
3. **Methodology** (if applicable): How was the research conducted?
4. **Conclusions**: What are the main takeaways?
5. **Key Terms**: Important terminology and definitions

Document Content:
{text[:8000]}

Summary:"""
        return await self.llm.generate(prompt, temperature=0.3)

    async def find_connections(self, doc_text: str, query: str = "") -> dict:
        """Find thematic connections and insights across document content."""
        prompt = f"""Analyze the following text and identify:
1. Key themes and topics
2. Cross-references to other potential topics
3. Unanswered questions raised
4. Potential connections to other research areas
5. Contradictions or gaps in the content

{f'Focus area: {query}' if query else ''}

Text:
{doc_text[:5000]}

Return your analysis in a structured format."""
        response = await self.llm.generate(prompt, temperature=0.5)
        return {"analysis": response, "query": query}
