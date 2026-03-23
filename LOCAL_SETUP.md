# Local Development Setup Guide (macOS)

A step-by-step guide to get Estate Executor OS running on your local macOS machine.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Install System Dependencies](#3-install-system-dependencies)
4. [Start Infrastructure Services](#4-start-infrastructure-services)
5. [Configure Environment Variables](#5-configure-environment-variables)
6. [Set Up the Backend](#6-set-up-the-backend)
7. [Run Database Migrations](#7-run-database-migrations)
8. [Set Up the Frontend](#8-set-up-the-frontend)
9. [Start the Application](#9-start-the-application)
10. [Set Up Background Workers (Optional)](#10-set-up-background-workers-optional)
11. [Verify Everything Works](#11-verify-everything-works)
12. [Useful Commands Reference](#12-useful-commands-reference)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

Make sure you have the following installed on your Mac before continuing.

### Homebrew

If you don't have Homebrew, install it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Docker Desktop

Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/). This is required for running PostgreSQL, Redis, MinIO, and Mailpit via Docker Compose.

After installing, make sure Docker Desktop is **running** (you should see the whale icon in your menu bar).

Verify:

```bash
docker --version
docker compose version
```

### Python 3.11+

The backend requires Python 3.11 or later (3.12 recommended).

```bash
brew install python@3.12
```

Verify:

```bash
python3 --version
# Should show Python 3.12.x (or 3.11.x)
```

> **Tip:** If you use `pyenv` for managing Python versions:
> ```bash
> brew install pyenv
> pyenv install 3.12
> pyenv local 3.12
> ```

### Node.js 20

The frontend requires Node.js 20.

```bash
brew install node@20
```

Or using `nvm`:

```bash
brew install nvm
nvm install 20
nvm use 20
```

Verify:

```bash
node --version
# Should show v20.x.x

npm --version
```

### Git

```bash
git --version
# macOS ships with git; install latest via: brew install git
```

---

## 2. Clone the Repository

```bash
cd ~/Desktop
git clone <repository-url> estate-executor
cd estate-executor
```

---

## 3. Install System Dependencies

These are optional but recommended for full functionality:

```bash
# For psycopg2 (PostgreSQL driver, in case binary wheel isn't available)
brew install libpq

# For building Python packages with C extensions
brew install openssl readline
```

---

## 4. Start Infrastructure Services

The project uses Docker Compose to run all infrastructure services locally. This includes:

| Service    | Port(s)      | Description                          |
|------------|-------------|--------------------------------------|
| PostgreSQL | 5432        | Primary database (v16)               |
| Redis      | 6379        | Cache, pub/sub, and Celery broker    |
| Mailpit    | 1025, 8025  | Local SMTP server + Web UI           |
| MinIO      | 9000, 9001  | S3-compatible object storage         |

Start all services:

```bash
docker compose up -d
```

Wait for all services to become healthy:

```bash
docker compose ps
```

You should see all services with status `Up` or `healthy`. The `minio-init` container will show `Exited (0)` — that's expected as it's a one-time init job that creates the S3 bucket.

### Verify the services

```bash
# PostgreSQL
docker compose exec postgres pg_isready -U postgres
# Should output: /var/run/postgresql:5432 - accepting connections

# Redis
docker compose exec redis redis-cli ping
# Should output: PONG
```

You can also visit:
- **Mailpit Web UI**: [http://localhost:8025](http://localhost:8025) — catches all outgoing emails
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) — login with `minioadmin` / `minioadmin`

---

## 5. Configure Environment Variables

The project uses three `.env` files: one at the root (for Docker Compose), one for the backend, and one for the frontend.

### 5a. Root `.env`

```bash
cp .env.example .env
```

The defaults work out of the box for local development. You only need to fill in API keys for services you plan to use:

| Variable              | Required? | Notes                                        |
|----------------------|-----------|----------------------------------------------|
| `DATABASE_URL`        | Pre-filled | Works with default Docker Compose setup      |
| `REDIS_URL`           | Pre-filled | Works with default Docker Compose setup      |
| `AUTH0_DOMAIN`        | Yes       | Your Auth0 tenant domain                     |
| `AUTH0_API_AUDIENCE`  | Yes       | Your Auth0 API audience                      |
| `AUTH0_CLIENT_ID`     | Yes       | Auth0 application client ID                  |
| `AUTH0_CLIENT_SECRET` | Yes       | Auth0 application client secret              |
| `ANTHROPIC_API_KEY`   | Optional  | Needed for AI-powered features               |
| `STRIPE_SECRET_KEY`   | Optional  | Needed for payment features                  |
| `RESEND_API_KEY`      | Optional  | Needed for real email sending (Mailpit works without it) |
| `APP_SECRET_KEY`      | Yes       | Generate with `openssl rand -hex 32`         |
| `ENCRYPTION_MASTER_KEY`| Yes      | Generate with `openssl rand -hex 32`         |

### 5b. Backend `.env`

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and configure:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/estate_executor
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/estate_executor
REDIS_URL=redis://localhost:6379/0
APP_ENV=development
APP_SECRET_KEY=<run: openssl rand -hex 32>
BACKEND_CORS_ORIGINS=http://localhost:3000
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.estate-executor.com

# Add these for full functionality:
ANTHROPIC_API_KEY=sk-ant-xxx
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
ENCRYPTION_MASTER_KEY=<run: openssl rand -hex 32>

# MinIO (local S3)
AWS_S3_BUCKET=estate-executor-documents
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT_URL=http://localhost:9000
```

### 5c. Frontend `.env`

```bash
cp frontend/.env.example frontend/.env
```

Edit `frontend/.env`:

```dotenv
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_SECRET=<run: openssl rand -hex 32>
AUTH0_AUDIENCE=https://api.estateexecutoros.com
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

> **Auth0 Setup:** You need an Auth0 account and application configured. Create a "Regular Web Application" in Auth0 Dashboard, set the callback URL to `http://localhost:3000/api/auth/callback`, and the logout URL to `http://localhost:3000`.

---

## 6. Set Up the Backend

### 6a. Create a Python virtual environment

It's strongly recommended to use a virtual environment:

```bash
cd backend

python3 -m venv venv
source venv/bin/activate
```

> **Tip:** Add `source ~/Desktop/estate-executor/backend/venv/bin/activate` to your shell profile or use tools like `direnv` for automatic activation.

### 6b. Install Python dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs:
- **Runtime:** FastAPI, SQLAlchemy, Alembic, Celery, boto3, anthropic SDK, and more
- **Dev tools:** pytest, ruff (linter/formatter), mypy (type checker), factory-boy (test factories)

Verify:

```bash
python -c "import fastapi; print(fastapi.__version__)"
# Should output: 0.115.0 or later
```

### 6c. Return to the project root

```bash
cd ..
```

---

## 7. Run Database Migrations

With Docker Compose running (PostgreSQL healthy) and the backend `.env` configured:

```bash
cd backend
source venv/bin/activate   # if not already activated

alembic upgrade head
```

This runs all Alembic migrations and creates the full database schema including:
- `firms`, `users`, `firm_memberships` — multi-tenant user management
- `matters`, `stakeholders` — estate/matter tracking
- `tasks`, `task_dependencies`, `task_documents`, `task_comments` — task management
- `assets`, `asset_documents`, `entity_assets` — asset tracking
- `documents`, `document_versions` — document management
- `deadlines`, `communications` — deadline and communication tracking
- `events`, `email_logs` — audit trail and email logging

### Verify migrations ran successfully

```bash
alembic current
# Should show the latest migration revision

# Or connect directly:
docker compose exec postgres psql -U postgres -d estate_executor -c "\dt"
# Should list all tables
```

Return to root:

```bash
cd ..
```

---

## 8. Set Up the Frontend

```bash
cd frontend
npm install
```

This installs all frontend dependencies including Next.js 16, React 19, Radix UI components, TanStack Query, and Auth0 SDK.

Verify:

```bash
npx next --version
# Should output the Next.js version
```

Return to root:

```bash
cd ..
```

---

## 9. Start the Application

You have two options:

### Option A: Use the Makefile (recommended)

From the project root, run everything at once:

```bash
make dev
```

This will:
1. Start Docker Compose services (if not already running)
2. Start the backend (FastAPI on port 8000 with hot-reload)
3. Start the frontend (Next.js on port 3000 with hot-reload)

### Option B: Start services manually in separate terminals

**Terminal 1 — Infrastructure** (if not already running):

```bash
docker compose up -d
```

**Terminal 2 — Backend:**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Frontend:**

```bash
cd frontend
npm run dev
```

### Access the application

| Service            | URL                                      |
|-------------------|------------------------------------------|
| Frontend          | [http://localhost:3000](http://localhost:3000) |
| Backend API       | [http://localhost:8000](http://localhost:8000) |
| API Docs (Swagger)| [http://localhost:8000/docs](http://localhost:8000/docs) |
| Health Check      | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) |
| WebSocket         | ws://localhost:8000/ws                    |
| Mailpit           | [http://localhost:8025](http://localhost:8025) |
| MinIO Console     | [http://localhost:9001](http://localhost:9001) |

---

## 10. Set Up Background Workers (Optional)

The app uses Celery for background task processing (AI document extraction, email notifications, report generation, deadline monitoring). This is optional for basic development but required for features that use async processing.

**Terminal 4 — Celery Worker:**

```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --queues=default,ai,notifications,documents
```

Or using Make:

```bash
make worker
```

**Terminal 5 — Celery Beat** (scheduled tasks):

```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app beat --loglevel=info
```

Or using Make:

```bash
make beat
```

The beat scheduler runs:
- **Deadline checks** — every hour
- **Overdue task checks** — every 6 hours

---

## 11. Verify Everything Works

### Backend health check

```bash
curl http://localhost:8000/api/v1/health
# Should return a JSON response indicating the service is healthy
```

### Run backend tests

```bash
cd backend
source venv/bin/activate
python -m pytest
```

### Run frontend tests

```bash
cd frontend
npm test
```

### Run linters

```bash
# From project root
make lint
```

### Run E2E tests (requires both backend and frontend running)

```bash
cd frontend
npx playwright install chromium   # first time only
npm run test:e2e:chromium
```

---

## 12. Useful Commands Reference

| Command                  | Description                                         |
|--------------------------|-----------------------------------------------------|
| `make setup`             | Install all backend and frontend dependencies       |
| `make dev`               | Start everything (Docker + backend + frontend)      |
| `make dev-services`      | Start only Docker infrastructure services           |
| `make migrate`           | Run database migrations (`alembic upgrade head`)    |
| `make test`              | Run all tests (backend + frontend)                  |
| `make lint`              | Run all linters (ruff, mypy, eslint, tsc)           |
| `make worker`            | Start Celery worker (all queues)                    |
| `make beat`              | Start Celery beat scheduler                         |
| `make clean`             | Stop and remove all Docker services and volumes     |
| `docker compose logs -f` | Tail logs from all Docker services                  |
| `docker compose ps`      | Check status of Docker services                     |

### Database management

```bash
cd backend && source venv/bin/activate

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Upgrade to latest
alembic upgrade head

# Downgrade one step
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current

# Connect to database directly
docker compose exec postgres psql -U postgres -d estate_executor
```

---

## 13. Troubleshooting

### Port conflicts

If ports are already in use:

```bash
# Find what's using a port
lsof -i :5432   # PostgreSQL
lsof -i :6379   # Redis
lsof -i :3000   # Frontend
lsof -i :8000   # Backend
```

Stop the conflicting process or change the port in `docker-compose.yml` / the run command.

### Docker services won't start

```bash
# Check logs for a specific service
docker compose logs postgres
docker compose logs redis

# Restart all services
docker compose down
docker compose up -d

# Full reset (destroys all data)
make clean
docker compose up -d
```

### Database connection errors

1. Make sure Docker Compose is running: `docker compose ps`
2. Make sure PostgreSQL is healthy: `docker compose exec postgres pg_isready -U postgres`
3. Verify your `DATABASE_URL` in `backend/.env` points to `localhost:5432`

### Migration errors

```bash
# Reset the database completely
docker compose exec postgres psql -U postgres -c "DROP DATABASE estate_executor;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE estate_executor;"
cd backend && alembic upgrade head
```

### Python virtual environment issues

```bash
# Recreate the virtual environment
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Node.js / npm issues

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Auth0 not working

- Ensure your Auth0 application type is set to "Regular Web Application"
- Callback URL must be: `http://localhost:3000/api/auth/callback`
- Logout URL must include: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`
- Make sure `AUTH0_SECRET` is set (generate with `openssl rand -hex 32`)

### MinIO / S3 upload issues

For local development, MinIO acts as the S3-compatible storage. Make sure:
- `AWS_ACCESS_KEY_ID=minioadmin`
- `AWS_SECRET_ACCESS_KEY=minioadmin`
- `S3_ENDPOINT_URL=http://localhost:9000` is set in your backend `.env`
- The bucket `estate-executor-documents` exists (auto-created by `minio-init` container)
