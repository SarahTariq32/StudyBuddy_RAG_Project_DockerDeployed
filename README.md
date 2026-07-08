# Study Buddy RAG

A full-stack PDF question-answering application built with FastAPI, React, ChromaDB, and optional LangChain runtime integration. Upload PDFs, index them into a vector store, ask grounded questions, and inspect request-level AI observability through the built-in operations dashboard.

## What This Project Does

- Uploads and indexes PDF files.
- Stores document metadata and chat history in SQLite.
- Stores embeddings in ChromaDB.
- Answers questions using Retrieval-Augmented Generation (RAG).
- Supports multi-turn follow-up questions using lightweight conversational query anchoring.
- Exposes an operations dashboard for traces, latency, retrieval outcomes, and request health.
- Runs cleanly in Docker behind nginx with a single public entrypoint.

## Core Features

### Document Q&A

- PDF upload and deletion.
- Duplicate protection via content hashing.
- Background indexing flow.
- Parent/child chunking strategy for retrieval quality.
- Source-aware answers backed by retrieved document chunks.

### Retrieval + Generation

- Semantic retrieval with ChromaDB.
- Query rewrite and optional multi-query expansion.
- Relevance filtering.
- Legacy RAG path and optional LangChain path.
- Multiple LLM providers:
  - Groq
  - Google Gemini
  - OpenRouter

### Conversation Handling

- Session-based chat history.
- Follow-up questions like “what are its advantages?” and “how to learn it?” are anchored to the last relevant user topic.
- Follow-up rewriting is conservative to reduce topic leakage.

### AI Observability Dashboard

- Dashboard page at `/ops`.
- Recent request list with subtle visual status highlighting:
  - green for successful requests
  - yellow for slow requests over 10 seconds
  - red for failed requests
- Trace viewer with per-stage timing and execution state.
- LangSmith-backed observability with local fast cache and graceful fallback behavior.

## Observability Model

The dashboard separates pipeline execution health from retrieval outcome.

Each pipeline stage has its own execution state:

- `Completed`
- `Failed`
- `Skipped`

Stages tracked:

- Query Rewrite
- Embedding
- Retrieval
- LLM Generation
- Final Answer

Each stage may also expose:

- latency
- outcome
- failure reason

Examples:

- Retrieval `Completed` + `no_relevant_context` means retrieval ran correctly but found nothing useful.
- Retrieval `Failed` means retrieval could not be performed because of an actual execution problem.
- A request with `0` chunks can still be successful if the system correctly reports that no relevant context exists.

Overall request status is derived from critical stage execution failures, not from chunk count alone.

Additional request-level metadata surfaced in traces:

- `answer_outcome`
- `retrieval_outcome`
- `response_source`
- `fallback_mode`
- `fallback_reason`
- `request_failure_reason`

## Architecture

```text
React + Vite frontend
        |
        |  same-origin /api requests
        v
nginx reverse proxy
   |               |
   |               |
   v               v
frontend        FastAPI backend
                    |
         -------------------------
         |           |           |
         v           v           v
     SQLite      ChromaDB    LLM providers
   (history,      (vectors)   (Groq/Gemini/
   documents)                 OpenRouter)
```

## Tech Stack

### Backend

- FastAPI `0.138.0`
- Uvicorn `0.49.0`
- Pydantic `2.13.4`
- Python Multipart for file uploads
- pypdf `6.14.2`
- ChromaDB `0.5.11`
- NumPy `1.26.4`
- LangChain Core `0.3.17`
- LangChain Chroma `0.1.4`
- LangChain OpenAI `0.2.8`
- LangChain Google GenAI `2.0.4`
- LangChain Groq `0.2.1`
- LangSmith `0.1.147`
- Google GenAI `2.9.0`
- Groq Python SDK
- OpenAI SDK `1.95.1`
- SQLite for app data

### Frontend

- React `18.3.1`
- React DOM `18.3.1`
- React Router DOM `6.30.1`
- Vite `6.3.5`
- `@vitejs/plugin-react`
- Inline component-scoped styling

### Infrastructure

- Docker Compose
- nginx `1.27-alpine`
- ChromaDB container
- Persistent Docker volumes for app data and vector storage

## Project Structure

```text
RAG project/
├── README.md
├── docker-compose.yml
├── docker-compose.override.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── schemas.py
│   │   ├── history/
│   │   ├── llm/
│   │   ├── ops/
│   │   ├── rag/
│   │   └── routes/
│   └── storage/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api/
│       ├── components/
│       └── pages/
└── nginx/
    └── nginx.conf
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop if you want the containerized stack

### Backend

```powershell
Set-Location "backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
Set-Location "frontend"
npm install
npm run dev
```

Frontend dev URL:

- `http://localhost:5173`

Backend dev URL:

