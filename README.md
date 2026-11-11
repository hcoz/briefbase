# BriefBase

Paste a note, and BriefBase asks an AI model for a short **summary** and **3–5 tags**, then stores them with the note. You can list your notes, filter them by tag and delete them.

> **Status: work in progress.** Backend (auth, notes, AI) and frontend work locally. Deployment steps are below; live URLs to follow.

## Tech stack
| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (sync), Alembic, psycopg 3, Python 3.12 |
| Database | PostgreSQL 16 |
| Auth | JWT (HS256, 60 min), passwords hashed with argon2id |
| AI | Google Gemini (`google-genai`, JSON mode) |
| Frontend | Next.js (App Router, TypeScript) + TanStack React Query, Node 22 |
| Hosting | Backend (Docker) + Postgres on Railway, frontend on Vercel |

## Run locally

### With Docker (recommended)

**Prerequisites:** Docker.

```bash
cp .env.example .env
#   set JWT_SECRET to the output of: openssl rand -hex 32
#   set GEMINI_API_KEY (leave it empty to run without AI; notes are still saved)
docker compose up -d --build
docker compose run --rm backend alembic upgrade head
open http://localhost:3000        # API: http://localhost:8000/docs
```

### Backend without Docker (for development)

**Prerequisites:** Docker (for Postgres), Python 3.12.

```bash
# 1. Config: as above
cp .env.example .env

# 2. Database
docker compose up -d db

# 3. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://briefbase:briefbase2026@localhost:5432/briefbasedb
alembic upgrade head
uvicorn app.main:app --reload
```

The `DATABASE_URL` export is needed because `.env` uses host `db`, the Docker service name, which only resolves inside Docker. Running the backend from your machine needs `localhost`.

Open **http://localhost:8000/docs** (Swagger UI) to try the API:
1. `POST /auth/register` with an email and a password of 8+ characters. Copy the `access_token`.
2. Click **Authorize** and paste the token.
3. `GET /auth/me` returns your user.

### Frontend without Docker (for development)

**Prerequisites:** Node 22, and the backend running on port 8000 (either way above).

```bash
cd frontend
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm ci
npm run dev                   # http://localhost:3000
```

Stop the database with `docker compose down`. Add `-v` to also delete its data.

## Deployment

```
Browser ──► Vercel (Next.js) ──HTTPS + Bearer JWT──► Railway: backend (Docker) ──private network──► Railway: Postgres
                                                                    └──► Google Gemini API
```

Railway is configured in its dashboard; there is no config file in the repo.

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
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference variable, private network; the `postgresql://` scheme is rewritten to psycopg) |
   | `JWT_SECRET` | output of `openssl rand -hex 32` (use a new value, not the local one) |
   | `GEMINI_API_KEY` | your key |
   | `GEMINI_MODEL` | `gemini-2.5-flash` |
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

## API
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | – | Liveness check |
| POST | `/auth/register` | – | `{email, password}` → `201 {access_token, token_type}`. Duplicate email → 409 |
| POST | `/auth/login` | – | `{email, password}` → `{access_token, token_type}`. Wrong credentials → 401 |
| GET | `/auth/me` | Bearer | `{id, email}` |

Every request to a protected route that fails authentication (no token, bad or expired token, deleted account) returns the same `401 {"detail": "Invalid or expired token"}`.

## Environment variables
All of them are listed with placeholders in [.env.example](.env.example).

| Variable | Used by | Notes |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | docker compose | Credentials for the local database |
| `DATABASE_URL` | backend | Required. `postgres://` and `postgresql://` URLs are accepted too |
| `JWT_SECRET` | backend | Required, at least 32 characters. There is no default |
| `JWT_EXPIRE_MINUTES` | backend | Default 60 |
| `GEMINI_API_KEY` | backend | If empty, AI is treated as unavailable |
| `GEMINI_MODEL` | backend | Default `gemini-2.5-flash` |
| `CORS_ORIGINS` | backend | Comma-separated frontend origins |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL |

## Security notes and known limitations
- **Passwords** are hashed with argon2id. Login runs a hash check even for unknown emails, so response time doesn't reveal which emails are registered.
- **Tokens** carry only the user id, `iat` and `exp`. The server accepts HS256 only, which blocks `alg: none` and algorithm-confusion attacks.
- **Not built, on purpose (scope):** stateless JWTs can't be revoked, so logout happens on the client and the short expiry limits the risk. There are no refresh tokens and no login rate limiting.

## Development
- Pre-commit hooks (gitleaks, ruff, hygiene): `brew install pre-commit && pre-commit install`, then `pre-commit run --all-files`.
- New migration (from `backend/`): `alembic revision --autogenerate -m "..."`, review the file by hand, then `alembic upgrade head`. `alembic check` reports drift between the models and the migrations.
