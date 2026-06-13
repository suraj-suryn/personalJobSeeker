.PHONY: up down build restart migrate seed test logs pull-models clean help \
        shell-backend shell-db dev-backend dev-frontend

# Default
help:
	@echo ""
	@echo "PersonalJobSeeker — Available Commands"
	@echo "======================================="
	@echo "  make up            Start all Docker services (detached)"
	@echo "  make down          Stop all services"
	@echo "  make build         Rebuild all Docker images (no cache)"
	@echo "  make restart       Restart all services"
	@echo "  make migrate       Apply Alembic database migrations"
	@echo "  make seed          Seed admin user + sample data"
	@echo "  make test          Run backend pytest suite"
	@echo "  make logs          Tail all service logs"
	@echo "  make logs-backend  Tail backend logs only"
	@echo "  make pull-models   Pull Ollama models (llama3.1:8b + nomic-embed-text)"
	@echo "  make shell-backend Open bash in backend container"
	@echo "  make shell-db      Open psql in postgres container"
	@echo "  make clean         Remove all volumes + images (WARNING: deletes data)"
	@echo "  make dev-backend   Run backend locally (no Docker)"
	@echo "  make dev-frontend  Run frontend locally (no Docker)"
	@echo ""

up:
	docker compose up -d
	@echo "Services started. App at http://localhost | API at http://localhost/api"

down:
	docker compose down

build:
	docker compose build --no-cache

restart:
	docker compose restart

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.utils.seed

test:
	docker compose exec backend pytest tests/ -v --tb=short

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

pull-models:
	@echo "Pulling llama3.1:8b (~4.7GB)..."
	docker compose exec ollama ollama pull llama3.1:8b
	@echo "Pulling nomic-embed-text (~274MB)..."
	docker compose exec ollama ollama pull nomic-embed-text
	@echo "Models ready."

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-jobseeker} -d $${POSTGRES_DB:-jobseeker}

clean:
	@echo "WARNING: This will delete ALL data volumes!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose down -v --rmi local

# Local development (without Docker)
dev-backend:
	cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

# Cloudflare Tunnel helper (run after `cloudflared tunnel login`)
tunnel:
	cloudflared tunnel --url http://localhost:80
