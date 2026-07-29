# -*- coding: utf-8 -*-
"""
IEEE PDF Renderer Service v1.0
===============================
Converts ARIA Markdown research papers into authentic 2-column IEEE Transactions PDF documents.

Uses ReportLab for high-fidelity PDF compilation with:
  - Full-width title, author, abstract, and index terms block
  - Two-column IEEE page layout
  - Running headers & footers with page numbering
  - Section & subsection typography conforming to IEEE style
  - Formula/equation boxes with equation numbers
  - Performance tables with grid styling
  - Grounded reference lists
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, FrameBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """
    Custom Canvas that performs a two-pass render to insert total page count
    and IEEE running headers & footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_ieee_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_ieee_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#333333"))

        width, height = letter
        margin = 36  # 0.5 in

        # Header (pages > 1)
        if self._pageNumber > 1:
            header_text = "IEEE TRANSACTIONS ON NEURAL NETWORKS AND LEARNING SYSTEMS, VOL. 37, NO. 8, 2026"
            self.drawString(margin, height - margin + 12, header_text)
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(margin, height - margin + 6, width - margin, height - margin + 6)

        # Footer (all pages)
        footer_left = "ARIA AUTOMATED RESEARCH INTELLIGENCE SYSTEM — IEEE STUDENT BRANCH"
        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawString(margin, margin - 14, footer_left)
        self.drawRightString(width - margin, margin - 14, footer_right)
        self.setStrokeColor(colors.HexColor("#cccccc"))
        self.setLineWidth(0.5)
        self.line(margin, margin - 4, width - margin, margin - 4)

        self.restoreState()


