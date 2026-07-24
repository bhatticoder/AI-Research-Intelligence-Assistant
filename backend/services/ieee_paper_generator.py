"""
IEEE Research Paper Generator Service
Generates publication-quality IEEE Transactions research papers based on indexed literature and user requirements.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from services.llm_service import LLMService
from services.embeddings import EmbeddingService
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

IEEE_PAPER_PROMPT = """You are a distinguished IEEE Senior Member and Principal AI Researcher writing a rigorous IEEE Transactions research paper.

Generate a comprehensive, publication-quality research paper in Markdown format following the standard IEEE Transactions structure based on the provided user requirements and retrieved literature context.

USER REQUIREMENTS:
Topic / Title Concept: {topic}
Target IEEE Journal: {journal}
Specific Focus / Requirements: {requirements}

RETRIEVED IEEE LITERATURE CONTEXT:
{context}

STRICT IEEE PAPER STRUCTURE & INSTRUCTIONS:
1. Title: Create a precise, formal IEEE research paper title.
2. Author Block: "ARIA Automated Research Intelligence, IEEE Student Member Branch, and Local Llama AI Laboratory"
3. Abstract: A single concise paragraph (150-250 words) summarizing background, core novel contribution, methodology, and empirical findings.
4. Index Terms: 5-8 relevant IEEE keywords separated by commas.
5. Section I: INTRODUCTION:
   - Subsection A: Background & Motivation
   - Subsection B: Problem Statement & Existing Limitations
   - Subsection C: Summary of Primary Novel Contributions (bulleted list)
   - Subsection D: Paper Organization
6. Section II: RELATED WORK & LITERATURE REVIEW:
   - Synthesize prior research from the provided literature context with numeric citations like [1], [2].
   - Compare existing approaches vs. proposed methodology.
7. Section III: PROPOSED METHODOLOGY & THEORETICAL FORMULATION:
   - Detailed mathematical formulation using LaTeX block equations ($$ ... $$) and inline math ($ ... $).
   - System Architecture description and algorithmic steps.
8. Section IV: EXPERIMENTAL EVALUATION & PERFORMANCE ANALYSIS:
   - Experimental setup, metrics, baseline comparisons, and analysis of results.
   - Use Markdown tables for performance comparison metrics.
9. Section V: DISCUSSION & OPEN RESEARCH CHALLENGES:
   - Theoretical implications, scalability considerations, and current limitations.
10. Section VI: CONCLUSION & FUTURE DIRECTIONS:
    - Summary of achievements and future research roadmap.
11. REFERENCES:
    - List numbered IEEE citations ([1], [2], etc.) referencing key papers or foundational concepts from context.

Use professional, academic English with precise technical language, mathematical rigor, and structured Markdown headers (# for Title, ## for Sections, ### for Subsections). Include LaTeX equations where appropriate.

Output ONLY the complete Markdown research paper.
"""


class IEEEPaperGenerator:
    """Generates IEEE Transactions style research papers using local LLMs and RAG."""

    def __init__(self):
        self.llm = LLMService()
        self.embeddings = EmbeddingService()

    async def generate_paper(
        self,
        topic: str,
        journal: str = "IEEE Transactions on Neural Networks and Learning Systems",
        requirements: str = "",
        output_dir: Optional[str] = None,
        n_sources: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate a complete IEEE research paper based on indexed IEEE documents & requirements.
        """
        logger.info(f"Generating IEEE paper for topic: '{topic}' in journal: '{journal}'")

        # 1. Query ChromaDB directly for relevant context chunks
        retrieval_query = f"{topic} {requirements}"
        retrieval = await self.embeddings.query(query_text=retrieval_query, n_results=n_sources)
        
        documents = retrieval.get("documents", [])
        metadatas = retrieval.get("metadatas", [])
        distances = retrieval.get("distances", [])

        sources = []
        context_chunks = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            similarity = 1.0 - dist if dist <= 1.0 else 0.5
            sources.append({
                "chunk_index": i,
                "document_id": meta.get("document_id", "unknown"),
                "chunk_text": doc[:200] + "..." if len(doc) > 200 else doc,
                "similarity_score": round(similarity, 4),
                "metadata": meta,
            })
            context_chunks.append(f"[Ref {i+1}]: {doc}")

        context_str = "\n\n".join(context_chunks) if context_chunks else "No specific IEEE literature found in database. Relying on general foundational research principles."

        # Keep context string bounded to ~3500 chars to avoid memory overruns in small local LLMs
        bounded_context = context_str[:3500]

        # 2. Build Prompt & Call LLM
        prompt = IEEE_PAPER_PROMPT.format(
            topic=topic,
            journal=journal,
            requirements=requirements or "General comprehensive investigation.",
            context=bounded_context,
        )

        logger.info("Invoking LLM for IEEE Paper synthesis...")
        paper_content = await self.llm.generate(prompt, temperature=0.3)

        # 3. Extract or clean Title
        title_match = re.search(r"^#\s+(.*)", paper_content, re.MULTILINE)
        paper_title = title_match.group(1).strip() if title_match else topic.title()
        # Clean title for filename
        clean_filename = re.sub(r'[\\/*?:"<>|]', "", paper_title).replace(" ", "_")[:60]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_filename}_{timestamp}.md"

        # 4. Add Obsidian Frontmatter
        frontmatter = f"""---
title: "{paper_title}"
date: {datetime.now().strftime('%Y-%m-%d')}
type: ieee-research-paper
target_journal: "{journal}"
topic: "{topic}"
generator: ARIA Local LLM
status: completed
tags:
  - ieee-paper
  - aria-generated
  - research
---

> [!INFO] IEEE Transactions Paper Generated by ARIA
> **Journal Target:** {journal}  
> **Generated:** {datetime.now().strftime('%B %d, %Y %H:%M')}  
> **Sources Referenced:** {len(sources)} IEEE documents  

"""
        full_paper_md = frontmatter + paper_content

        # Append source metadata at end if available
        if sources:
            full_paper_md += "\n\n---\n\n### Ingested Literature Sources Used\n"
            for idx, src in enumerate(sources, 1):
                doc_name = src.get("metadata", {}).get("file_name") or src.get("document_id") or f"Source {idx}"
                relevance = src.get("similarity_score", 0)
                full_paper_md += f"- **[{idx}]** `{doc_name}` (Relevance Score: {relevance:.1%})\n"

        # Save to file if output_dir specified
        file_path = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_paper_md)
            logger.info(f"Saved generated IEEE paper to: {file_path}")

        return {
            "title": paper_title,
            "filename": filename,
            "file_path": file_path,
            "journal": journal,
            "topic": topic,
            "content": full_paper_md,
            "sources": sources,
            "generated_at": datetime.now().isoformat(),
        }
