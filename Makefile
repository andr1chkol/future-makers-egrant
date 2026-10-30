UV ?= uv
.PHONY: dev install check test e2e generate migrate e2e-integration e2e-profiles e2e-documents e2e-full-product
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

e2e-integration:
	cd frontend && npx playwright test --config playwright.integration.config.ts

e2e-profiles:
	cd frontend && npx playwright test --config src/features/profiles/playwright.config.ts
	cd frontend && npx playwright test --config src/features/profiles/playwright.integration.config.ts

e2e-documents:
	frontend/node_modules/.bin/playwright test --config tests/documents/playwright.config.cjs

e2e-full-product:
	cd frontend && npx playwright test --config playwright.full-product.config.ts
