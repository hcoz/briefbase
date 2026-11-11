# BriefBase

Paste a note, and BriefBase asks an AI model for a short **summary** and **3–5 tags**, then stores them with the note. You can list your notes, filter them by tag, re-summarize and delete them. Every user sees only their own notes.

| | |
|---|---|
| **Live app** | https://briefbase-nu.vercel.app |
| **Backend API** | https://briefbase-production.up.railway.app ([`/docs`](https://briefbase-production.up.railway.app/docs) for Swagger) |
| **Test account** | `demo@briefbase.dev` / `BriefBase.2026`, or register your own on the login screen (any email, password of 8+ characters) |
| **AI provider** | Google Gemini (`gemini-3.6-flash`) |
| **Demo video** | DEMO_VIDEO_URL_HERE |

## Submission checklist
- [x] Repo link: https://github.com/hcoz/briefbase
- [x] Live Vercel URL: https://briefbase-nu.vercel.app
- [x] Backend location: cloud, Railway: https://briefbase-production.up.railway.app (Postgres on Railway too)
- [x] Test account or registration instructions: see the table above
- [x] AI provider used: Google Gemini
- [x] `.env.example` committed: [.env.example](.env.example)
- [x] Migration file committed: [backend/alembic/versions/0001_create_users_and_notes.py](backend/alembic/versions/0001_create_users_and_notes.py)
- [x] `docker compose up` works locally: see [Run locally](#run-locally)
- [ ] Demo video link: DEMO_VIDEO_URL_HERE
- [x] No secrets committed (gitleaks runs as a pre-commit hook; `.env` is git-ignored)

## Tech stack
| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (sync), Alembic, psycopg 3, Python 3.12 |
| Database | PostgreSQL 16 |
| Auth | JWT (HS256, 60 min), passwords hashed with argon2id |
| AI | Google Gemini (`google-genai`, JSON mode with a response schema) |
| Frontend | Next.js (App Router, TypeScript) + TanStack React Query, plain CSS, Node 22 |
| Hosting | Backend (Docker) + Postgres on Railway, frontend on Vercel |
| Quality | pytest against real Postgres, GitHub Actions CI, pre-commit (gitleaks, ruff) |

## Architecture

```
Browser ──► Vercel (Next.js) ──HTTPS + Bearer JWT──► Railway: backend (Docker) ──private network──► Railway: Postgres
                                                                    └──► Google Gemini API
```

The frontend and the backend are on different origins. The browser calls the backend directly, using the URL in `NEXT_PUBLIC_API_URL`, and the backend allows the Vercel origin through `CORS_ORIGINS`. The backend is hosted in the cloud, so no tunnel is needed.

```
backend/app/
  main.py        FastAPI app, CORS, /health
  config.py      all env vars in one place (pydantic-settings); fails fast if required ones are missing
  db.py          engine, session dependency
  models.py      User, Note
  schemas.py     request/response models and validation
  security.py    argon2id hashing, JWT encode/decode, current-user dependency
  ai.py          summarize(): Gemini call, retry, normalization; never raises
  routers/       auth.py, notes.py
backend/alembic/versions/0001_create_users_and_notes.py   the schema
frontend/
  lib/api.ts     fetch wrapper: base URL, Bearer token, error messages, 401 → logout
  lib/auth.ts    token in localStorage
  app/page.tsx   notes page: list, tag filter, logout
  components/    NoteForm (create), NoteList (list, tags, delete, re-summarize)
```

## Design choices and why

- **Sync SQLAlchemy.** FastAPI runs plain `def` endpoints in a thread pool, so async would add complexity here for no gain.
- **Schema only through Alembic.** Tables are created by the migration, never by `create_all` at runtime. On Railway the migration runs as a pre-deploy step, so a failed migration stops the deploy.
- **Tags as a `text[]` column**, not a join table. A note has at most 5 tags and is never queried by tag on its own. A **GIN index** backs the tag filter, which uses `tags @> ARRAY[tag]` because `= ANY(tags)` can't use that index. The list query `WHERE user_id = ? ORDER BY created_at DESC, id DESC` matches a composite index exactly, so Postgres doesn't need a sort step.
- **Ownership scoping.** Every notes query filters by the current user. A note that doesn't exist and a note that belongs to someone else both return **404**, so note ids from other users are never confirmed.
- **AI failure policy: the note is always saved.** `ai.summarize()` never raises. A missing key, network error, quota error or timeout (20 s) is logged and the function returns `None`. If Gemini returns malformed or empty JSON, or fewer than 3 tags, the call is **retried once** before giving up. When AI fails, the note is stored with `summary = null` and no tags, and the UI shows "Summary unavailable" with a **Re-summarize** button, so the user's text is never lost. Re-summarizing an existing note returns **502** on failure and leaves the note unchanged. Tags are normalized (trimmed, lowercased, `#` removed, deduplicated, at most 5). A note can be up to 20,000 characters, and the whole note is sent to the model: the AI input limit is the same 20,000. The system prompt tells the model to treat the note only as text to summarize.
- **React Query cache.** Notes are cached under `["notes", tag]`. Creating, deleting and re-summarizing all call `invalidateQueries({ queryKey: ["notes"] })`. That is a prefix match, so the unfiltered list and every filtered list are refetched without a page reload. Delete is also **optimistic**: the note disappears from every cached list at once, comes back if the request fails, and the lists are refetched either way. Logging out clears the whole cache, so the next user on the same browser never sees the previous user's notes.
- **JWT in localStorage.** The frontend and backend are on different sites, and the API returns the token in the response body. An httpOnly cookie would be safer against XSS, but it needs a same-origin proxy and CSRF handling, which is more than this scope needs. Mitigations: all user and AI text is rendered as plain React text (never `dangerouslySetInnerHTML`), tokens expire after 60 minutes, and the token is cleared on any 401.

## Run locally

### With Docker (recommended)

**Prerequisites:** Docker.

```bash
git clone https://github.com/hcoz/briefbase.git && cd briefbase
cp .env.example .env
#   set JWT_SECRET to the output of: openssl rand -hex 32
#   set GEMINI_API_KEY (free key: https://aistudio.google.com/apikey).
#   Leaving it empty also works: notes are saved without a summary.
docker compose up -d --build
docker compose run --rm backend alembic upgrade head     # create the tables
open http://localhost:3000                                # API docs: http://localhost:8000/docs
```

This starts Postgres, the backend and the frontend. Stop everything with `docker compose down`, and add `-v` to also delete the database volume.

### Backend without Docker (for development)

**Prerequisites:** Docker (for Postgres), Python 3.12.

```bash
cp .env.example .env              # as above
docker compose up -d db

cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://briefbase:briefbase2026@localhost:5432/briefbasedb
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

The `DATABASE_URL` export is needed because `.env` uses host `db`, the Docker service name, which only resolves inside Docker. From your machine the database is on `localhost`.

### Frontend without Docker (for development)

**Prerequisites:** Node 22, and the backend running on port 8000.

```bash
cd frontend
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm ci
npm run dev                       # http://localhost:3000
```

## Environment variables
All of them are listed with placeholders in [.env.example](.env.example).

| Variable | Used by | Notes |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | docker compose | Credentials for the local database |
| `DATABASE_URL` | backend | Required. `postgres://` and `postgresql://` URLs are accepted and rewritten for psycopg |
| `JWT_SECRET` | backend | Required, at least 32 characters. There is no default |
| `JWT_EXPIRE_MINUTES` | backend | Default 60 |
| `GEMINI_API_KEY` | backend | If empty, AI is treated as unavailable and notes are saved without a summary |
| `GEMINI_MODEL` | backend | Default `gemini-3.6-flash` |
| `CORS_ORIGINS` | backend | Comma-separated frontend origins |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL. Inlined at build time |

## API
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | – | Liveness check |
| POST | `/auth/register` | – | `{email, password}` → `201 {access_token, token_type}`. Duplicate email → 409 |
| POST | `/auth/login` | – | `{email, password}` → `{access_token, token_type}`. Wrong credentials → 401 |
| GET | `/auth/me` | Bearer | `{id, email}` |
| GET | `/notes?tag=` | Bearer | The current user's notes, newest first. With `tag`, only notes that have that tag |
| POST | `/notes` | Bearer | `{title?, content}` → `201` note with `summary` and `tags` (`summary: null`, `tags: []` if AI failed) |
| DELETE | `/notes/{id}` | Bearer | `204`. Missing or someone else's note → 404 |
| POST | `/notes/{id}/summarize` | Bearer | Re-runs the AI and returns the updated note. AI failure → 502, note unchanged |

Every request to a protected route that fails authentication (no token, bad signature, expired token, deleted account) gets the same response: `401 {"detail": "Invalid or expired token"}`.

## Tests and CI

The backend tests run against a real Postgres database. The schema comes from the Alembic migration: the session fixture runs a downgrade and then an upgrade, which also proves the migration is reversible. Gemini is never called; the AI module's client is mocked.

```bash
docker compose up -d db
docker compose exec db createdb -U briefbase briefbase_test   # once
cd backend && source .venv/bin/activate
TEST_DATABASE_URL=postgresql://briefbase:briefbase2026@localhost:5432/briefbase_test pytest
```

The database name must end in `_test`, because the tests wipe it. The tests cover:
- **Auth:** register, login and `/auth/me`; duplicate email; missing, garbage, expired, wrong-secret and `alg: none` tokens all return 401; the token payload contains no email.
- **Ownership:** user B can't list, delete or re-summarize user A's notes and gets 404.
- **Notes:** AI result is stored; the note is still saved when AI fails; tag filter; newest-first order; validation.
- **AI module:** malformed JSON or fewer than 3 tags is retried once and then gives up; provider errors return `None`; tags are normalized; long input is truncated.

[CI](.github/workflows/ci.yml) runs on every push and pull request. Backend: Postgres service → `alembic upgrade head` → `alembic check` (models and migration match) → `pytest`. Frontend: `npm run lint` and `npm run build`.

## Deployment

Railway is configured in its dashboard; there is no config file for it in the repo.

### 1. Railway: Postgres + backend
1. New project → **Add PostgreSQL**.
2. **New service → GitHub repo** → this repo. In the service **Settings**:
   - **Root Directory**: `backend` (the Dockerfile there is detected automatically)
   - **Pre-deploy command**: `alembic upgrade head` (migrations run before each new version goes live; a failed migration aborts the deploy)
   - **Healthcheck path**: `/health`
   - **Networking → Generate domain** (Railway routes it to the `$PORT` the container listens on)
3. Service **Variables**:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference variable, private network) |
   | `JWT_SECRET` | output of `openssl rand -hex 32` (a new value, not the local one) |
   | `GEMINI_API_KEY` | your key |
   | `GEMINI_MODEL` | `gemini-3.6-flash` |
   | `CORS_ORIGINS` | `http://localhost:3000` for now; the Vercel URL is added in step 3 |

