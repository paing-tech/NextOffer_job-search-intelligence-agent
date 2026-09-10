# NextOffer — Job Search Intelligence Agent

An LLM agent that keeps your job search organized:

- **Job-link analyzer** — paste a LinkedIn / JobStreet / careers-page link (or the
  description text) and get a normalized summary: company, title, location, and
  requirements reduced to tokens like `Python`, `FastAPI`, `2+ years backend experience`,
  `Bachelor's in CS or equivalent`.
- **Gmail tracker** *(milestones 1–2)* — scans job-related mail, classifies each update
  (applied / assessment / interview / rejection / offer / status), extracts company,
  title, dates and next actions, and keeps a Google Sheet in sync.

It demonstrates: an agent loop with tool/function calling, structured output, information
extraction, classification, conversation state/context management, and API integrations.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), Auth.js / NextAuth v5 (email + password) |
| Backend | FastAPI, hand-written agent loop |
| LLM | GPT-5.6 Terra via **Microsoft Foundry** (Azure AI Foundry), OpenAI-compatible SDK |
| Database | **Azure Database for PostgreSQL** (async SQLAlchemy + Alembic) |
| Integrations | Google OAuth → Gmail + Sheets *(milestone 1)* |

The browser only ever calls the Next.js app. `frontend/src/app/api/backend/[...path]`
reads the NextAuth session, mints a short-lived HS256 token (shared `AUTH_SECRET`), and
proxies to FastAPI, which verifies it per request.

## Run the backend

Requires Python 3.11+ and a reachable PostgreSQL database.

```sh
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock.txt
cp .env.example .env          # fill DATABASE_URL, AUTH_SECRET, FOUNDRY_*
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health check: http://localhost:8000/health · API docs: http://localhost:8000/docs

Run the tests (SQLite, no external services):

```sh
pytest
```

## Run the frontend (another terminal)

Use Node.js 24 LTS.

```sh
cd frontend
npm install
cp .env.example .env.local    # AUTH_SECRET must match the backend, set BACKEND_URL
npm run dev
```

Open http://localhost:3000 — create an account, then paste a job link in Chat.

## Verify

```sh
cd frontend && npm run lint && npm run build
cd ../backend && pytest
```

## Milestones

0. **Scaffold + job-link analyzer** — auth, agent loop, structured extraction, tracking. ✅
1. Google OAuth, Gmail + Sheets connection, spreadsheet selection.
2. Email-scan pipeline: classify + extract updates, match applications, sync the Sheet.
3. Scheduled scans (Azure Container Apps job) + deployment.

## Configuration

`backend/.env` and `frontend/.env.local` are documented in the matching `.env.example`
files. `AUTH_SECRET` must be identical in both. Never commit real secrets.
