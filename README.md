# PersonalJobSeeker 🎯

> AI-powered job search and application assistant — zero cost, runs locally or publicly via Cloudflare Tunnel.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=nextdotjs)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What It Does

PersonalJobSeeker is a production-ready AI agent that:

- **Scrapes jobs every 15 minutes** from LinkedIn, Indeed, Wellfound, and Naukri
- **Scores your resume** against every job using vector similarity + LLM skill-gap analysis
- **Sends desktop/email alerts** within 15 minutes of new matching jobs
- **Optimizes your resume** for specific jobs (without fabricating anything)
- **Generates cover letters** in professional, enthusiastic, or concise tone
- **Writes LinkedIn messages** and email drafts for outreach
- **Prepares you for interviews** with technical, behavioral, and company-specific questions
- **Automates job applications** via browser automation (requires your confirmation before submitting)
- **Tracks applications** in a Kanban board (saved → applied → interviewing → offer/rejected)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Nginx (port 80)                   │
│         /  → Frontend    /api/ → Backend            │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼───────────┐     ┌──────────▼──────────┐
│  Next.js 14   │     │   FastAPI Backend    │
│  (port 3000)  │     │   (port 8000)        │
│               │     │                      │
│  Redux Toolkit│     │  APScheduler (15min) │
│  TanStack Q   │     │  AI Agents           │
│  Tailwind CSS │     │  Job Scrapers        │
└───────────────┘     └──────┬───────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐   ┌────────▼──────┐   ┌───────▼──────┐
   │ PostgreSQL  │   │   ChromaDB    │   │    Ollama    │
   │   15-alpine │   │  (vectors)    │   │  (local LLM) │
   └─────────────┘   └───────────────┘   └──────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111, Python 3.11, SQLAlchemy 2.0 async |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind CSS |
