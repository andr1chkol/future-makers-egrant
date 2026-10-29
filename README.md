# eGrant document assistant

Shared foundation for document-to-form extraction with mandatory human review.
Repository: https://github.com/andr1chkol/future-makers-egrant.

This bootstrap candidate provides contracts, platform infrastructure and feature
shells. Domain operations return `503 FEATURE_UNAVAILABLE`. The reference invoice
and linked examples are synthetic. Upload, extraction, profile editing, review,
confirmation and export need the four module implementations and integration.
No OCR, AI or eGrant provider is called. Credentials alone do not enable adapters.

## Start with Docker

Install Docker Desktop with Compose, Git, Python 3.12, uv 0.13.6 and Node 22.12+
with npm. Docker runs the application; host Python/Node are for checks and tests.

```sh
git clone https://github.com/andr1chkol/future-makers-egrant.git
cd future-makers-egrant
git switch codex/bootstrap
cp .env.example .env
make dev
```

Open http://localhost:5173. Compose starts PostgreSQL 16, applies migrations,
then starts API, worker and frontend. Ports bind to loopback only; PostgreSQL uses 55433 (override DB_PORT if needed). The default
fixture configuration permits localhost access and shows a persistent yellow
banner. It never changes an eGrant application. Private uploads use a Docker
volume that is not served by the frontend. Stop with `docker compose down`;
keep volumes to preserve data. Do not use `down -v` on data you need.

Before team module work, member 4 must review the PR in a fresh chat and the
approved commit must be tagged `bootstrap-v1`. Until then this branch is a
candidate, not an approved baseline. After publication use:

```sh
git fetch origin --tags
git rev-parse 'bootstrap-v1^{commit}'
git switch -c codex/documents bootstrap-v1
```

## Local development and verification

```sh
make install
cp .env.example .env
# Start only the development database if running API on the host.
docker compose up -d db
make migrate
PYTHONPATH=backend uv run uvicorn app.main:app --port 8000 --no-access-log
# In other terminals:
PYTHONPATH=backend uv run python -m app.worker
cd frontend && npm run dev
```

The API validates settings at startup. Disable Uvicorn access logs so query
strings and filenames cannot enter logs. There are no secrets in VITE variables.

Ordinary checks use no paid/private providers. Persistence tests reset only an
explicitly supplied database whose name starts with `egrant_test`. They fail
without it; they never substitute SQLite or silently skip database coverage.

```sh
docker run --name egrant-bootstrap-test -e POSTGRES_USER=egrant -e POSTGRES_DB=egrant_test -e POSTGRES_PASSWORD=local-test-only -p 127.0.0.1:55432:5432 -d postgres:16
export TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test
make check
make test
cd frontend && npx playwright install chromium
cd ..
make e2e
```

`make check` checks locks, lint, formatting, OpenAPI drift, generated types and
frontend build. `make test` checks schemas, source agreement, access, redaction,
storage, migrations, concurrent claim/recovery, retry and session persistence.
`make e2e` starts isolated local API/frontend servers on 8011/5174 and checks the
shell and fixture banner in desktop/mobile layouts. Keep those test ports free. The complete document-to-export workflow and
assembled domain-route coverage are pending module integration, not passing tests.
Screenshots are written to docs/release by the shell E2E.

## Contracts and module ownership

Read `AGENTS.md`, `CONTRACT.md`, `QUALITY.md`, `docs/team/README.md` and
`contracts/internal.md` before implementation. Root CONTRACT/QUALITY and their
team copies must stay identical. `BASE_BRANCH=main`; setup is `codex/bootstrap`.
The current architecture has no pre-existing application code to reconcile.

`backend/app/platform/contracts.py` defines public Pydantic DTOs. Run
`make generate` after a coordinated change; it writes `contracts/api.yaml` and
`frontend/src/shared/api.generated.ts`. The shared client is `shared/api.ts`.
Do not duplicate models in features. The examples include a missing purchase
order, warnings, table rows, exact sources and a separate human correction.
`python scripts/create_examples.py` rebuilds them deterministically.

Platform migration: `0001_platform`. Reserve `010*` documents, `020*` extraction,
`030*` profiles, `040*` reviews and `050*` integrations. Module migrations branch
from `0001_platform`; member 5 reconciles heads with a merge migration. Request
shared dependencies, registrations or contracts in each module handoff and PR.
See `contracts/internal.md` for exact signatures, transactions, queue semantics,
router assembly, warning identity and confirmation retries.

## Access and deployment limits

The local bypass requires `APP_MODE=fixture`, `DEV_AUTH_BYPASS=true`, a localhost
PUBLIC_ORIGIN and localhost request hostname. For shared access disable bypass,
set a random ACCESS_CODE of at least 24 characters, PUBLIC_ORIGIN to the exact
HTTPS origin and COOKIE_SECURE=true. Use a trusted TLS reverse proxy; do not
expose Vite or the development API directly to the internet. Login exchanges the
code for an eight-hour HttpOnly SameSite=Strict cookie. Session hashes and expiry
are durable in PostgreSQL. Unsafe requests require an exact Origin match.

This is a single-workspace demo gate, not eGrant identity or production tenant
isolation. Authentication rate limiting belongs at the trusted deployment proxy.
Provider configuration names are in `.env.example`; leave values out of Git.
Unknown external write outcomes require reconciliation. Export is not apply.

## Compatibility sources

The selected versions are resolved in shared lockfiles. Python 3.12 and Pydantic
v2 follow [FastAPI release guidance](https://fastapi.tiangolo.com/release-notes/).
PostgreSQL uses the explicit psycopg 3 dialect described in
[SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#psycopg).
Node 22.12+ follows [Vite requirements](https://vite.dev/guide/).
Locked installs follow [uv project guidance](https://docs.astral.sh/uv/guides/projects/).

## Review and release

Authors self-review the final diff. Member 4 independently reviews bootstrap
using `docs/team/06-PEER-REVIEW.md` against the exact PR head. Do not move an
existing bootstrap-v1 tag or merge automatically. After approval and checks,
publish that tag and SHA, then continue with `05-INTEGRATION-PROMPT.md` on
`codex/integration`. Member 1 runs `07-RELEASE-REVIEW.md` after module assembly.
The shell is not evidence of a working extraction product.