- `http://127.0.0.1:8000`

## Docker Quick Start

The Docker setup is the recommended run path for this project.

### Run

```powershell
Set-Location "c:\Users\sarah\OneDrive\Desktop\RAG project"
docker compose up -d --build
```

### Open the app

Recommended URLs:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

### Important Docker Notes

- nginx is the public entrypoint.
- Frontend is served through nginx.
- API requests are reverse-proxied through `/api`.
- Docker ports are explicitly bound to IPv4 loopback:
  - `127.0.0.1:80:80`
  - `127.0.0.1:5173:80`

This was done to avoid Windows localhost/IPv6 forwarding issues that caused Docker Desktop port links to fail on some machines.

### Stop

```powershell
docker compose down
```

## Docker Services

### `db`

- ChromaDB service
- stores embeddings in a named Docker volume

### `backend`

- FastAPI app
- talks to ChromaDB over the Docker network
- stores PDFs and SQLite DB in persistent volume `/data`

### `frontend`

- React app built with Vite
- served from a lightweight static container on port `4173`

### `nginx`

- single public ingress
- proxies:
  - `/` -> frontend
  - `/api/` -> backend

## Main Endpoints

### App API

- `POST /ask`
- `POST /documents`
- `GET /documents`
- `DELETE /documents/{id}`
- `GET /health`

### Ops API

- `GET /ops/dashboard?hours=24&limit=100`
- `GET /ops/traces?hours=24&limit=30`
- `GET /ops/traces/{trace_id}`

Frontend operations page:

- `/ops`

## Environment Variables

### LLM Provider

```env
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash

OPENROUTER_API_KEY=
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free
```

### Storage

```env
PDF_STORAGE_PATH=/data/pdfs
DB_PATH=/data/app.db
CHROMA_COLLECTION=documents
CHROMA_HOST=db
CHROMA_PORT=8000
```

### Retrieval / Chunking

```env
EMBEDDING_BATCH_SIZE=48
PARENT_CHUNK_SIZE=1500
CHILD_CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_CHILD_CHUNKS=450
MAX_PDF_PAGES=40
NUM_MULTI_QUERIES=2
DISTANCE_THRESHOLD=1.2
RAG_TOP_K=8
```

### LangChain Runtime

```env
USE_LANGCHAIN=true
RAG_LLM_PROVIDER=groq
RAG_EMBEDDINGS_PROVIDER=legacy
```

### LangSmith Observability

```env
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=studybuddy-rag
```

## How Request Handling Works

### Document-grounded answer path

1. Read session history.
2. Rewrite follow-up question if needed.
3. Embed query and retrieve relevant chunks.
4. If relevant context exists, generate grounded answer.
5. Save chat history.
6. Emit request trace for dashboard and LangSmith.

### No-relevant-context path

1. Retrieval completes successfully.
2. No relevant chunks are found.
3. Request remains successful.
4. Trace records retrieval outcome as `no_relevant_context`.
5. Final response source may be `llm_only_response` depending on flow.

### Failure path

If a critical stage fails due to execution error, the trace captures:

- failed stage
- failure reason
- degraded fallback metadata if applicable
- overall request failure if not successfully recovered

## Troubleshooting

### Docker app opens but localhost link fails

Use:

- `http://localhost:5173`
- or `http://127.0.0.1:5173`

The current Compose setup binds nginx to IPv4 loopback to avoid host IPv6 issues.

### Ops dashboard shows missing traces or empty metrics

- Ensure `LANGSMITH_API_KEY` is set if you want remote LangSmith-backed trace sync.
- The backend still uses local trace cache for fast dashboard freshness.
- Temporary LangSmith rate limits should not block request handling.

### A request has 0 retrieved chunks

This is not automatically a failure.

Interpretation depends on stage metadata:

- Retrieval `Completed` + `no_relevant_context` -> normal no-evidence case
- Retrieval `Failed` -> actual pipeline problem

### Recent Requests colors

- Green: request successful
- Yellow: successful but slow (`>10s` overall latency)
- Red: failed request

## Current State Summary

This README reflects the code currently present in the repository, including:

- Docker-first run path behind nginx
- stable localhost behavior on Windows
- follow-up question handling improvements
- fast ops dashboard with local trace cache
- richer observability semantics aligned with industry-grade tracing workflows
```env
LLM_PROVIDER=groq          # Switch to free fast provider
# Or add exponential backoff (already in code, but monitor)
```

### LangChain appears disabled in logs
**Cause:** `USE_LANGCHAIN` is false/missing in active environment, or backend not restarted.  
**Fix:**
```env
USE_LANGCHAIN=true
RAG_LLM_PROVIDER=groq
RAG_EMBEDDINGS_PROVIDER=legacy
```
Then restart backend/container and confirm startup log shows `LangChain enabled`.

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
