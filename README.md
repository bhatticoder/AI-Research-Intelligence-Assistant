# ARIA - AI Research & Intelligence Assistant

ARIA is a full-stack, privacy-first AI system designed for researchers, students, journalists, and professionals to manage, search, and extract insights from their personal knowledge bases and documents. It connects seamlessly to Obsidian, uses local LLMs for privacy, and builds a powerful RAG (Retrieval-Augmented Generation) pipeline over your data.

## Features

- **Privacy First**: Uses local LLMs via Ollama. No data leaves your machine unless you configure external APIs.
- **Obsidian Integration**: Connects to your Obsidian vault to synchronize and search your markdown notes.
- **Document Intelligence**: Upload PDFs, DOCX, TXT, and HTML. Uses PyMuPDF and PaddleOCR to extract text and tables, even from scanned documents.
- **Advanced RAG Chat**: Chat with your documents using semantic search (ChromaDB). Answers include source citations.
- **Knowledge Graph**: Automatically extracts entities (People, Organizations, Concepts, etc.) and visualizes their connections across your documents.
- **Automated Reports**: Generate comprehensive research reports using your knowledge base and customizable templates (Markdown/PDF export).
- **News & Papers Feed**: Integrated search for arXiv papers and news articles to stay up-to-date with your field.

## Tech Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4, custom UI components
- **State Management**: Zustand, TanStack Query
- **Real-time**: WebSockets for streaming chat

### Backend
- **Framework**: FastAPI (Python 3)
- **Database**: PostgreSQL (SQLAlchemy async)
- **Vector Store**: ChromaDB
- **Caching/Queues**: Redis
- **File Storage**: MinIO (S3 compatible)
- **AI/ML**: Ollama, SentenceTransformers, PaddleOCR, PyMuPDF, NetworkX

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Docker Compose
- [Node.js](https://nodejs.org/) (v20+)
- [Python](https://www.python.org/) 3.10+
- [Ollama](https://ollama.com/) (installed locally for LLMs)

## Quick Start

### 1. Start Infrastructure

Start the backing services (PostgreSQL, Redis, ChromaDB, MinIO) using Docker:

```bash
docker compose up -d
```

### 2. Configure Environment

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```
Ensure the configuration matches your setup.

### 3. Backend Setup

Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8080
```

### 4. Frontend Setup

In a new terminal window, navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Managing AI Models

By default, ARIA uses Ollama for local LLMs. You will need to pull a model for chat and embeddings before using the chat functionality:

```bash
# Pull a chat model
ollama run mistral
# Pull an embedding model
ollama pull nomic-embed-text
```

You can also manage models from the Settings page in the ARIA dashboard.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License. See `LICENSE` for more information.
