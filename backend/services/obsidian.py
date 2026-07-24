"""
Obsidian Sync & Command Service
Bi-directional sync between Obsidian vault and ARIA backend.
Handles:
- Monitoring vault for changes
- Auto-ingest IEEE reports into ChromaDB
- Auto-executing paper generation commands from Obsidian notes
- Maintaining live Dashboard.md in Obsidian
"""

import logging
import os
import re
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from config import get_settings
from services.document_processor import DocumentProcessor
from services.embeddings import EmbeddingService
from services.ieee_paper_generator import IEEEPaperGenerator
from services.llm_service import LLMService

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class VaultFile:
    """Represents a file in the Obsidian vault."""
    path: str
    name: str
    relative_path: str
    size: int
    modified: datetime
    hash: str
    is_markdown: bool
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass
class SyncStatus:
    """Current sync status."""
    is_syncing: bool = False
    last_sync: Optional[datetime] = None
    vault_path: Optional[str] = None
    total_files: int = 0
    synced_files: int = 0
    pending_files: int = 0
    indexed_documents: int = 0
    errors: list[str] = field(default_factory=list)


class ObsidianSyncService:
    """
    Manages Obsidian vault synchronization, command execution, and live dashboard generation.
    """

    def __init__(self):
        self.vault_path: Optional[str] = settings.obsidian_vault_path or r"G:\Obsedian Files\ARIA"
        self.sync_interval: int = settings.obsidian_sync_interval or 30
        self.status = SyncStatus(vault_path=self.vault_path)
        self._file_hashes: dict[str, str] = {}  # path -> hash
        self._watching = False
        self._on_file_changed: Optional[Callable] = None
        self._watch_task: Optional[asyncio.Task] = None
        self.doc_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.paper_generator = IEEEPaperGenerator()
        self.llm_service = LLMService()

        # Ensure essential directories exist inside vault
        self._ensure_vault_folders()

    def _ensure_vault_folders(self):
        """Ensure default folders exist in Obsidian vault."""
        if self.vault_path and os.path.exists(self.vault_path):
            folders = ["IEEE Reports", "Commands", "Generated Papers", "Templates"]
            for f in folders:
                os.makedirs(os.path.join(self.vault_path, f), exist_ok=True)

    def set_vault_path(self, path: str):
        """Update the vault path."""
        if not os.path.isdir(path):
            raise ValueError(f"Vault path does not exist: {path}")
        self.vault_path = path
        self.status.vault_path = path
        self._ensure_vault_folders()
        logger.info(f"Vault path set to: {path}")

    # ── Vault Scanning ────────────────────────────────────────────

    async def scan_vault(self) -> list[VaultFile]:
        """Scan vault files."""
        if not self.vault_path or not os.path.exists(self.vault_path):
            logger.warning("Vault path not set or does not exist")
            return []

        vault = Path(self.vault_path)
        files = []

        supported = {".md", ".markdown", ".txt", ".pdf", ".docx", ".html"}
        skip_dirs = {".obsidian", ".trash", ".git", "node_modules"}

        for root, dirs, filenames in os.walk(vault):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]

            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext not in supported:
                    continue

                file_path = os.path.join(root, filename)
                relative = os.path.relpath(file_path, self.vault_path)

                try:
                    stat = os.stat(file_path)
                    file_hash = self._quick_hash(file_path)

                    vf = VaultFile(
                        path=file_path,
                        name=filename,
                        relative_path=relative,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        hash=file_hash,
                        is_markdown=ext in {".md", ".markdown"},
                    )

                    if vf.is_markdown:
                        vf.tags, vf.links = self._extract_obsidian_meta(file_path)

                    files.append(vf)
                except Exception as e:
                    logger.error(f"Error scanning {file_path}: {e}")

        self.status.total_files = len(files)
        return files

    async def detect_changes(self) -> dict:
        """Compare current vault state with cached hashes to find changes."""
        files = await self.scan_vault()
        current_hashes = {f.path: f.hash for f in files}

        new_files = []
        modified_files = []
        deleted_paths = []

        for f in files:
            if f.path not in self._file_hashes:
                new_files.append(f)
            elif self._file_hashes[f.path] != f.hash:
                modified_files.append(f)

        for cached_path in self._file_hashes:
            if cached_path not in current_hashes:
                deleted_paths.append(cached_path)

        self._file_hashes = current_hashes

        return {
            "new": new_files,
            "modified": modified_files,
            "deleted": deleted_paths,
            "unchanged": len(files) - len(new_files) - len(modified_files),
        }

    # ── Auto Ingestion & Processing ───────────────────────────────

    async def _ingest_file(self, vault_file: VaultFile):
        """Process and embed vault document into ChromaDB."""
        # Skip Dashboard or Generated Papers from auto-ingestion loops
        rel = vault_file.relative_path.replace("\\", "/")
        if rel in ["Dashboard.md"] or rel.startswith("Generated Papers/"):
            return

        try:
            logger.info(f"Auto-ingesting document into ChromaDB: {vault_file.relative_path}")
            doc_result = await self.doc_processor.process_file(vault_file.path)
            if doc_result.chunks:
                doc_id = f"obsidian_{hashlib.md5(vault_file.relative_path.encode()).hexdigest()[:12]}"
                meta = {
                    "file_name": vault_file.name,
                    "relative_path": vault_file.relative_path,
                    "source": "obsidian",
                    "tags": ",".join(vault_file.tags),
                }
                metadatas = [meta] * len(doc_result.chunks)
                await self.embedding_service.add_documents(
                    doc_id=doc_id,
                    chunks=doc_result.chunks,
                    metadatas=metadatas
                )
                self.status.indexed_documents += 1
                logger.info(f"Successfully embedded {len(doc_result.chunks)} chunks from {vault_file.name}")
        except Exception as e:
            logger.error(f"Failed to ingest file {vault_file.path}: {e}")

    # ── Command Processing ────────────────────────────────────────

    async def process_pending_commands(self):
        """Find notes tagged with aria_action: generate_paper and status: pending, and execute them."""
        if not self.vault_path or not os.path.exists(self.vault_path):
            return

        commands_dir = os.path.join(self.vault_path, "Commands")
        gen_dir = os.path.join(self.vault_path, "Generated Papers")

        # Scan all .md files in Commands directory & vault for pending frontmatter
        for root, _, filenames in os.walk(self.vault_path):
            for fn in filenames:
                if not fn.endswith((".md", ".markdown")):
                    continue
                fp = os.path.join(root, fn)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    if "aria_action: generate_paper" in content and "status: pending" in content:
                        logger.info(f"Found pending paper generation command in: {fn}")

                        # Extract frontmatter fields
                        topic_m = re.search(r'topic:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
                        journal_m = re.search(r'target_journal:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
                        req_m = re.search(r'requirements:\s*["\']?(.*?)["\']?\s*$', content, re.MULTILINE)

                        topic = topic_m.group(1).strip() if topic_m else fn.replace(".md", "").replace("Generate IEEE Paper - ", "")
                        journal = journal_m.group(1).strip() if journal_m else "IEEE Transactions on Neural Networks and Learning Systems"
                        requirements = req_m.group(1).strip() if req_m else ""

                        # 1. Update status to processing
                        content_processing = content.replace("status: pending", "status: processing")
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(content_processing)

                        # 2. Generate IEEE Paper
                        result = await self.paper_generator.generate_paper(
                            topic=topic,
                            journal=journal,
                            requirements=requirements,
                            output_dir=gen_dir
                        )

                        # 3. Update status to completed
                        generated_rel_link = f"[[Generated Papers/{result['filename']}]]"
                        content_completed = content_processing.replace(
                            "status: processing",
                            f"status: completed\ngenerated_paper: \"{generated_rel_link}\""
                        )
                        # Append reference note to bottom of command file
                        content_completed += f"\n\n> [!SUCCESS] IEEE Paper Generation Completed!\n> **Result:** {generated_rel_link}\n> **Generated At:** {result['generated_at']}\n"

                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(content_completed)

                        logger.info(f"Completed IEEE paper generation command for {topic}")

                except Exception as e:
                    logger.error(f"Error checking/processing command note {fp}: {e}")

    # ── Live Dashboard Generator ──────────────────────────────────

    async def update_dashboard(self):
        """Render and write Dashboard.md in the Obsidian vault."""
        if not self.vault_path or not os.path.exists(self.vault_path):
            return

        dashboard_path = os.path.join(self.vault_path, "Dashboard.md")

        # Gather system metrics
        stats = await self.embedding_service.get_stats()
        total_chunks = stats.get("total_chunks", 0)
        ollama_status = await self.llm_service.health_check()
        active_llm = ollama_status.get("chat_model", settings.ollama_chat_model)

        # Count files in IEEE Reports and Generated Papers
        ieee_dir = os.path.join(self.vault_path, "IEEE Reports")
        gen_dir = os.path.join(self.vault_path, "Generated Papers")
        cmd_dir = os.path.join(self.vault_path, "Commands")

        ieee_count = len(os.listdir(ieee_dir)) if os.path.exists(ieee_dir) else 0
        gen_count = len(os.listdir(gen_dir)) if os.path.exists(gen_dir) else 0
        cmd_count = len(os.listdir(cmd_dir)) if os.path.exists(cmd_dir) else 0

        # Build list of recent generated papers
        recent_papers_str = ""
        if os.path.exists(gen_dir):
            papers = sorted(os.listdir(gen_dir), reverse=True)[:5]
            if papers:
                for p in papers:
                    recent_papers_str += f"- [[Generated Papers/{p}]]\n"
            else:
                recent_papers_str = "_No research papers generated yet. Create a command note or use the plugin ribbon icon._\n"
        else:
            recent_papers_str = "_No papers folder found._\n"

        dashboard_md = f"""---
title: ARIA Research Control Panel
updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags:
  - aria/dashboard
---

# 🧠 ARIA - AI Research & Intelligence Assistant

> [!ABSTRACT] Obsidian Control Plane
> **Backend Status:** 🟢 Online  
> **Active Local LLM:** `{active_llm}`  
> **ChromaDB Vectors:** `{total_chunks}` indexed chunks  
> **Last Sync:** {datetime.now().strftime('%b %d, %Y %I:%M %p')}  

---

## 📊 System Overview

| Metric | Status / Value | Description |
| :--- | :--- | :--- |
| **IEEE Source Papers** | `{ieee_count}` reports | Place raw IEEE PDFs or notes in `IEEE Reports/` |
| **Active Commands** | `{cmd_count}` notes | Create task notes in `Commands/` |
| **Generated Papers** | `{gen_count}` papers | Synthesized IEEE Transactions papers in `Generated Papers/` |
| **Vector Store Status** | `{total_chunks}` chunks | Semantic search & RAG index status |

---

## 📄 Recent Generated IEEE Research Papers

{recent_papers_str}

---

## 🚀 Quick Command Guide for Obsidian

### Method 1: Use the ARIA Assistant Plugin (Recommended)
- Click the **ARIA Ribbon Icon** on the left bar OR press `Ctrl + P` and search **`ARIA: Generate IEEE Research Paper`**.
- Fill in topic, journal target, and requirements, then click **Generate Paper**.

### Method 2: Create a Command Note in `Commands/`
Create a markdown note inside `Commands/` folder with the following frontmatter:

```yaml
---
aria_action: generate_paper
topic: "Distributed Federated Learning in 6G IoT Networks"
target_journal: "IEEE Transactions on Mobile Computing"
requirements: "Focus on convergence proofs and privacy constraints."
status: pending
---
```
*ARIA backend will automatically pick up `status: pending`, generate the IEEE paper, and update the note with a link to the output paper!*

---

## 📁 Vault Folders
- `IEEE Reports/` → Drop your reference IEEE Transaction PDFs & documents here for local AI study.
- `Commands/` → Place command notes to trigger paper generation.
- `Generated Papers/` → Access your generated IEEE Transactions research papers.
- `Templates/` → Ready-to-use task templates.
"""
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_md)

        logger.info("Updated Obsidian Dashboard.md")

    # ── Sync Operations ───────────────────────────────────────────

    async def sync(self) -> dict:
        """Run full vault sync, command execution, and dashboard update."""
        if self.status.is_syncing:
            return {"status": "already_syncing"}

        self.status.is_syncing = True
        self.status.errors = []
        results = {"new": 0, "modified": 0, "deleted": 0, "errors": []}

        try:
            changes = await self.detect_changes()

            # Process new/modified files for auto-ingestion
            for f in changes["new"]:
                try:
                    await self._ingest_file(f)
                    if self._on_file_changed:
                        await self._on_file_changed("create", f)
                    results["new"] += 1
                except Exception as e:
                    err = f"Error processing new file {f.name}: {e}"
                    results["errors"].append(err)
                    self.status.errors.append(err)

            for f in changes["modified"]:
                try:
                    await self._ingest_file(f)
                    if self._on_file_changed:
                        await self._on_file_changed("modify", f)
                    results["modified"] += 1
                except Exception as e:
                    err = f"Error processing modified file {f.name}: {e}"
                    results["errors"].append(err)

            results["deleted"] = len(changes["deleted"])
            self.status.last_sync = datetime.now()
            self.status.synced_files = results["new"] + results["modified"]

            # Process pending generation commands
            await self.process_pending_commands()

            # Refresh live Dashboard.md
            await self.update_dashboard()

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            results["errors"].append(str(e))
        finally:
            self.status.is_syncing = False

        return results

    async def start_watching(self):
        """Start periodic vault watching."""
        if self._watching:
            return

        self._watching = True
        logger.info(f"Started watching vault: {self.vault_path}")

        async def watch_loop():
            while self._watching:
                try:
                    await self.sync()
                except Exception as e:
                    logger.error(f"Watch sync error: {e}")
                await asyncio.sleep(self.sync_interval)

        self._watch_task = asyncio.create_task(watch_loop())

    async def stop_watching(self):
        """Stop periodic vault watching."""
        self._watching = False
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
        logger.info("Stopped watching vault")

    def get_status(self) -> dict:
        """Get current sync status."""
        return {
            "is_syncing": self.status.is_syncing,
            "last_sync": self.status.last_sync.isoformat() if self.status.last_sync else None,
            "vault_path": self.status.vault_path,
            "total_files": self.status.total_files,
            "synced_files": self.status.synced_files,
            "pending_files": self.status.pending_files,
            "indexed_documents": self.status.indexed_documents,
            "errors": self.status.errors[-5:],
            "watching": self._watching,
        }

    def get_stats(self) -> dict:
        """Get vault statistics."""
        return {
            "vault_path": self.vault_path,
            "total_files": self.status.total_files,
            "cached_hashes": len(self._file_hashes),
            "last_sync": self.status.last_sync.isoformat() if self.status.last_sync else None,
        }

    # ── Helpers ────────────────────────────────────────────────────

    def _quick_hash(self, file_path: str) -> str:
        """Quick hash for change detection (first 8KB + file size)."""
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            h.update(f.read(8192))
        h.update(str(os.path.getsize(file_path)).encode())
        return h.hexdigest()

    def _extract_obsidian_meta(self, file_path: str) -> tuple[list[str], list[str]]:
        """Extract tags and wiki-links from an Obsidian markdown file."""
        tags = []
        links = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            tags = re.findall(r'(?<!\S)#([a-zA-Z0-9_/-]+)', content)
            links = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]', content)
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")

        return tags, links
