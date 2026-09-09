# NextOffer

A mobile-friendly chat assistant that will maintain your job application tracker in Google Sheets.

## Milestone 1 — local foundation

- Next.js chat and settings UI, with explicit preview behavior.
- FastAPI health endpoint.
- No authentication, LLM calls, email access, automatic scans, or Sheets writes yet.

## Run the frontend

Use Node.js 24 LTS (recommended). Node 23 can emit dependency engine warnings.

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Run the backend (another terminal)

Requires Python 3.11 or newer.

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
uvicorn app.main:app --reload --port 8000
```

Health check: http://localhost:8000/health. API documentation: http://localhost:8000/docs.
The preview frontend does not call the backend yet.

## Verify

```sh
cd frontend
npm run lint
npm run build
```

## Next milestones

1. Supabase sign-in and per-user access controls.
2. Google OAuth and spreadsheet selection.
3. Validated agent extraction and application matching.
4. Scheduled email scans, duplicate prevention, Sheets updates and review in chat.
5. Railway deployment and multi-user validation.

Never commit credentials. Root `.env.example` documents configuration as integrations are introduced.
