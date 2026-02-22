.PHONY: dev dev-backend dev-frontend test lint build docker-up docker-down clean help

# Default target
help:
	@echo "AgentChord Visual Builder"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start backend and frontend (requires 2 terminals)"
	@echo "  make dev-backend    - Start backend dev server"
	@echo "  make dev-frontend   - Start frontend dev server"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linters"
	@echo ""
	@echo "Production:"
	@echo "  make build          - Build frontend for production"
	@echo "  make docker-up      - Start all services via Docker"
	@echo "  make docker-down    - Stop all Docker services"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make install        - Install all dependencies"

# Development
dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	npm run dev

install:
	cd backend && pip install -r requirements.txt
	npm install

# Testing
test:
	cd backend && python -m pytest tests/ -q --tb=short

test-cov:
	cd backend && python -m pytest tests/ --cov=app --cov-report=html

# Linting
lint:
	npm run lint
	cd backend && python -m py_compile app/main.py

# Build
build:
	npm run build

# Docker
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# Clean
clean:
	rm -rf dist node_modules/.vite
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type f -name "*.pyc" -delete 2>/dev/null || true
