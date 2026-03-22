.PHONY: setup dev dev-services dev-backend dev-frontend migrate test lint clean

# Install all dependencies
setup:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Start everything for local development
dev: dev-services
	@echo "Starting backend and frontend..."
	@trap 'kill 0' EXIT; \
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev & \
	wait

# Start infrastructure services only
dev-services:
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 3
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"
	@echo "Mailpit UI: http://localhost:8025"

# Run database migrations
migrate:
	cd backend && alembic upgrade head

# Run all tests
test:
	cd backend && python -m pytest
	cd frontend && npm test

# Run linters
lint:
	cd backend && ruff check . && ruff format --check . && mypy app
	cd frontend && npm run lint && npx tsc --noEmit

# Stop and clean up docker services
clean:
	docker compose down -v
