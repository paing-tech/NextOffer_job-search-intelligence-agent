# Backend — NextOffer API

FastAPI + async SQLAlchemy. The agent loop is hand-written (no framework).

## Layout

- `app/config.py` — env settings (pydantic-settings). All integration secrets optional at import.
- `app/db/` — `models.py` (ORM), `session.py` (async engine), `migrations/` (Alembic, async env).
- `app/auth/` — `deps.py` verifies the HS256 bearer minted by the Next.js BFF; `passwords.py` bcrypt.
- `app/llm/` — `client.py` is the ONLY provider-specific module (Microsoft Foundry / OpenAI-compatible).
  `schemas.py` Pydantic models for structured output; `extraction.py` extraction calls.
- `app/integrations/jobfetch.py` — best-effort URL fetch + auth-wall heuristic (`needs_paste`).
- `app/services/` — domain logic shared by routers and agent tools (`jobs.py`, `applications.py`).
- `app/agent/` — `loop.py` (turn loop + chat persistence), `tools.py` (specs + dispatch), `prompts.py`.
- `app/routers/` — `auth`, `jobs`, `chat` (SSE), `applications` are live; `google`, `scans` are 501 stubs.

## Conventions

- New model calls go through `app.llm.client.complete()`, never the SDK directly.
- Logic callable from both REST and the agent lives in `app/services/`, not in routers.
- `alembic revision --autogenerate -m "..."` after model changes; the URL comes from `DATABASE_URL`.
- Tests use in-memory SQLite (`Base.metadata.create_all`); migrations are Postgres-only.
