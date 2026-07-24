"""
Report Generator - Create research reports from queries with template support.
Supports Markdown and PDF export.
"""

import logging
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from services.llm_service import LLMService
from services.rag import RAGService
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

REPORT_TEMPLATES = {
    "research_summary": {
        "name": "Research Summary",
        "prompt": """Generate a comprehensive research summary report based on the following query and source materials.

Structure:
# {title}

## Executive Summary
Brief overview of findings

## Background & Context
Relevant background information from sources

## Key Findings
Detailed findings organized by theme

## Analysis
Critical analysis and interpretation

## Methodology Notes
How information was gathered and any limitations

## Conclusions & Recommendations
Key takeaways and suggested next steps

## Sources
List of documents referenced

Query: {query}
Sources: {context}""",
    },
    "literature_review": {
        "name": "Literature Review",
        "prompt": """Generate a literature review report.

Structure:
# Literature Review: {title}

## Introduction
Overview of the topic and scope

## Thematic Analysis
Organize findings by theme across sources

## Key Authors & Contributions
Notable contributions from the sources

## Research Gaps
Identified gaps in the literature

## Future Directions
Suggested areas for further research

## Bibliography
Formatted references

Query: {query}
Sources: {context}""",
    },
    "briefing": {
        "name": "Executive Briefing",
        "prompt": """Generate a concise executive briefing.

Structure:
# Briefing: {title}

## Bottom Line Up Front (BLUF)
One paragraph summary

## Key Points
- Bullet point format
- Most important facts

## Supporting Evidence
Brief evidence for each key point

## Implications
What this means for the reader

## Action Items
Recommended next steps

Query: {query}
Sources: {context}""",
    },
    "default": {
        "name": "General Report",
        "prompt": """Generate a detailed report based on the query and sources.

# {title}

## Summary
## Key Information
## Details
## Conclusions

Query: {query}
Sources: {context}""",
    },
}


class ReportGenerator:
    """Generates research reports from RAG queries with template support."""

    def __init__(self):
        self.llm = LLMService()
        self.rag = RAGService()
        os.makedirs(settings.reports_dir, exist_ok=True)

    async def generate(
        self,
        query: str,
        title: Optional[str] = None,
        template: str = "default",
        format: str = "markdown",
        n_sources: int = 10,
    ) -> dict:
        """Generate a full report from a query."""
        title = title or f"Report: {query[:80]}"

        # 1. Retrieve relevant content
        retrieval = await self.rag.query(question=query, n_results=n_sources)
        context = "\n\n".join(retrieval.get("context_chunks", []))
        sources = retrieval.get("sources", [])

        # 2. Get template
        tmpl = REPORT_TEMPLATES.get(template, REPORT_TEMPLATES["default"])
        prompt = tmpl["prompt"].format(
            title=title,
            query=query,
            context=context[:10000],
        )

        # 3. Generate report content
        response = await self.llm.generate(prompt, temperature=0.4)

        # 4. Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}"

        file_path = None
        if format == "markdown":
            file_path = await self._save_markdown(response, filename, title, sources)
        elif format == "pdf":
            file_path = await self._save_pdf(response, filename, title)

        return {
            "title": title,
            "content": response,
            "template": template,
            "format": format,
            "file_path": file_path,
            "sources_used": sources,
            "model_used": settings.ollama_chat_model,
            "generated_at": datetime.now().isoformat(),
        }

    async def _save_markdown(
        self, content: str, filename: str, title: str, sources: list
    ) -> str:
        """Save report as Markdown file."""
        path = os.path.join(settings.reports_dir, f"{filename}.md")

        header = f"""---
title: "{title}"
generated: "{datetime.now().isoformat()}"
generator: ARIA
---

"""
        # Append source references
        source_section = "\n\n---\n\n## Sources\n\n"
        for i, src in enumerate(sources):
            doc_id = src.get("document_id", "unknown")
            score = src.get("similarity_score", 0)
            source_section += f"{i + 1}. Document `{doc_id}` (relevance: {score:.0%})\n"

        full_content = header + content + source_section

        with open(path, "w", encoding="utf-8") as f:
            f.write(full_content)

        logger.info(f"Report saved: {path}")
        return path

    async def _save_pdf(self, content: str, filename: str, title: str) -> str:
        """Save report as PDF using ReportLab."""
        path = os.path.join(settings.reports_dir, f"{filename}.pdf")

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_JUSTIFY

            doc = SimpleDocTemplate(path, pagesize=A4)
            styles = getSampleStyleSheet()

            # Custom styles
            styles.add(ParagraphStyle(
                name="ARIABody",
                parent=styles["Normal"],
                fontSize=11,
                leading=16,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
            ))

            story = []

            # Title
            story.append(Paragraph(title, styles["Title"]))
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph(
                f"Generated by ARIA on {datetime.now().strftime('%B %d, %Y')}",
                styles["Italic"],
            ))
            story.append(Spacer(1, 0.5 * inch))

            # Content — convert markdown to paragraphs
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.1 * inch))
                elif line.startswith("# "):
                    story.append(Paragraph(line[2:], styles["Heading1"]))
                elif line.startswith("## "):
                    story.append(Paragraph(line[3:], styles["Heading2"]))
                elif line.startswith("### "):
                    story.append(Paragraph(line[4:], styles["Heading3"]))
                elif line.startswith("- "):
                    story.append(Paragraph(f"• {line[2:]}", styles["ARIABody"]))
                else:
                    # Escape special XML characters for ReportLab
                    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(safe, styles["ARIABody"]))

            doc.build(story)
            logger.info(f"PDF report saved: {path}")
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            # Fallback to markdown
            return await self._save_markdown(content, filename, title, [])

        return path

    def list_templates(self) -> list[dict]:
        """List available report templates."""
        return [
            {"id": k, "name": v["name"]}
            for k, v in REPORT_TEMPLATES.items()
        ]