4. Check: `curl https://<backend>.up.railway.app/health` → `{"status":"ok"}`.

To run migrations from your laptop instead, use the Postgres service's `DATABASE_PUBLIC_URL`:
`cd backend && DATABASE_URL='<public url>' alembic upgrade head`.

### 2. Vercel: frontend
1. **Add New → Project** → import this repo. **Root Directory**: `frontend` (Next.js is detected; Node 22 comes from `engines` in `package.json`).
2. **Environment variable** `NEXT_PUBLIC_API_URL=https://<backend>.up.railway.app` (no trailing slash). It is inlined at build time, so changing it later needs a redeploy. The build fails if it is missing.
3. Deploy.

### 3. Connect them (CORS)
Set `CORS_ORIGINS=https://<app>.vercel.app,http://localhost:3000` on the Railway backend, using the exact production domain from Vercel. Saving it redeploys the backend. Only listed origins are allowed, so Vercel *preview* URLs get CORS errors; use the production URL.

### 4. Smoke test (browser DevTools → Network)
Register → create a note (summary and tags appear) → `OPTIONS` preflight succeeds and `POST /notes` is followed by an automatic `GET /notes` → click a tag (`GET /notes?tag=…`) → delete. There should be no CORS errors in the console.

## Security notes and known limitations
- **Passwords** are hashed with argon2id. Login runs a hash check even for unknown emails, so response time doesn't reveal which emails are registered.
- **Tokens** carry only the user id, `iat` and `exp`. The server accepts HS256 only, which blocks `alg: none` and algorithm-confusion attacks, and it requires all three claims.
- **Secrets** come only from environment variables. The app refuses to start without `DATABASE_URL` or with a `JWT_SECRET` shorter than 32 characters. gitleaks runs as a pre-commit hook.
- **Not built, on purpose (scope):** stateless JWTs can't be revoked, so logout happens on the client and the short expiry limits the risk. There are no refresh tokens and no login rate limiting. The AI call runs inside the create request, which takes a few seconds; a background job queue would be the next step at larger scale.

## Development
- Pre-commit hooks (gitleaks, ruff, hygiene): `brew install pre-commit && pre-commit install`, then `pre-commit run --all-files`.
- New migration (from `backend/`): `alembic revision --autogenerate -m "..."`, review the file by hand, then `alembic upgrade head`. `alembic check` reports drift between the models and the migrations.
