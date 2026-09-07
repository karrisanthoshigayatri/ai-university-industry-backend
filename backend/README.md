# Smart AI Problem-to-Impact Backend

This directory contains the initial FastAPI backend foundation. Business modules, authentication, AI integrations, and database models will be added in later phases.

## Requirements

- Python 3.12 or newer
- PostgreSQL for database-backed features

## Setup on Windows

Open PowerShell in the `backend` directory and create a virtual environment:

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and replace the placeholder values. `DATABASE_URL` should use a PostgreSQL SQLAlchemy URL, for example:

```text
postgresql+psycopg://<username>:<password>@<host>:<port>/<database>
```

Use a long, randomly generated value for `SECRET_KEY`. Do not commit `.env` or place real secrets in source control.

## Run the server

```powershell
python -m uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Swagger documentation

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in a browser.

## Health check

With the server running, use PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "message": "Backend is running"
}
```

## Alembic

Alembic is configured for future migrations and currently has no revisions or database tables managed by this project. Migration commands should be run from this directory after models are introduced.

## Database connectivity check

The database check is optional and does not run during application startup. After configuring PostgreSQL and `.env`, run:

```powershell
python -c "from app.db.health import check_database_connection; print(check_database_connection())"
```

It prints `True` when the configured PostgreSQL database accepts a connection and `False` otherwise.