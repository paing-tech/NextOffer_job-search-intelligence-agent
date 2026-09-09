# NextOffer

A mobile-friendly chat assistant that will maintain your job application tracker in Google Sheets.

## Current milestone — Supabase authentication

- Next.js chat and settings UI, with explicit preview behavior.
- FastAPI health endpoint.
- Email/password sign-up, sign-in, sign-out, cookie refresh, and server-verified page access.
- No LLM calls, email access, automatic scans, or Sheets writes yet.
- No application database tables yet; per-user database policies and backend token verification must be added before storing or exposing user data.

## Run the frontend

Use Node.js 24 LTS (recommended). Node 23 can emit dependency engine warnings.

```sh
cd frontend
npm install
cp .env.example .env.local
# Fill in your Supabase URL and publishable key before starting.
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

1. Per-user database access policies and backend token verification.
2. Google OAuth and spreadsheet selection.
3. Validated agent extraction and application matching.
4. Scheduled email scans, duplicate prevention, Sheets updates and review in chat.
5. Railway deployment and multi-user validation.

Never commit credentials. Root `.env.example` documents configuration as integrations are introduced.

## Supabase setup

In Authentication → Providers, enable Email authentication. Keep email confirmation enabled.
In Authentication → URL Configuration, set the local Site URL to `http://localhost:3000` and add `http://localhost:3000/auth/callback` to Redirect URLs. If using `127.0.0.1`, add `http://127.0.0.1:3000/auth/callback` too. Use the same host throughout registration and confirmation. Add your HTTPS production callback when deploying.

The default confirmation email link works with the PKCE callback in `/auth/callback`; open it in the browser where you registered. Expired or cross-browser links show a retry message. Supabase email delivery limits and provider settings apply; configure production email delivery before inviting friends.

Manual auth check:
1. Visit `/` signed out: expect a redirect to `/login`. Repeat with `/settings`.
2. Create an account, confirm your email, and sign in. Your email should appear in Settings.
3. Refresh: you should remain signed in.
4. Sign out from Settings, then revisit `/settings`: expect `/login`.
5. Try an incorrect password: expect a clear error and no session.

Authentication does not authorize Gmail access. The separate Google connection remains disabled. Do not expose secret/service-role keys through `NEXT_PUBLIC_` variables.
