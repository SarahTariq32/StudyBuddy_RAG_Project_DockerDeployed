# Study Buddy — RAG-Powered PDF Q&A

A modern full-stack application that lets you upload PDF documents and ask natural language questions about them. Powered by Retrieval-Augmented Generation (RAG), it uses vector embeddings and semantic search to find relevant content from your PDFs and generates intelligent answers backed by source documents.

**Live Demo:** https://study-buddy-rag-project.vercel.app/

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start (Local)](#quick-start-local)
- [Quick Start (Docker)](#quick-start-docker)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [API Endpoints](#api-endpoints)
- [Configuration & Tuning](#configuration--tuning)
- [Troubleshooting](#troubleshooting)

---

## Features

✅ **PDF Upload & Management**
- Upload up to 5 PDFs (configurable)
- File size limit: 50 MB (configurable)
- Automatic deduplication by content hash
- Real-time indexing status tracking

✅ **Smart Document Processing**
- Intelligent multi-level chunking (parent + child chunks)
- Metadata preservation (source filename, chunk position)
- Automatic content hash to prevent duplicate uploads

✅ **Multi-Query Semantic Retrieval**
- LLM-powered query rewriting for better recall
- Searches multiple paraphrases of user questions
- Deduplication of retrieved chunks
- Relevance filtering by embedding distance

✅ **Source Attribution**
- Retrieved chunks include source filename
- LLM instructed to cite relevant documents
- Full context passed to answer generation

✅ **Conversation Memory**
- Multi-turn chat history per session
- Automatic pronouns/ambiguity rewriting
- Context-aware follow-up question handling

✅ **Mobile-Responsive UI**
- Desktop: Fixed left sidebar + chat pane
- Mobile: Hamburger menu with slide-out drawer
- Touch-friendly input and controls
- Responsive breakpoint at 900px

✅ **LLM Provider Flexibility**
- Support for Gemini, Groq, and OpenRouter
- Easy runtime provider switching via environment variable
- Graceful error handling with meaningful messages

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│  - ChatPage (router)                                        │
│  - Sidebar (PDF list + upload)                              │
│  - ChatWindow (messages + input)                            │
│  - Mobile-responsive hamburger drawer                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                BACKEND (FastAPI + Python)                   │
│                                                             │
│  Routes:                                                    │
│  ├─ POST /documents (upload PDF)                           │
│  ├─ GET /documents (list all)                              │
│  ├─ DELETE /documents/{id} (delete + cleanup)              │
│  ├─ POST /ask (query with RAG)                             │
│  └─ GET /health (liveness check)                           │
│                                                             │
│  RAG Pipeline:                                              │
│  ├─ PDF Loader (pypdf)                                     │
│  ├─ Chunking (parent + child splits)                       │
│  ├─ Embeddings (ONNX-based, BAAI/bge-small)               │
│  ├─ Vector DB (ChromaDB persistent storage)                │
│  ├─ Query Rewriter (LLM-powered multi-query)               │
│  ├─ Retriever (semantic search + filtering)                │
│  └─ Answer Generator (LLM with context)                    │
│                                                             │
│  Storage:                                                   │
│  ├─ SQLite (document metadata + chat history)              │
│  ├─ ChromaDB (vector embeddings)                           │
│  └─ Local filesystem (PDF files)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.138.0 |
| **Server** | Uvicorn 0.49.0 |
| **PDF Processing** | pypdf 6.14.2 |
| **Vector DB** | ChromaDB 1.5.9 |
| **Embeddings** | ONNX (chromadb.utils.embedding_functions) |
| **LLM Providers** | Google Gemini, Groq, OpenRouter |
| **Database** | SQLite (documents + chat history) |
| **Async** | Threading (background indexing) |

### Frontend
| Component | Technology |
|-----------|-----------|
| **Framework** | React 18.3.1 |
| **Build Tool** | Vite 6.3.5 |
| **Routing** | React Router 6.30.1 |
| **Styling** | Inline CSS (responsive, no external CSS) |
| **API Client** | Native Fetch API |
| **State Management** | React Hooks (useState, useRef, useEffect) |

### Deployment
| Environment | Service |
|-------------|---------|
| **Backend** | Railway / Fly.io (Docker) |
| **Frontend** | Vercel (Next.js-agnostic SPA) |
| **Vector DB** | Persistent volume (Railway) |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone & Setup

```bash
cd "c:\Users\sarah\OneDrive\Desktop\RAG project"
git clone <your-repo-url> .
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set LLM_PROVIDER and corresponding API key
```

### 3. Run Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
✓ Database initialized
✓ LLM provider initialized
```

### 4. Frontend Setup (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Expected output:
```
  VITE v6.3.5  ready in 156 ms

  ➜  Local:   http://localhost:5173/
```

### 5. Test Locally

1. Open http://localhost:5173/
2. Upload a PDF
3. Wait for indexing (watch status in sidebar)
4. Ask a question
5. Verify answer includes source attribution

---

## Quick Start (Docker)

**One-Click Multi-Container Setup** (Backend + Frontend + Data Storage)

### Prerequisites
- Docker Desktop (or Docker Engine + Docker Compose)

### 1. Setup

```bash
cd "c:\Users\sarah\OneDrive\Desktop\RAG project"
cp .env.docker.example .env
# Edit .env and fill in your LLM API key (GROQ_API_KEY, etc.)
```

### 2. Run Everything

```bash
docker-compose up --build
```

Docker will:
- Build backend container from `backend/Dockerfile`
- Build frontend container from `frontend/Dockerfile`
- Create a shared network for inter-service communication
- Create a persistent volume for PDFs, ChromaDB, and SQLite
- Start both services

### 3. Access the App

- **Frontend:** http://localhost:5173 (served through NGINX with `/api` reverse-proxied to the backend)
- **Backend API:** http://localhost:8000
- **Health Check:** `curl http://localhost:8000/health`

### 4. Stop

```bash
docker-compose down
```

**For detailed Docker setup, tuning, and production deployment, see [DOCKER.md](DOCKER.md)**

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions for:
- Backend deployment on Railway with persistent volumes
- Frontend deployment on Vercel
- Environment variable configuration
- CORS setup for production

### Quick Summary

**Backend (Railway):**
```bash
git push  # Railway auto-builds from Dockerfile
# Set env vars: LLM_PROVIDER, GEMINI/GROQ/OPENROUTER_API_KEY, CORS_ORIGINS
# Attach persistent volume at /data for PDFs, ChromaDB, SQLite
```

**Frontend (Vercel):**
```bash
# Connect repo → Vercel auto-detects Vite
# Root Directory: frontend
# Env var: VITE_API_URL=https://your-backend-domain
# Deploy
```

---

## Environment Variables

### Backend (`.env`)

**Required:**
```env
LLM_PROVIDER=groq                    # One of: gemini, groq, openrouter
GROQ_API_KEY=your-key-here           # Or GEMINI_API_KEY / OPENROUTER_API_KEY
```

**Recommended (Production):**
```env
CORS_ORIGINS=https://your-frontend.vercel.app
MAX_FILE_SIZE_MB=50
PDF_STORAGE_PATH=/data/pdfs          # Persistent volume path
CHROMA_PATH=/data/chroma_db
DB_PATH=/data/app.db
```

**Optional (Advanced Tuning):**
```env
EMBEDDING_BATCH_SIZE=48
PARENT_CHUNK_SIZE=1500
CHILD_CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_CHILD_CHUNKS=450
MAX_PDF_PAGES=40
DISTANCE_THRESHOLD=1.2
NUM_MULTI_QUERIES=2
```

See `backend/.env.example` for all options.

### Frontend (Vercel)

```env
VITE_API_URL=https://your-backend-domain
```

(If omitted, falls back to `http://localhost:8000` for local dev)

---

## Project Structure

```
RAG project/
├── README.md                          # This file
├── DEPLOYMENT.md                      # Detailed deployment guide
│
├── backend/
│   ├── DockerFile                     # Container image definition
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment variable template
│   │
│   └── app/
│       ├── main.py                    # FastAPI app entry point
│       ├── config.py                  # Configuration (env vars, defaults)
│       ├── database.py                # SQLite schema + init
│       ├── schemas.py                 # Pydantic models (request/response)
│       │
│       ├── llm/
│       │   ├── base.py                # LLMProvider abstract class
│       │   ├── factory.py             # Provider selector
│       │   ├── gemini_provider.py     # Google Gemini implementation
│       │   ├── groq_provider.py       # Groq API implementation
│       │   └── openrouter_provider.py # OpenRouter implementation
│       │
│       ├── rag/
│       │   ├── loader.py              # PDF text extraction
│       │   ├── chunking.py            # Parent + child chunking
│       │   ├── embeddings.py          # Embedding generation (ONNX)
│       │   ├── vector_store.py        # ChromaDB wrapper
│       │   ├── pipeline.py            # Multi-query retrieval orchestration
│       │   ├── query_rewrite.py       # LLM-powered query rewriting
│       │   └── generator.py           # Answer generation with context
│       │
│       ├── routes/
│       │   ├── document.py            # POST/GET/DELETE /documents
│       │   └── chat.py                # POST /ask endpoint
│       │
│       └── history/
│           └── chat_history.py        # Session history persistence
│
├── frontend/
│   ├── package.json                   # NPM dependencies
│   ├── vite.config.js                 # Vite build config
│   ├── index.html                     # HTML entry point
│   │
│   └── src/
│       ├── main.jsx                   # React DOM mount
│       ├── App.jsx                    # Router setup
│       │
│       ├── pages/
│       │   ├── LandingPage.jsx        # Home / onboarding
│       │   └── ChatPage.jsx           # Main app (with canvas background)
│       │
│       ├── components/
│       │   ├── Sidebar.jsx            # PDF list + upload (responsive drawer on mobile)
│       │   ├── ChatWindow.jsx         # Messages + input box
│       │   ├── InputBox.jsx           # Question input (compact on mobile)
│       │   ├── Message.jsx            # Individual message display
│       │   ├── PDFList.jsx            # List of uploaded PDFs
│       │   ├── PDFItem.jsx            # Single PDF with status + delete
│       │   ├── UploadButton.jsx       # File input + upload logic
│       │   └── NotificationToast.jsx  # Error/success notifications
│       │
│       └── api/
│           ├── chat.js                # /ask API client
│           └── documents.js           # /documents API with fallback logic
│
└── storage/                           # Local (dev) or volume (prod)
    ├── pdfs/                          # Uploaded PDF files
    ├── chroma_db/                     # Vector embeddings
    └── app.db                         # SQLite database
```

---

## How It Works

### RAG Pipeline (Step-by-Step)

#### 1. Upload Phase
```
User uploads PDF
    ↓
File validation (type, size, dedup hash)
    ↓
Save to storage/pdfs/{doc_id}.pdf
    ↓
Create DB record (status='processing')
    ↓
Return immediately (async background start)
    ↓
[Background Thread]
├─ Extract text from PDF (pypdf)
├─ Truncate to MAX_TEXT_CHARS
├─ Create parent chunks (1500 chars, overlap)
├─ Create child chunks from parents (500 chars)
├─ Generate embeddings (ONNX, batched)
├─ Store in ChromaDB with metadata
├─ Update DB status='ready'
└─ Done
```

#### 2. Query Phase
```
User asks: "What is the capital of France?"
    ↓
Check if any PDFs are ready (if not: show "no docs" message)
    ↓
Fetch conversation history 
    ↓
Rewrite question using history context
    → "What is the capital of France?" (if no history)
    → Or clarified if it's a follow-up
    ↓
Generate multi-query rewrites (2 variants)
    → ["What is France's capital?", "Name the French capital"]
    ↓
Embed original + rewrites
    ↓
Search ChromaDB for top-K results per query
    ↓
Merge and deduplicate by parent text
    ↓
Filter by distance threshold (1.2)
    ↓
Return up to 15 unique parent chunks with source
    ↓
If no context found: respond with "Context not enough to answer."
    ↓
Otherwise: format context with [Source: filename.pdf] labels
    ↓
Send to LLM with system prompt (cite sources, only use context)
    ↓
Return answer to user
    ↓
Save Q&A to chat_history table
```

#### 3. Delete Phase
```
User deletes PDF
    ↓
Delete document record from SQLite
    ↓
[Background Thread]
├─ Delete all chunks from ChromaDB where doc_id matches
├─ Delete file from storage/pdfs/
└─ Done
```

### Chunking Strategy

**Why Two Levels?**
- **Parent chunks** (1500 chars): Used in LLM prompt for full context
- **Child chunks** (500 chars): Used for embedding search (more specific)

This allows:
- Dense, specific embeddings for retrieval
- Rich context window for answer generation
- No orphaned chunks

---

## API Endpoints

### Documents Management

**Upload PDF**
```
POST /documents
Content-Type: multipart/form-data

Request:
  file: <binary PDF>

Response (201):
  {
    "id": "uuid-string",
    "filename": "document.pdf",
    "uploaded_at": "2026-06-24T10:30:00+00:00",
    "status": "processing"
  }

Errors:
  400 - Not a PDF / Empty file / Too large
  409 - Duplicate (same content hash)
```

**List PDFs**
```
GET /documents

Response (200):
  [
    {
      "id": "uuid",
      "filename": "study_notes.pdf",
      "uploaded_at": "2026-06-24T10:30:00+00:00",
      "status": "ready"  # or "processing" or "error"
    },
    ...
  ]
```

**Delete PDF**
```
DELETE /documents/{doc_id}

Response (204): No content

Errors:
  404 - PDF not found
```

### Chat / RAG

**Ask Question**
```
POST /ask
Content-Type: application/json

Request:
  {
    "session_id": "user-session-uuid",
    "question": "What is machine learning?"
  }

Response (200):
  {
    "answer": "Machine learning is a subset of AI where..."
  }

Errors:
  422 - Missing session_id or question
  502 - Retrieval or LLM error
```

### Health Check

```
GET /health

Response (200):
  { "status": "ok" }
```

---

## Configuration & Tuning

### Chunking Behavior

Adjust in `.env`:

```env
# Larger parent = more context in LLM prompt (slower embedding)
PARENT_CHUNK_SIZE=1500

# Larger child = fewer embeddings, but less specific search
CHILD_CHUNK_SIZE=500

# Higher overlap = more redundancy, better edge handling
CHUNK_OVERLAP=50
```

**Recommendation for Study Material:**
- `PARENT_CHUNK_SIZE=1500` (good for paragraphs + sections)
- `CHILD_CHUNK_SIZE=500` (specific sentences/concepts)
- `CHUNK_OVERLAP=50` (10% overlap balances redundancy)

### Retrieval Tuning

```env
# How many chunks per query variant to search
TOP_K=8

# How many paraphrases to generate
NUM_MULTI_QUERIES=2   # 0=disable multi-query (faster)

# Max unique parent chunks in final context
MAX_CONTEXT_PARENTS=15

# Embedding distance cutoff (lower=stricter)
DISTANCE_THRESHOLD=1.2
```

**Recommendation:**
- `NUM_MULTI_QUERIES=2` for balanced speed + recall
- `DISTANCE_THRESHOLD=1.2` catches loosely-related content (safer)
- `TOP_K=8` gives good recall without hitting rate limits

### LLM Provider Selection

```env
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

**Options:**

| Provider | Model | Speed | Cost | Quality |
|----------|-------|-------|------|---------|
| **Groq** | Llama 3.3 70B | ⚡ Fastest | Free | Good |
| **Gemini** | 2.0 Flash | ⚡ Fast | $0.075/M in | Excellent |
| **OpenRouter** | Many (Free tiers) | Variable | $0+ | Variable |

---

## Troubleshooting

### "vite: Permission denied" on Vercel deploy
**Cause:** `node_modules` was tracked in git.  
**Fix:**
```bash
git rm -r --cached frontend/node_modules
npm install --package-lock-only
git add frontend/package-lock.json
git commit -m "fix: remove tracked node_modules"
git push
```
Redeploy on Vercel with build cache disabled.

### Data disappears on Railway redeploy
**Cause:** No persistent volume attached.  
**Fix:**
1. Go to Railway → Backend service → Settings → Volumes
2. Add volume with mount path `/data`
3. Set env vars:
   ```env
   PDF_STORAGE_PATH=/data/pdfs
   CHROMA_PATH=/data/chroma_db
   DB_PATH=/data/app.db
   ```
4. Redeploy

### "CORS error" in frontend console
**Cause:** Frontend domain not in backend CORS_ORIGINS.  
**Fix:** Update Railway env var:
```env
CORS_ORIGINS=https://your-vercel-app.vercel.app
```
(Or comma-separated for multiple: `https://app.vercel.app,https://preview-*.vercel.app`)

### Mobile layout broken / hamburger not showing
**Cause:** Browser cache or old build.  
**Fix:**
```bash
cd frontend
npm run build
# Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### Embeddings slow on large PDFs
**Cause:** ONNX CPU embedding on massive document.  
**Fix:**
```env
EMBEDDING_BATCH_SIZE=32    # Reduce to lower memory peak
# Or truncate input
MAX_PDF_PAGES=30           # Limit pages extracted
```

### LLM API rate limit hit
**Cause:** High query volume.  
**Fix:**
```env
LLM_PROVIDER=groq          # Switch to free fast provider
# Or add exponential backoff (already in code, but monitor)
```

---

## Future Enhancements

- [ ] Streaming responses (SSE or WebSocket)
- [ ] User authentication (multi-user sessions)
- [ ] Admin dashboard (analytics, usage stats)
- [ ] PDF annotation (highlight + link to Q&A)
- [ ] Custom embedding model swap (OpenAI, Cohere)
- [ ] Batch import (ZIP of PDFs)
- [ ] Export conversation as PDF
- [ ] Dark mode toggle (currently hardcoded dark)

---

## License

This project is provided as-is for educational and research purposes.

---

## Support

For issues, questions, or feature requests:
1. Check this README and [DEPLOYMENT.md](DEPLOYMENT.md)
2. Review logs from backend: `uvicorn app.main:app --log-level debug`
3. Check frontend console (browser DevTools)
4. Verify environment variables are set correctly

---

**Built with ❤️ for efficient PDF-based learning**
