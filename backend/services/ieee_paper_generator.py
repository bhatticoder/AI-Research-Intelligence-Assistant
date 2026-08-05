# -*- coding: utf-8 -*-
"""
IEEE Research Paper Generator Service  v2.0
============================================
Senior Staff Engineer–grade rewrite.

Responsibilities:
  - Retrieve top-K semantically relevant excerpts from ChromaDB (researcher's own papers)
  - Inject bounded context into a tightly-engineered LLM prompt
  - Produce a COMPLETE, publication-ready IEEE Transactions Markdown paper:
      • Full 6-section academic structure
      • Rigorous LaTeX block equations ($$ ... $$) and inline math ($ ... $)
      • Mermaid.js system architecture / flowchart diagrams
      • Markdown performance comparison tables
      • Numeric in-text citations [1], [2] mapped to the researcher's actual source files
      • Obsidian-compatible frontmatter + callouts
  - Save paper to vault's Generated Papers/ directory
  - Return structured metadata dict for API response

Author: ARIA Backend – Phase 3
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

# ══════════════════════════════════════════════════════════════════
# MASTER PROMPT  (v2.0 — production quality)
# ══════════════════════════════════════════════════════════════════

IEEE_PAPER_PROMPT = r"""\

You are a Distinguished Principal Researcher and IEEE Fellow with 25 years of publication experience. \
You are writing a rigorous, COMPLETE IEEE Transactions research paper in Markdown. \
Your writing is authoritative, precise, and mathematically rigorous. \
You DO NOT truncate sections or add placeholder text. \
You produce a FULL paper—every section written out completely.

═══════════════════════════════════════════════════════════
RESEARCHER'S REQUEST
═══════════════════════════════════════════════════════════
Paper Topic / Title Concept : {topic}
Target Journal              : {journal}
Technical Focus / Scope     : {requirements}
Number of Source References : {num_sources}

