.PHONY: dev test lint build push-fly

# ── Local dev ─────────────────────────────────────────────────────────────────
dev:
	@echo "Starting StatEdge locally..."
	@cp -n .env.example .env 2>/dev/null || true
	@cd frontend && cp -n .env.example .env 2>/dev/null || true
	docker compose up --build

dev-backend:
	@cd backend && PYTHONPATH=. uvicorn src.api.main:app --reload --port 8000

dev-frontend:
	@cd frontend && npm run dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	@cd backend && PYTHONPATH=. pytest tests/ -v --tb=short

test-backend:
	@cd backend && PYTHONPATH=. pytest tests/ -v

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	@cd backend && ruff check src/ tests/
	@cd frontend && npm run type-check

lint-fix:
	@cd backend && ruff check --fix src/ tests/

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	docker compose build

# ── Fly.io deployment (single app: API + frontend in one image) ──────────────
deploy:
	@echo "Deploying StatEdge (combined app) to Fly.io..."
	fly deploy
	@echo "✓ StatEdge deployed"

# ── Fly.io secrets ────────────────────────────────────────────────────────────
fly-secrets:
	@echo "Setting Fly.io secrets from .env..."
	@grep -v '^#' .env | grep -v '^$$' | xargs -I{} fly secrets set {} --app statedge-api

# ── Database ──────────────────────────────────────────────────────────────────
db-migrate:
	@cd backend && alembic upgrade head

db-shell:
	docker compose exec db psql -U statedge statedge

# ── Install ───────────────────────────────────────────────────────────────────
install:
	@cd backend && pip install -r requirements.txt
	@cd frontend && npm install

# ── Git ───────────────────────────────────────────────────────────────────────
save:
	git add -A
	git commit -m "chore: save progress [$(shell date -u +%Y-%m-%dT%H:%M:%SZ)]"
	git push origin main
