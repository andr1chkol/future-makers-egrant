UV ?= uv
.PHONY: dev install check test e2e generate migrate
install:
	$(UV) sync --locked
	cd frontend && npm ci
dev:
	docker compose up --build
migrate:
	$(UV) run alembic -c backend/alembic.ini upgrade head
generate:
	$(UV) run python scripts/export_contract.py
	cd frontend && npm run generate
check:
	$(UV) lock --check
	$(UV) run ruff check backend scripts tests
	$(UV) run ruff format --check backend scripts tests
	$(UV) run python scripts/scan_secrets.py
	$(UV) run python scripts/export_contract.py
	cd frontend && npm run generate && npm run format:check && npm run build
	git diff --exit-code -- contracts/api.yaml frontend/src/shared/api.generated.ts
test:
	$(UV) run pytest
	cd frontend && npm test
e2e:
	cd frontend && npm run e2e