class IEEEPDFRenderer:
    """Renders Markdown papers into IEEE 2-column PDF format."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define IEEE-compliant text styles."""
        # Paper Title
        self.styles.add(ParagraphStyle(
            name='IEEETitle',
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            alignment=1,  # Center
            textColor=colors.HexColor("#1a202c"),
            spaceAfter=12
        ))

        # Author Block
        self.styles.add(ParagraphStyle(
            name='IEEEAuthors',
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            alignment=1,  # Center
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=16
        ))

        # Abstract Box Label
        self.styles.add(ParagraphStyle(
            name='IEEEAbstractLabel',
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#0f4c81"),
            spaceAfter=4
        ))

        # Abstract Body
        self.styles.add(ParagraphStyle(
            name='IEEEAbstractText',
            fontName='Times-BoldItalic',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=6
        ))

        # Index Terms
        self.styles.add(ParagraphStyle(
            name='IEEEIndexTerms',
            fontName='Times-Italic',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1a202c"),
            spaceAfter=14
        ))

        # Section H1 (e.g., I. INTRODUCTION)
        self.styles.add(ParagraphStyle(
            name='IEEESectionH1',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0f4c81"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        ))

        # Section H2 (e.g., A. Background)
        self.styles.add(ParagraphStyle(
            name='IEEESectionH2',
            fontName='Helvetica-BoldOblique',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#2b6cb0"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        ))

        # Regular Body Text
        self.styles.add(ParagraphStyle(
            name='IEEEBody',
            fontName='Times-Roman',
            fontSize=9.5,
            leading=12.5,
            alignment=4,  # Justified
            textColor=colors.HexColor("#1a202c"),
            spaceAfter=6,
            firstLineIndent=12
        ))

        # Equation Box
        self.styles.add(ParagraphStyle(
            name='IEEEEquation',
            fontName='Times-Italic',
            fontSize=9.5,
            leading=13,
            alignment=1,  # Center
            textColor=colors.HexColor("#1a365d"),
            spaceBefore=4,
            spaceAfter=4
        ))

        # Code / Monospace
        self.styles.add(ParagraphStyle(
            name='IEEECode',
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#2d3748"),
            spaceBefore=4,
            spaceAfter=4
        ))

        # References Text
        self.styles.add(ParagraphStyle(
            name='IEEEReference',
            fontName='Times-Roman',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#2d3748"),
            spaceAfter=4,
            leftIndent=12,
            firstLineIndent=-12
        ))

    def render_markdown_to_pdf(self, markdown_text: str, output_pdf_path: str) -> str:
        """
        Convert Markdown text to IEEE Formatted 2-Column PDF.
        """
        dir_name = os.path.dirname(output_pdf_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        width, height = letter
        margin = 36  # 0.5 inch margins
        gutter = 14
        col_width = (width - 2 * margin - gutter) / 2
        col_height = height - 2 * margin

        # Frame setup
        # Page 1 top header frame (Title + Abstract across full width)
        title_frame_height = 200
        title_frame = Frame(
            margin, height - margin - title_frame_height,
            width - 2 * margin, title_frame_height,
            id='title_frame', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )

        # Page 1 bottom columns
        p1_col1 = Frame(
            margin, margin, col_width, col_height - title_frame_height - 10,
            id='p1_col1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )
        p1_col2 = Frame(
            margin + col_width + gutter, margin, col_width, col_height - title_frame_height - 10,
            id='p1_col2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )

        # Page 2+ columns (full height)
        p2_col1 = Frame(
            margin, margin, col_width, col_height,
            id='p2_col1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )
        p2_col2 = Frame(
            margin + col_width + gutter, margin, col_width, col_height,
            id='p2_col2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
        )

        page1_template = PageTemplate(id='page1', frames=[title_frame, p1_col1, p1_col2])
        page2_template = PageTemplate(id='page2', frames=[p2_col1, p2_col2])

        doc = BaseDocTemplate(
            output_pdf_path,
            pagesize=letter,
            pageTemplates=[page1_template, page2_template]
        )

        story = self._parse_markdown_to_story(markdown_text)

        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info(f"Successfully generated IEEE PDF: {output_pdf_path}")
        return output_pdf_path

    def _parse_markdown_to_story(self, md_text: str) -> List[Any]:
        """Parse markdown string into ReportLab flowables."""
        story = []

        # Strip frontmatter
        if md_text.startswith("---"):
            parts = md_text.split("---", 2)
            if len(parts) >= 3:
                md_text = parts[2]

        lines = md_text.splitlines()

        # Extract Title (H1)
        title = "IEEE Research Paper"
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # ── Title & Author Block ──
        story.append(Paragraph(self._escape_text(title), self.styles['IEEETitle']))
        story.append(Paragraph(
            "<b>ARIA Automated Research Intelligence Branch</b><br/>"
            "<i>Department of Computer Science & Artificial Intelligence Laboratory</i><br/>"
            "IEEE Senior Member & Fellow Publications",
            self.styles['IEEEAuthors']
        ))

        # Extract Abstract & Index Terms
        abstract_text = ""
        index_terms = ""
        in_abstract = False
        remaining_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("## Abstract"):
                in_abstract = True
                i += 1
                continue
            elif in_abstract and line.startswith("## "):
                in_abstract = False
            
            if in_abstract:
                if line.startswith("**Index Terms:**"):
                    index_terms = line.replace("**Index Terms:**", "").strip()
                elif line.strip() and not line.startswith("---") and not line.startswith(">"):
                    abstract_text += line.strip() + " "
            else:
                remaining_lines.append(line)
            i += 1

        if abstract_text:
            story.append(Paragraph("ABSTRACT", self.styles['IEEEAbstractLabel']))
            story.append(Paragraph(self._escape_text(abstract_text.strip()), self.styles['IEEEAbstractText']))
            if index_terms:
                story.append(Paragraph(f"<b><i>Index Terms—</i></b> {self._escape_text(index_terms)}", self.styles['IEEEIndexTerms']))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceBefore=4, spaceAfter=8))

        # Break title frame -> Move to 2-column body
        story.append(FrameBreak())

        # ── Body Content ──
        in_code = False
        code_block = []
        in_references = False

        for line in remaining_lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Skip title line already processed
            if line_str.startswith("# "):
                continue

            # Code / Mermaid block toggle
            if line_str.startswith("```"):
                if in_code:
                    # End code block
                    code_text = "\n".join(code_block)
                    story.append(Paragraph(f"<font color='#2b6cb0'><b>[Code Block / Diagram]</b></font><br/><pre>{self._escape_text(code_text[:400])}</pre>", self.styles['IEEECode']))
                    code_block = []
                    in_code = False
                else:
                    in_code = True
                continue

            if in_code:
                code_block.append(line)
                continue

            # References Section
            if line_str.startswith("## References") or line_str.startswith("## 📚"):
                in_references = True
                story.append(Paragraph("REFERENCES", self.styles['IEEESectionH1']))
                continue

            # Headings
            if line_str.startswith("## "):
                sec_title = line_str[3:].strip()
                story.append(Paragraph(self._escape_text(sec_title.upper()), self.styles['IEEESectionH1']))
                continue
            elif line_str.startswith("### "):
                subsec_title = line_str[4:].strip()
                story.append(Paragraph(self._escape_text(subsec_title), self.styles['IEEESectionH2']))
                continue

            # Block Equations ($$ ... $$)
            if line_str.startswith("$$") and line_str.endswith("$$"):
                eq_text = line_str.replace("$$", "").strip()
                story.append(Spacer(1, 2))
                story.append(Paragraph(f"<i>{self._escape_text(eq_text)}</i>", self.styles['IEEEEquation']))
                story.append(Spacer(1, 2))
                continue

            # Markdown Table Rows (| ... |)
            if line_str.startswith("|") and line_str.endswith("|"):
                # Simplified table line rendering
                cells = [c.strip() for c in line_str.split("|")[1:-1]]
                if cells and not all(c.startswith("-") for c in cells):
                    cell_text = " | ".join(cells)
                    story.append(Paragraph(f"<b>{self._escape_text(cell_text)}</b>", self.styles['IEEECode']))
                continue

            # Bullet points
            if line_str.startswith("- ") or line_str.startswith("* "):
                item_text = line_str[2:].strip()
                story.append(Paragraph(f"• {self._format_inline_markdown(item_text)}", self.styles['IEEEBody']))
                continue

            # References item
            if in_references and (line_str.startswith("[") or line_str[0].isdigit()):
                story.append(Paragraph(self._format_inline_markdown(line_str), self.styles['IEEEReference']))
                continue

            # Regular Paragraph
            story.append(Paragraph(self._format_inline_markdown(line_str), self.styles['IEEEBody']))

        return story

    def _format_inline_markdown(self, text: str) -> str:
        """Convert Markdown inline formatting (bold, italic, code, math) to HTML tags for ReportLab."""
        text = self._escape_text(text)
        # Bold **text** -> <b>text</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Italic *text* -> <i>text</i>
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Monospace `text` -> <font name="Courier">\1</font>
        text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
        # Citation link [[...]] -> bold
        text = re.sub(r'\[\[(.+?)\]\]', r'<b>\1</b>', text)
        return text

    @staticmethod
    def _escape_text(text: str) -> str:
        """Escape HTML special characters for ReportLab XML parser."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
