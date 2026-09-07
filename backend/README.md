# Smart AI Problem-to-Impact — Backend

FastAPI backend for the AI-driven university–industry collaboration platform. Steps 1–28 implemented.

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # fill in DATABASE_URL and SECRET_KEY
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger UI: http://127.0.0.1:8000/docs

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | JWT signing key |
| `ALGORITHM` | | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `30` | Token lifetime |
| `AI_ENABLED` | | `false` | `true` = real Qwen2.5 via Ollama |
| `EMBEDDING_ENABLED` | | `false` | `true` = real BGE embeddings |

Both AI features default to **false** — the backend runs fully without GPU or Ollama.

## Commands

```bash
# Apply migrations
python -m alembic upgrade head

# Run demo seed (idempotent)
python -m app.services.demo_seed

# Run tests
python -m pytest tests/ -v

# Run tests (summary only)
python -m pytest tests/ --tb=no -q
```

## Demo Seed

```bash
python -m app.services.demo_seed
```

Creates: Karnataka Government + officer · 3 HEIs (NITK, IISc, UAS) · Faculty + resources · 3 Partners (AgroTech/Industry, SmartFarm/Startup, Rural Dev/CSR) · Demo problem: *"Village requires smart irrigation monitoring"*

Demo login: `officer@demo.gov.in` / `Demo@1234`

## Architecture

```
Problem Submission → Similarity → Government Validation → AI Analysis
  → HEI Matching → Faculty/Resource Matching → Project Creation
  → Capability Gap → Partner Matching → Collaboration
  → Project Partner → Milestones → Outputs → Impact → Audit Log
```

## Test Results

155 passed · 2 skipped (app_user FK isolation) · 0 failed
