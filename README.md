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

## Quick Start (1-Click Install)

We provide interactive setup scripts that will automatically configure your environment and start the application via Docker.

### For Windows Users:
1. Double-click the `setup.bat` file in the project directory, OR run it from your terminal:
   ```cmd
   setup.bat
   ```
2. When prompted, paste the full path to your Obsidian vault (e.g., `C:\Users\Name\Documents\MyVault`).

### For Mac / Linux Users:
1. Open your terminal and run the setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
2. When prompted, paste the full path to your Obsidian vault (e.g., `/Users/Name/Documents/MyVault`).

The script will automatically build the backend, download ChromaDB, and connect it to your Obsidian vault!

### Setup Ollama Models
ARIA relies on local Ollama models. Ensure Ollama is running on your machine and download the necessary models:
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