═══════════════════════════════════════════════════════════
RETRIEVED LITERATURE CONTEXT (researcher's own papers)
═══════════════════════════════════════════════════════════
{context}

═══════════════════════════════════════════════════════════
MANDATORY OUTPUT SPECIFICATION — follow EXACTLY
═══════════════════════════════════════════════════════════

Produce ONLY the complete Markdown paper. Zero preamble, zero post-text.

---

# [Precise, Formal IEEE-Style Title]

**[Author Block]** ARIA Automated Research Intelligence, IEEE Student Member Branch; Local Llama AI Laboratory

---

## Abstract

*One paragraph, 200–280 words.* Summarise: background problem, core novelty, proposed methodology, key results with numbers, and significance. No citations in abstract.

**Index Terms:** [6–10 comma-separated IEEE keywords]

---

## I. Introduction

### A. Background and Motivation
[3–4 paragraphs establishing research context, citing retrieved sources as [N].]

### B. Problem Statement and Existing Limitations
[2–3 paragraphs precisely defining the unsolved problem. Reference specific gaps from the literature [N].]

### C. Primary Novel Contributions
This paper makes the following principal contributions:
- **C1:** [Contribution 1 — specific and measurable]
- **C2:** [Contribution 2]
- **C3:** [Contribution 3]
- **C4:** [Contribution 4]

### D. Paper Organisation
[One sentence per section describing the paper structure.]

---

## II. Related Work and Literature Review

### A. [First Thematic Cluster]
[2–3 paragraphs. Synthesise retrieved literature with citations [N]. Compare methodologies.]

### B. [Second Thematic Cluster]
[2–3 paragraphs. Identify the gap this paper fills.]

### C. Comparative Positioning

| Approach | Method | Dataset | Key Metric | Limitation |
|---|---|---|---|---|
| [Ref N] | ... | ... | ... | ... |
| [Ref N] | ... | ... | ... | ... |
| **Proposed** | ... | ... | ... | — |

---

## III. Proposed Methodology and Theoretical Formulation

### A. System Architecture Overview

```mermaid
flowchart TD
    A[Input: Researcher Papers] --> B[Document Processor\nPyMuPDF + OCR]
    B --> C[Semantic Chunker]
    C --> D[(ChromaDB\nVector Store)]
    D --> E[RAG Retriever\nTop-K Cosine Search]
    E --> F[Local LLM\nOllama / Llama]
    F --> G[IEEE Paper Output\nMarkdown + LaTeX]
    G --> H[Obsidian Vault\nGenerated Papers/]
```

[2 paragraphs describing the architecture.]

### B. Mathematical Formulation

Let the input document corpus be $\mathcal{{D}} = \{{d_1, d_2, \ldots, d_N\}}$ where each $d_i$ is segmented into chunks $\mathcal{{C}}_i = \{{c_{{i,1}}, \ldots, c_{{i,K}}\}}$.

**Embedding function:** For a chunk $c$, the embedding is computed as:

$$
\mathbf{{e}}(c) = \text{{Enc}}_\theta(c) \in \mathbb{{R}}^d
$$

where $\text{{Enc}}_\theta$ is the sentence encoder parameterised by $\theta$ and $d$ is the embedding dimension.

**Retrieval scoring:** Given query $q$, top-$K$ chunks are retrieved by cosine similarity:

$$
\text{{sim}}(q, c) = \frac{{\mathbf{{e}}(q)^\top \mathbf{{e}}(c)}}{{\|\mathbf{{e}}(q)\| \cdot \|\mathbf{{e}}(c)\|}}
$$

$$
\mathcal{{R}}(q) = \underset{{c \in \mathcal{{C}}}}{{\text{{top-}}K}} \; \text{{sim}}(q, c)
$$

**Generation objective:** The language model $p_\phi$ is conditioned on the retrieved context:

$$
\hat{{y}} = \arg\max_{{y}} \; p_\phi\!\left(y \mid q, \mathcal{{R}}(q)\right)
$$

[Continue with 2–3 topic-specific equations central to the paper topic, e.g., loss functions, optimisation bounds, or domain-specific formulations. Make them rigorous and directly relevant to "{topic}".]

### C. Algorithmic Description

**Algorithm 1:** [Name of Primary Algorithm]

```
Input:  Query q, Corpus D, Parameters theta, phi, K
Output: Generated paper y_hat

1: Pre-process D -> chunks C via semantic chunker
2: Encode C -> embeddings {{e(c)}} using Enc_theta
3: Encode query q -> e(q)
4: Retrieve R(q) = top-K chunks by cosine similarity
5: Format prompt P = [system_template, R(q), q]
6: Generate y_hat = p_phi(y | P) via autoregressive decoding
7: Apply post-processing: inject frontmatter, save to vault
8: Return y_hat
```

### D. Complexity Analysis
[Discuss time and space complexity of the proposed approach. Use Big-O notation.]

---

## IV. Experimental Evaluation and Performance Analysis

### A. Experimental Setup
[Describe datasets, hardware, hyperparameters, baseline systems. 2 paragraphs.]

### B. Evaluation Metrics
[Define metrics: ROUGE-L, BERTScore, citation precision, generation latency, etc.]

### C. Baseline Comparison

| Model / System | ROUGE-L | BERTScore F1 | Citation Prec. | Latency (s) |
|---|---|---|---|---|
| GPT-4 (API) | — | — | — | — |
| RAG + GPT-3.5 | — | — | — | — |
| Fine-tuned LLaMA | — | — | — | — |
| **ARIA (Proposed)** | **—** | **—** | **—** | **—** |

### D. Ablation Study

| Ablation Variant | Δ ROUGE-L | Δ BERTScore |
|---|---|---|
| w/o RAG retrieval | −X.X | −X.X |
| w/o LaTeX formatting | −X.X | −X.X |
| w/o citation grounding | −X.X | −X.X |
| Full ARIA System | Baseline | Baseline |

### E. Qualitative Analysis

```mermaid
graph LR
    subgraph "Quality Dimensions"
        A[Factual Accuracy] --> E[Overall Score]
        B[Mathematical Rigour] --> E
        C[Citation Precision] --> E
        D[Structural Compliance] --> E
    end
```

[2 paragraphs discussing qualitative findings and error analysis.]

---

## V. Discussion and Open Research Challenges

### A. Theoretical Implications
[2 paragraphs on theoretical significance.]

### B. Limitations
[Honest discussion of current limitations: LLM hallucination, context window constraints, dependency on ingested corpus quality.]

### C. Open Research Challenges
1. **Scalability:** [Challenge description]
2. **Multimodal Input:** [Challenge description]
3. **Automated Verification:** [Challenge description]

---

## VI. Conclusion and Future Directions

### A. Summary of Contributions
[2 paragraphs summarising what was achieved and demonstrated.]

### B. Future Research Roadmap
- [Future direction 1]
- [Future direction 2]
- [Future direction 3]

---

## References

{references_block}

---
*Generated by ARIA v2.0 — AI Research & Intelligence Assistant*
"""

# ── Reference block builder ──────────────────────────────────────
_IEEE_REF_TEMPLATE = "[{n}] {author}, \"{title},\" *{journal}*, vol. XX, no. X, pp. XX–XX, {year}."


def _build_references_block(sources: List[Dict]) -> str:
    """Build an IEEE-style numbered reference list from retrieved source metadata."""
    lines = []
    for i, src in enumerate(sources, 1):
        meta = src.get("metadata", {})
        file_name = meta.get("file_name", "").replace(".pdf", "").replace(".md", "").replace("_", " ")
        title = file_name if file_name else f"Reference Document {i}"
        author = meta.get("author", "Author et al.")
        year = meta.get("year", datetime.now().year)
        rel_path = meta.get("relative_path", "")
        lines.append(f"[{i}] {author}, \"{title},\" *IEEE Transactions*, {year}. (Source: `{rel_path}`)")
    return "\n".join(lines) if lines else "[1] No literature sources indexed. Ingest papers into `IEEE Reports/` and re-run."


# ══════════════════════════════════════════════════════════════════
# SERVICE CLASS
# ══════════════════════════════════════════════════════════════════

class IEEEPaperGenerator:
    """
    Generates complete, publication-quality IEEE Transactions research papers.

    Pipeline:
      1. Retrieve top-K semantically relevant chunks from ChromaDB
      2. Build bounded context string (guards against LLM context overflow)
      3. Construct structured prompt with LaTeX/Mermaid/Table directives
      4. Stream or call LLM for generation
      5. Extract title, inject Obsidian frontmatter
      6. Append grounded reference list
      7. Save Markdown file to vault's Generated Papers/ directory
    """

    # Maximum context characters fed to LLM.
    # ~4 chars per token; 4000 chars ≈ 1000 tokens — safe for 4K–8K context models.
    _MAX_CONTEXT_CHARS = 4000

    def __init__(self):
        self.llm = LLMService()
        self.embeddings = EmbeddingService()

    # ── Public API ───────────────────────────────────────────────

    async def generate_paper(
        self,
        topic: str,
        journal: str = "IEEE Transactions on Neural Networks and Learning Systems",
        requirements: str = "",
        output_dir: Optional[str] = None,
        n_sources: int = 8,
    ) -> Dict[str, Any]:
        """
        Generate a complete IEEE research paper.

        Args:
            topic: Research topic or title concept.
            journal: Target IEEE journal name.
            requirements: Researcher's specific technical focus and constraints.
            output_dir: Absolute path to save the Markdown file.
            n_sources: Number of literature excerpts to retrieve from ChromaDB.

        Returns:
            Dict with keys: title, filename, file_path, journal, topic,
                            content, sources, generated_at
        """
        logger.info(f"[IEEEGen] Starting paper: '{topic}' → {journal}")

        # ── Step 1: Literature Retrieval ──────────────────────────
        sources = await self._retrieve_sources(topic, requirements, n_sources)
        context_str = self._build_context_string(sources)
        references_block = _build_references_block(sources)

        logger.info(f"[IEEEGen] Retrieved {len(sources)} source chunks | "
                    f"context={len(context_str)} chars")

        # ── Step 2: Prompt Construction ───────────────────────────
        prompt = IEEE_PAPER_PROMPT.format(
            topic=topic,
            journal=journal,
            requirements=requirements or "Provide a comprehensive general investigation with rigorous mathematical treatment.",
            num_sources=len(sources),
            context=context_str,
            references_block=references_block,
        )

        # ── Step 3: LLM Generation ────────────────────────────────
        logger.info("[IEEEGen] Invoking LLM — this may take 1–5 minutes on local hardware…")
        try:
            paper_body = await self.llm.generate(prompt, temperature=0.25)
        except Exception as exc:
            logger.error(f"[IEEEGen] LLM generation failed: {exc}")
            raise RuntimeError(f"LLM generation failed: {exc}") from exc

        if not paper_body or len(paper_body) < 200:
            raise RuntimeError("LLM returned an empty or trivially short paper. Check Ollama model availability.")

        # ── Step 4: Post-processing ───────────────────────────────
        paper_title = self._extract_title(paper_body, topic)
        filename = self._make_filename(paper_title)
        frontmatter = self._build_frontmatter(paper_title, journal, topic, len(sources))
        sources_footer = self._build_sources_footer(sources)

        full_md = frontmatter + paper_body + sources_footer

        # ── Step 5: Save to disk ──────────────────────────────────
        file_path = None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, filename)
            try:
                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.write(full_md)
                logger.info(f"[IEEEGen] ✅ Saved paper → {file_path}")
            except OSError as exc:
                logger.error(f"[IEEEGen] Failed to save paper: {exc}")
                file_path = None

        # ── Step 6: Return result dict ──────────────────
        return {
            "title": paper_title,
            "filename": filename,
            "file_path": file_path,
            "journal": journal,
            "topic": topic,
            "content": full_md,
            "sources": sources,
            "generated_at": datetime.now().isoformat(),
        }

    def _build_latex_from_markdown(self, markdown_body: str, title: str, journal: str, sources: List[Dict]) -> tuple:
        """Build an IEEEtran LaTeX (.tex + .bib) from generated Markdown paper body."""
        return "", ""

        # ── Extract abstract ──────────────────────────────────────────────
        abstract = ""
        abstract_match = re.search(
            r"## Abstract\s*\n+(.+?)(?=\n## |\Z)", markdown_body, re.DOTALL
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            # Strip markdown formatting
            abstract = re.sub(r"\*\*(.+?)\*\*", r"\1", abstract)
            abstract = re.sub(r"\*(.+?)\*", r"\1", abstract)
            abstract = re.sub(r"\[(.+?)\]", r"\1", abstract)  # strip cite brackets from abstract

        # ── Extract sections ──────────────────────────────────────────────
        section_pattern = re.compile(
            r"## ([IVX]+\.\s+.+?)\n(.+?)(?=\n## [IVX]+\.\s|\Z)", re.DOTALL
        )
        body_sections = {}
        for m in section_pattern.finditer(markdown_body):
            sec_title_raw = m.group(1).strip()
            sec_body_raw = m.group(2).strip()

            # Clean title — remove roman numeral prefix for LaTeX \section{}
            sec_title = re.sub(r"^[IVX]+\.\s+", "", sec_title_raw)

            # Convert basic Markdown to LaTeX in body
            sec_body = self._markdown_section_to_latex(sec_body_raw)
            body_sections[sec_title] = sec_body

        if not body_sections:
            # Fallback: dump everything as a single section
            body_sections["Generated Content"] = _latex_escape(markdown_body[:3000])

        # ── Build bibliography from sources ───────────────────────────────
        bib_refs = []
        for src in sources:
            meta = src.get("metadata", {})
            key = f"ref{src['ref_num']}"
            bib_refs.append({
                "key": key,
                "n": src["ref_num"],
                "author": meta.get("author", "Author, A."),
                "title": meta.get("title", f"Reference {src['ref_num']}"),
                "journal": meta.get("journal", "IEEE Transactions"),
                "year": meta.get("year", str(datetime.now().year)),
                "volume": "1",
                "pages": "1--10",
            })

        tex_content, bib_content = build_ieeeetran_latex(
            title=title,
            authors="ARIA Research Intelligence System, Local AI Laboratory",
            abstract=abstract or "Abstract generated by ARIA v2.0 local AI research assistant.",
            body_sections=body_sections,
            references=bib_refs,
            journal=journal,
        )
        return tex_content, bib_content

    @staticmethod
    def _markdown_section_to_latex(text: str) -> str:
        """Convert a Markdown section body to basic LaTeX."""
        import re as _re
        # Subsections (### A. Title → \subsection{Title})
        text = _re.sub(r"^### [A-Z]\.\s+(.+)$", r"\\subsection{\1}", text, flags=_re.MULTILINE)
        # Bold (**text** → \textbf{text})
        text = _re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
        # Italic (*text* → \textit{text})
        text = _re.sub(r"\*(.+?)\*", r"\\textit{\1}", text)
        # Code (`text` → \texttt{text})
        text = _re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
        # Wiki-style citation [N] → \cite{refN}
        text = _re.sub(r"\[([0-9]+)\]", r"\\cite{ref\1}", text)
        # Mermaid blocks → replace with placeholder figure comment
        text = _re.sub(
            r"```mermaid[\s\S]+?```",
            r"% [Figure: Architecture diagram — insert TikZ or graphicx figure here]",
            text,
        )
        # Other code blocks → verbatim
        text = _re.sub(r"```[a-z]*([\s\S]+?)```", r"\\begin{verbatim}\1\\end{verbatim}", text)
        # Markdown tables → simple tabular (best-effort)
        # LaTeX block equations (already in $$ ... $$ format, keep as-is)
        # Inline $ ... $ stays as-is
        # Bullet lists (- item → \item)
        lines = text.split("\n")
        result_lines = []
        in_itemize = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_itemize:
                    result_lines.append("\\begin{itemize}")
                    in_itemize = True
                result_lines.append(f"  \\item {stripped[2:]}")
            else:
                if in_itemize:
                    result_lines.append("\\end{itemize}")
                    in_itemize = False
                result_lines.append(line)
        if in_itemize:
            result_lines.append("\\end{itemize}")
        return "\n".join(result_lines)

    # ── Private Helpers ──────────────────────────────────────────

    async def _retrieve_sources(
        self, topic: str, requirements: str, n_sources: int
    ) -> List[Dict]:
        """Query ChromaDB for semantically relevant literature chunks."""
        query = f"{topic} {requirements}".strip()
        try:
            retrieval = await self.embeddings.query(
                query_text=query,
                n_results=min(n_sources, 15),  # hard cap — protect small models
            )
        except Exception as exc:
            logger.warning(f"[IEEEGen] ChromaDB retrieval failed ({exc}). Proceeding without context.")
            return []

        documents: List[str] = retrieval.get("documents", [])
        metadatas: List[dict] = retrieval.get("metadatas", [])
        distances: List[float] = retrieval.get("distances", [])

        sources = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            # Convert cosine distance → similarity (ChromaDB uses 1−cos for cosine space)
            similarity = round(max(0.0, 1.0 - dist), 4)
            sources.append({
                "ref_num": i + 1,
                "document_id": meta.get("document_id", f"doc_{i}"),
                "chunk_preview": doc[:300] + ("…" if len(doc) > 300 else ""),
                "chunk_text": doc,
                "similarity_score": similarity,
                "metadata": meta,
            })

        return sources

    def _build_context_string(self, sources: List[Dict]) -> str:
        """Build a bounded context block for the LLM prompt."""
        if not sources:
            return (
                "No literature found in the vector store. "
                "The researcher should place reference PDFs in 'IEEE Reports/' "
                "and trigger a sync before generating a paper. "
                "Proceed using foundational knowledge only."
            )

        parts = []
        total_chars = 0
        for src in sources:
            chunk = src["chunk_text"]
            meta = src["metadata"]
            file_label = meta.get("file_name", f"Source {src['ref_num']}")
            header = f"[Ref {src['ref_num']} | Source: {file_label} | Relevance: {src['similarity_score']:.0%}]"
            entry = f"{header}\n{chunk}"

            if total_chars + len(entry) > self._MAX_CONTEXT_CHARS:
                # Include partial chunk up to limit
                remaining = self._MAX_CONTEXT_CHARS - total_chars
                if remaining > 100:
                    parts.append(entry[:remaining] + "\n[…truncated for context window]")
                break

            parts.append(entry)
            total_chars += len(entry)

        return "\n\n---\n\n".join(parts)

    def _extract_title(self, paper_body: str, fallback_topic: str) -> str:
        """Extract the H1 title from generated paper."""
        match = re.search(r"^#\s+(.+)", paper_body, re.MULTILINE)
        if match:
            # Strip any trailing bold/italic markers
            return re.sub(r"[*_`]", "", match.group(1)).strip()
        return fallback_topic.title()

    def _make_filename(self, title: str) -> str:
        """Create a filesystem-safe filename from the paper title."""
        safe = re.sub(r'[\\/*?:"<>|]', "", title)
        safe = re.sub(r"\s+", "_", safe)[:70]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe}_{timestamp}.md"

    def _build_frontmatter(
        self, title: str, journal: str, topic: str, num_sources: int
    ) -> str:
        """Build Obsidian-compatible YAML frontmatter + info callout."""
        now = datetime.now()
        return f"""---
title: "{title}"
date: {now.strftime('%Y-%m-%d')}
time: {now.strftime('%H:%M')}
type: ieee-research-paper
target_journal: "{journal}"
topic: "{topic}"
generator: "ARIA v2.0 — Local LLM"
sources_used: {num_sources}
status: generated
tags:
  - ieee-paper
  - aria-generated
  - research
  - local-ai
---

> [!ABSTRACT] IEEE Transactions Paper — Generated by ARIA v2.0
> **Journal Target:** {journal}
> **Topic:** {topic}
> **Generated:** {now.strftime('%B %d, %Y at %H:%M')}
> **Literature Sources Used:** {num_sources} indexed excerpts from researcher's vault
> **Rendering:** Enable *Dataview* and *Mermaid* in Obsidian for full diagram rendering.

"""

    def _build_sources_footer(self, sources: List[Dict]) -> str:
        """Append a structured sources table at the bottom of the paper."""
        if not sources:
            return ""

        footer = "\n\n---\n\n### 📚 Indexed Literature Sources Used in Synthesis\n\n"
        footer += "| # | Source File | Relevance | Document ID |\n"
        footer += "|---|---|---|---|\n"
        for src in sources:
            meta = src.get("metadata", {})
            file_name = meta.get("file_name", src.get("document_id", f"Source {src['ref_num']}"))
            rel = src.get("similarity_score", 0)
            doc_id = src.get("document_id", "—")
            footer += f"| [{src['ref_num']}] | `{file_name}` | {rel:.0%} | `{doc_id[:20]}` |\n"

        return footer
