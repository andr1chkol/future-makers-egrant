# eGrant Document Assistant

Turn invoice data into a form draft. Review the extracted fields and line items beside the original document, correct them, and confirm before exporting JSON.

## Try the demo

Requirements: Git and Docker with Compose.

```sh
git clone https://github.com/andr1chkol/future-makers-egrant.git
cd future-makers-egrant
cp .env.example .env
docker compose up --build --wait
```

1. Open [the app](http://localhost:5173).
2. Upload the [sample invoice](contracts/examples/synthetic-invoice.csv) and start extraction.
3. Review the fields and line items, make a correction, and confirm.
4. Download the confirmed JSON.

The default fixture mode parses the uploaded sample and uses a recorded model response. It needs no API key. The optional live mode requires an OpenAI key and model. OCR uses Tesseract when configured. The app exports JSON for integration with eGrant. Direct form submission to eGrant is outside this release.

Stop the app with `docker compose down`. Docker preserves the local database and uploads in volumes.

[Verification results and release scope](docs/release/FINISH-PRODUCT.md)

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
frontend build. `make test` covers schemas, access, redaction, storage, migrations,
queue recovery, concurrent submission idempotency, invalid/stale reviews and exact
human corrections in the persisted export. Database tests use real PostgreSQL 16.
`make e2e` starts isolated API/frontend servers on 8011/5174 and tests the shell.

The dedicated submission browser suite uses another disposable database and
ports 8013/5176. It resets only a database whose name starts with egrant_test_e2e:

```sh
docker exec egrant-bootstrap-test createdb -U egrant egrant_test_e2e_integration
export INTEGRATION_E2E_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test_e2e_integration
make e2e-integration
```

Profiles have two additional browser suites (two UI-adapter scenarios and one
real UI/API/PostgreSQL workflow with two distinct forms). Use a separate empty
test database; the guarded test server applies the production migrations itself:

```sh
docker exec egrant-bootstrap-test createdb -U egrant egrant_test_profiles_browser
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test_profiles_browser make e2e-profiles
```

The submission suite uses explicit test-only neighboring public-interface doubles while
exercising the real submission routes, PostgreSQL persistence and JSON download.
History UI tests simulate responses for the history list. The complete-product
suite below uses the real neighboring modules. Keep test ports free.

## Contracts and module ownership

Read `AGENTS.md`, `CONTRACT.md`, `QUALITY.md`, `docs/team/README.md` and
`contracts/internal.md` before implementation. Root CONTRACT/QUALITY and their
team copies must stay identical. `BASE_BRANCH=main`; setup was `codex/bootstrap`, integration is `codex/integration`.
The current architecture has no pre-existing application code to reconcile.

`backend/app/platform/contracts.py` defines public Pydantic DTOs. Run
`make generate` after a coordinated change; it writes `contracts/api.yaml` and
`frontend/src/shared/api.generated.ts`. The shared client is `shared/api.ts`.
Do not duplicate models in features. The examples include a missing purchase
order, warnings, table rows, exact sources and a separate human correction.
`python scripts/create_examples.py` rebuilds them deterministically.

Platform migration: `0001_platform`; integration migration: `0501_submissions`.
`0502_profiles_assembly` merges it with the unchanged owned `0301_profiles`.
Reserve `010*` documents, `020*` extraction,
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
Node 22.12+, 24.x or 26+ (supported even-numbered releases) follows [Vite requirements](https://vite.dev/guide/).
Locked installs follow [uv project guidance](https://docs.astral.sh/uv/guides/projects/).

## Review and release

Authors self-review the final diff. Member 4 independently reviews integration
using `docs/team/06-PEER-REVIEW.md` against the exact PR head. The bootstrap review
report is published in [PR #2](https://github.com/andr1chkol/future-makers-egrant/pull/2)
for head 70370b3; its tree matches the baseline merge. Do not move bootstrap-v1
or automatically merge module PRs. Member 1 runs `07-RELEASE-REVIEW.md` after
assembly. The fixture/test interface doubles are not product adapters.

`docs/release/INTEGRATION-HANDOFF.md` contains the provider matrix, dependency
requests, demo procedure, remaining evaluation scenarios and release checklist.
No external application write is enabled. A future live write needs a documented
application-data interface, authorized test target and explicit human confirmation.

## Document runtime and cleanup

Production storage is supported in the Linux containers. macOS supports local
POSIX development; native Windows storage is explicitly unavailable. Use Docker
on Windows. No O_NOFOLLOW protection is replaced with zero. Browser launcher
paths and environment configuration support Windows syntax, but native Windows
application/storage tests were not executed.

The API bounds the complete raw upload to DOCUMENT_MAX_BATCH_BYTES plus 1 MiB
for multipart framing before multipart parsing begins, including chunked bodies.
Per-file and total content limits still apply. API and worker read all DOCUMENT_*
settings from the same Compose env_file. The image includes Tesseract and slk/eng
language data. To enable it, set DOCUMENT_OCR_PROVIDER=tesseract and
DOCUMENT_OCR_EXECUTABLE=/usr/bin/tesseract, then recreate API and worker. Default
OCR remains disabled. The synthetic Linux smoke test does not verify Slovak OCR
accuracy on real applicant documents.

Run orphan cleanup only after all upload processes use this assembly:

```sh
docker compose exec worker uv run --no-sync python -m app.documents.cleanup
```

Cleanup considers UUID originals older than one hour, takes the same PostgreSQL
transaction lock as intake, and checks for a committed document before removing
anything. It skips active uploads, accepted originals, symlinks and non-UUID files.
Do not remove private-volume files manually. Interrupted dot-prefixed staging
files are excluded from this command.

The document browser suite uses an isolated database named
`egrant_test_documents_e2e`, real document routes/storage/worker and explicit
neighboring profile/extraction fixtures:

```sh
export DOCUMENT_E2E_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test_documents_e2e
make e2e-documents
```

See docs/release/DOCUMENTS-ASSEMBLY.md for the earlier document assembly evidence. Separate review links are preserved for separate
documents. No unconfirmed data is exported or applied.

## Complete-product acceptance demo

After the locked install and Chromium installation, create disposable PostgreSQL
databases `egrant_test_full_product` and `egrant_test_full_product_e2e`. Set
`TEST_DATABASE_URL` and `FULL_PRODUCT_E2E_DATABASE_URL` to their connection URLs,
then run `scripts/final-assembly-demo.sh`. The backend test resets the supplied
`egrant_test` database; the browser launcher resets only the exact
`egrant_test_full_product_e2e` database. Never point these commands at demo data.

The script uses the production routes, worker, private storage and real file
normalization in visibly labeled fixture mode. It stops at the first failure.
The backend and browser assertions verify draft persistence, explicit
confirmation and the exact corrected scalar and table values in the downloaded
JSON. There are no neighboring service doubles in this suite.
`make e2e-full-product` runs the browser portion separately; `make test`
includes the backend acceptance cases.

See [the reproducible demo procedure](docs/release/FINAL-ASSEMBLY-DEMO.md)
and [verification evidence](docs/release/FINISH-PRODUCT.md).