| Database | PostgreSQL 15, ChromaDB 0.5 (vector store) |
| AI / LLM | Ollama (local) → OpenRouter → Groq → Gemini fallback chain |
| Embeddings | nomic-embed-text (768-dim, via Ollama) |
| Scheduler | APScheduler 3.10 (runs inside FastAPI process) |
| Browser | Playwright 1.45 (async, stealth mode) |
| Auth | JWT (python-jose), bcrypt passwords, role-based (admin/user) |
| Infra | Docker Compose, Nginx reverse proxy |

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Docker Desktop | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |
| Git | Any | [git-scm.com](https://git-scm.com/download/win) |

> Docker Desktop includes everything else (no Python or Node.js needed on the host).

---

## Quick Start (5 Steps)

### 1 — Clone the repository

```bash
git clone https://github.com/suraj-suryn/personalJobSeeker.git
cd personalJobSeeker
```

### 2 — Create your `.env` file

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Open `.env` and set these **required** values:

```env
APP_SECRET_KEY=your-random-64-char-secret-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourStrongPassword1!
POSTGRES_PASSWORD=yourdbpassword
DATABASE_URL=postgresql+asyncpg://jobseeker:yourdbpassword@postgres:5432/jobseeker
JWT_SECRET_KEY=another-random-64-char-secret-here
```

> All other values have working defaults. LLM defaults to **Ollama** (free, local, private).

### 3 — Build and start all services

```bash
# First time only — builds all Docker images (~5-10 min)
docker compose build

# Start all 6 services in background
docker compose up -d

# Watch startup logs (Ctrl+C to stop watching)
docker compose logs -f
```

### 4 — Apply database migrations and seed data

```bash
# Create all database tables
docker compose exec backend alembic upgrade head

# Create admin account + 3 sample jobs
docker compose exec backend python -m app.utils.seed
```

### 5 — Pull AI models (first time only, ~5 GB)

```bash
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text
```

> **Skip Ollama entirely:** Set `GROQ_API_KEY` in `.env` (free at [console.groq.com](https://console.groq.com)) and skip model downloads. Groq offers 14,400 free requests/day.

---

## Access the App

| URL | Description |
|-----|-------------|
| http://localhost | Frontend UI |
| http://localhost/api/docs | Swagger API docs |
| http://localhost:8000/docs | API docs (direct) |

**Default login:**
- Email: value of `ADMIN_EMAIL` in your `.env`
- Password: value of `ADMIN_PASSWORD` in your `.env`

---

## LLM Provider Options (Zero Cost)

The app auto-falls back through providers in this order:

```
Ollama (local) → OpenRouter (free) → Groq (free) → Gemini (free) → OpenAI (paid)
```

| Provider | Cost | Setup |
|----------|------|-------|
| **Ollama** | Free, private | Built in — just run `docker compose up` |
| **Groq** | Free (14,400 req/day) | [console.groq.com](https://console.groq.com) → set `GROQ_API_KEY` in `.env` |
| **Gemini** | Free (1M tokens/day) | [aistudio.google.com](https://aistudio.google.com) → set `GEMINI_API_KEY` in `.env` |
| **OpenRouter** | Free models available | [openrouter.ai](https://openrouter.ai) → set `OPENROUTER_API_KEY` in `.env` |
| **OpenAI** | Paid | Set `OPENAI_API_KEY` in `.env` |

Each user can select their preferred provider in the **Settings** page.

---

## User Management

Admin creates all accounts — there is no self-registration endpoint:

```bash
# Via Swagger UI at http://localhost/api/docs
POST /v1/auth/admin/users
{
  "email": "colleague@example.com",
  "name": "Jane Smith",
  "password": "SecurePass1!"
}
```

Or use the **Settings → User Management** section in the UI (admin only).

---

## Common Commands

```bash
# Start / Stop
docker compose up -d                        # Start all services
docker compose down                          # Stop all services
docker compose restart backend               # Restart backend after code changes

# Database
docker compose exec backend alembic upgrade head          # Apply migrations
docker compose exec backend python -m app.utils.seed      # Seed sample data
docker compose exec postgres psql -U jobseeker -d jobseeker  # DB shell

# Testing
docker compose exec backend pytest tests/ -v --tb=short

# Logs
docker compose logs -f                       # All services
docker compose logs -f backend               # Backend only

# AI Models
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama list       # See installed models

# Full rebuild (after changing Dockerfile or requirements.txt)
docker compose build --no-cache
docker compose up -d
```

---

## Public Access via Cloudflare Tunnel (Zero Cost)

Expose the app to the internet without a server or domain:

```bash
# Install cloudflared (Windows)
winget install Cloudflare.cloudflared

# Start tunnel — exposes http://localhost on a public HTTPS URL
cloudflared tunnel --url http://localhost
```

Cloudflare prints a `https://*.trycloudflare.com` URL. Share it with your trusted users and update `APP_ALLOWED_ORIGINS` in `.env`.

---

## Project Structure

```
personalJobSeeker/
├── backend/
│   ├── app/
│   │   ├── agents/          # AI agents (resume parser, match scorer, cover letter, interview prep, browser)
│   │   ├── api/v1/          # FastAPI route handlers (auth, jobs, resumes, scoring, applications, etc.)
│   │   ├── core/            # Security, LLM router, embeddings, APScheduler
│   │   ├── models/          # SQLAlchemy ORM models (8 tables)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── scrapers/        # Job scrapers (LinkedIn, Indeed, Wellfound, Naukri)
│   │   ├── services/        # Business logic services
│   │   └── main.py          # FastAPI app factory + lifespan
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages (8 pages)
│       ├── components/      # Sidebar, Providers
│       ├── lib/             # Axios API client, utilities
│       └── store/           # Redux Toolkit slices
├── docker/
│   ├── nginx/nginx.conf     # Reverse proxy config
│   └── postgres/init.sql    # DB initialization
├── docker-compose.yml       # 6-service orchestration
├── Makefile                 # Shortcut commands
└── .env.example             # Environment variable template
```

---

## API Reference (Key Endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/auth/login` | Login — returns JWT token |
| GET | `/v1/auth/me` | Current user profile |
| POST | `/v1/resumes/upload` | Upload PDF/DOCX resume |
| POST | `/v1/jobs/search` | Trigger live job search |
| GET | `/v1/jobs/` | List jobs (paginated, filterable) |
| GET | `/v1/jobs/recent/new` | Jobs found in last N hours |
| POST | `/v1/scoring/score` | Score a job against your resume |
| GET | `/v1/scoring/matches` | Match dashboard with stats |
| POST | `/v1/cover-letters/generate` | Generate cover letter |
| POST | `/v1/outreach/generate` | Generate LinkedIn/email message |
| POST | `/v1/interview-prep/generate` | Generate interview prep materials |
| POST | `/v1/automation/start` | Start browser automation session |
| POST | `/v1/automation/confirm/{id}` | Confirm form submission (REQUIRED before submit) |
| WS | `/v1/automation/ws/{id}` | Real-time automation events |

Full interactive docs: **http://localhost/api/docs**

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker: command not found` | Install Docker Desktop and restart terminal |
| Backend crashes on startup | Run `docker compose logs backend` — likely DB not ready, try `docker compose restart backend` |
| `alembic upgrade head` fails | Check postgres is healthy: `docker compose ps` |
| Ollama runs out of memory | Use Groq/Gemini instead: set `GROQ_API_KEY` in `.env` |
| Port 80 already in use | Edit `docker-compose.yml` nginx ports to `"8080:80"`, use `http://localhost:8080` |
| Frontend shows blank page | `docker compose logs frontend` then `docker compose restart frontend` |
| Jobs not appearing | Click "Search New Jobs" in the UI, or wait up to 15 min for the scheduler |
| Login fails after seed | Verify `ADMIN_EMAIL` and `ADMIN_PASSWORD` match what's in your `.env` |

---

## Security

- `.env` is in `.gitignore` — **never commit it**
- Browser automation will **not submit** any form without an explicit `/automation/confirm/{id}` API call
- Admin account is seeded from `.env` on first startup only
- JWT tokens expire after 7 days
- All passwords are bcrypt-hashed with cost factor 12

---

## License

MIT — free to use for personal and commercial purposes.