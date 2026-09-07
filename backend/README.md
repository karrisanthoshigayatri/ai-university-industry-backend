# Smart AI Problem-to-Impact Backend

FastAPI backend implementing 25 steps of the AI-driven Problem-to-Impact platform for university–industry collaboration.

## Architecture Overview

```
Problem Submission
    → Similarity / Duplicate Detection (BGE embeddings, mock-safe)
    → Government Validation
    → AI Analysis (Qwen2.5, mock-safe)
    → HEI Matching (deterministic scoring)
    → Faculty / Resource Matching
    → Project Creation
    → Capability Gap Analysis
    → Partner Matching
    → Collaboration → Project Partner
    → Milestones → Outputs
    → Impact Records → Beneficiaries
    → Notifications → Audit Log
```

## Tech Stack

- **Framework:** FastAPI 0.115
- **ORM:** SQLAlchemy 2.x
- **Database:** PostgreSQL (Supabase)
- **Migrations:** Alembic
- **Auth:** JWT (python-jose), argon2 (pwdlib)
- **AI:** Qwen2.5 (optional, `ai_enabled=false` for mock)
- **Embeddings:** BGE (optional, `embedding_enabled=false` for mock)

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (or Supabase project)

### 2. Clone and install

```bash
git clone https://github.com/karrisanthoshigayatri/ai-university-industry-backend.git
cd ai-university-industry-backend/backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 3. Environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret (long random string) |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default: `30`) |
| `AI_ENABLED` | Set `true` to use real Qwen2.5 (default: `false`) |
| `EMBEDDING_ENABLED` | Set `true` to use real BGE embeddings (default: `false`) |

### 4. Database / Supabase setup

Create a PostgreSQL database or Supabase project. Set `DATABASE_URL` accordingly.

```bash
python -m alembic upgrade head
```

### 5. Run the server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger UI: http://127.0.0.1:8000/docs

## Seed Commands

### Capability taxonomy (auto-runs at startup)

The capability taxonomy seed runs automatically when the app starts. It is idempotent.

### Demo data (manual, run once)

```bash
python -m app.services.demo_seed
```

Creates:
- Government organization + officer (`officer@demo.gov.in` / `Demo@1234`)
- 3 HEIs (NITK, IISc, UAS) with faculty, resources, capabilities
- 3 partners (Industry, Startup, CSR) with capabilities and offerings
- Demo problem: *"Village requires smart irrigation monitoring"*

## Migration Commands

```bash
# Apply all migrations
python -m alembic upgrade head

# Check current revision
python -m alembic current

# See migration history
python -m alembic history
```

## Test Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_integration.py -v

# Run with summary only
python -m pytest tests/ --tb=no -q
```

## API Documentation

Full Swagger UI available at: http://127.0.0.1:8000/docs

### Key endpoint groups

| Tag | Base Path | Description |
|---|---|---|
| auth | `/api/auth` | Register, login, JWT |
| organizations | `/api/organizations` | Org management |
| problems | `/api/problems` | Problem CRUD + evidence + similarity |
| hei | `/api/heis` | HEI profiles + capabilities + faculty + resources |
| partners | `/api/partners` | Partner registry + capabilities + offerings |
| matching | `/api/matching/...` | HEI, Faculty, Resource, Partner matching |
| projects | `/api/projects` | Project lifecycle management |
| capability-gaps | `/api/projects/{id}/capability-gaps` | Gap analysis |
| collaboration | `/api/projects/{id}/collaboration-requests` | Collaboration |
| milestones-outputs | `/api/projects/{id}/milestones` | Milestones + outputs |
| impact-notifications-audit | `/api/projects/{id}/impact` | Impact, notifications, audit |

## AI / Embedding Configuration

Both AI features are **disabled by default** — the backend starts and operates fully without any local AI runtime:

- `AI_ENABLED=false` → Deterministic mock output from Qwen2.5 analysis
- `EMBEDDING_ENABLED=false` → Mock embeddings for similarity detection

To enable with local Ollama:
```env
AI_ENABLED=true
AI_PROVIDER=local
AI_BASE_URL=http://localhost:11434/v1
QWEN_MODEL=qwen2.5
```

## Security

- JWT tokens expire in 30 minutes
- Passwords hashed with argon2
- `.env` is gitignored
- Sensitive fields (`password_hash`, `secret_key`, `token`) never appear in audit logs
- CORS enabled for all origins (configure for production)
