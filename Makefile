.PHONY: install api mcp test lint frontend check

install:
	cd backend && uv sync --all-extras --all-groups
	cd frontend && npm install

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

mcp:
	cd backend && uv run python -m app.mcp_server

frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .

check: lint test
	cd frontend && npm run build

