# ARIA - AI Research & Intelligence Assistant

ARIA is a privacy-first AI system designed for researchers, students, journalists, and professionals to manage, search, and extract insights from their personal knowledge bases and documents. It connects seamlessly to Obsidian, uses local LLMs for privacy, and builds a powerful RAG (Retrieval-Augmented Generation) pipeline over your data.

## Features

- **Privacy First**: Uses local LLMs via Ollama. No data leaves your machine unless you configure external APIs.
- **Obsidian Integration**: Connects to your Obsidian vault to synchronize and search your markdown notes.
- **Document Intelligence**: Upload PDFs, DOCX, TXT, and HTML. Uses PyMuPDF and PaddleOCR to extract text and tables, even from scanned documents.
- **Advanced RAG Chat**: Chat with your documents using semantic search (ChromaDB). Answers include source citations.
- **Automated Reports**: Generate comprehensive research reports using your knowledge base and customizable templates (Markdown/PDF export).

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Docker Compose
- [Ollama](https://ollama.com/) (installed locally for LLMs)
- [Obsidian](https://obsidian.md/) (Optional, but highly recommended)

## Quick Start (Docker Deployment - Recommended)

The easiest way to run ARIA and let anyone use it is via Docker Compose. This will spin up the Python backend and ChromaDB vector database.

### 1. Set your Obsidian Vault Path
By default, Docker expects an Obsidian vault to be present. You can export an environment variable before running Docker to set your vault path:

**Windows (PowerShell):**
```powershell
$env:OBSIDIAN_VAULT_PATH="C:\path\to\your\vault"
```
*(If no path is set, it will create a `./vault` folder in the project directory.)*

**Mac/Linux:**
```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/vault"
```

### 2. Start the Application
Run the following command in the root of the project:

```bash
docker-compose up -d --build
```
This will:
- Build the Python backend and install OCR/PDF processing dependencies.
- Start ChromaDB.
- Mount your Obsidian vault into the container.
- Expose the API on `http://localhost:8080`.

### 3. Setup Ollama Models
ARIA relies on local Ollama models. Ensure Ollama is running and download the necessary models:
```bash
ollama run llama3.2
ollama pull nomic-embed-text
```

## Manual Setup (Without Docker)
If you prefer to run it locally without containerizing the backend:
1. Start ChromaDB using `docker-compose up -d chromadb`
2. Run `run_backend.bat` (Windows) to automatically install requirements and start the server.

## License
MIT License.
