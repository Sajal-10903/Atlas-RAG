# Atlas RAG

Atlas is a production-oriented Retrieval Augmented Generation and agent workflow service. It accepts PDF, DOCX, text, Markdown, HTML, and CSV documents; extracts/chunks content; indexes semantic vectors in Qdrant and lexical content in PostgreSQL; and generates grounded answers with inline source citations.

The built-in web workbench adds drag-and-drop uploads, automatic ingestion-status polling, document-scoped hybrid search, expandable source evidence, and an agent-report workspace. It is served directly by FastAPI at the root URL, so there is no separate frontend build step.

## Architecture

```text
Upload -> extractor -> chunker -> embeddings -> Qdrant (semantic)
                                    -> PostgreSQL (documents, chunks, FTS)
Question -> hybrid retrieval (RRF) -> citation-aware LLM -> answer API/UI
Report request -> research agent -> retrieval + analysis -> structured report
```

## Quick start

1. Copy `.env.example` to `.env` and provide `OPENAI_API_KEY` (or an OpenAI-compatible endpoint).
2. Run `docker compose up --build`.
3. Open http://localhost:8000 for the UI, and http://localhost:8000/docs for the API.

After changing source files while using Docker, refresh the running stack with `docker compose up --build --force-recreate`.

`EMBEDDING_PROVIDER=openai` is the production default. For an offline ingestion-only smoke test, set `EMBEDDING_PROVIDER=local`; it uses deterministic hash vectors and is deliberately not a replacement for semantic embeddings. Chat and report generation still require a configured LLM provider.

For a non-Docker local run, start PostgreSQL and Qdrant, run `alembic upgrade head`, then run `uvicorn app.main:app --reload`.

## API

- `POST /api/v1/documents` multipart upload; returns a document id and starts ingestion.
- `GET /api/v1/documents` returns the latest indexed documents for the workbench.
- `GET /api/v1/documents/{id}` ingestion status and metadata.
- `POST /api/v1/chat` `{question, document_ids?, top_k?}` returns answer, citations, and retrieval trace.
- `POST /api/v1/reports` `{topic, document_ids?, format?}` runs the research/report agent.
- `GET /health` dependency-free liveness endpoint.

## Production notes

The service separates durable metadata (PostgreSQL) from vector search (Qdrant), uses deterministic reciprocal-rank fusion, persists source offsets, constrains model output to supplied context, and exposes retrieval traces for evaluation. For deployment, add OAuth/RBAC, a task queue (Celery/Temporal), object storage, antivirus scanning, rate limits, migrations, structured logging/OTel, and secret management.

Run lightweight unit tests with `pytest`. Run retrieval evaluation after loading a corpus with `python scripts/evaluate.py --dataset tests/fixtures/eval.json`.
