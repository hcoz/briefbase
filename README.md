# BriefBase

Paste a note, and BriefBase asks an AI model for a short **summary** and **3–5 tags**, then stores them with the note. You can list your notes, filter them by tag and delete them.

> **Status: work in progress.** The backend has auth (register / login / me). Notes, AI, the frontend and deployment are still to come.

## Tech stack
| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (sync), Alembic, psycopg 3, Python 3.12 |
| Database | PostgreSQL 16 |
| Auth | JWT (HS256, 60 min), passwords hashed with argon2id |
| AI | Google Gemini (`google-genai`, JSON mode) — *coming next* |
| Frontend | Next.js (App Router, TypeScript) + TanStack React Query, Node 22 — *planned* |
| Hosting | Backend + Postgres on Railway, frontend on Vercel — *planned* |

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

> Until the frontend is added, start only the API: `docker compose up -d --build db backend`.

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

Stop the database with `docker compose down`. Add `-v` to also delete its data.

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
