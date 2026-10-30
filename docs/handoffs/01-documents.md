# Member 1: document intake and normalized sources

Branch: `codex/documents`. PR target: `main`. Verified baseline:
`bootstrap-v1`, `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
The pending-review text in the frozen bootstrap documents is stale; the tag exists
and matches the SHA supplied by the team. No frozen contracts or shared runtime
files were changed.

## Delivery status

The owned backend and upload feature are implemented and tested. Shared-app
assembly is still required from member 5 before normal application routes work.
The unchanged foundation currently serves document shells and an unavailable
worker handler. Browser tests replace those registrations in a test assembly of
the existing application; they do not prove that integration has been merged.

GitHub refused the authenticated push dry run with HTTP 403: the current account
has no repository write permission. No remote branch, PR, review request, merge,
or deployment was created. An independent agent reviewed the implementation and
its fixes. Member 5's fresh-chat peer review is still required.

## Public interfaces and registrations

```python
from app.documents.routes import router
from app.documents.service import get_normalized, process_document, reconcile_interrupted

get_normalized(session: Session, document_id: UUID) -> NormalizedDocument
process_document(session: Session, document_id: UUID) -> None
reconcile_interrupted(session: Session) -> None
```

`get_normalized` never commits. Unknown IDs raise `NotFoundError`; uploaded,
processing and failed documents raise `ConflictError`. Ready source units are
immutable. Retrying a ready document returns 409; a new upload is required to
produce different source data. Source IDs are UUIDv5 values derived from the
document ID and page or sheet/cell location. Units remain ordered across reads.

Member 5 must make these shared changes in a coordinated integration PR:

1. Remove all six document shell operations from `app.platform.routes`, then
   include `app.documents.routes.router` under `/api/v1` in `create_app`, retaining
   `Depends(require_access)`. The owned router also requires that gate. Its
   operations, including binary response metadata, match the frozen OpenAPI.
2. Replace the reserved `document.process` registration in
   `app.worker.build_registry` with `process_document`. Register exactly once.
   Use the existing worker and fresh Sessions. Optionally call
   `reconcile_interrupted` periodically with its own fresh Session; HTTP list,
   detail and retry operations already invoke it before their main operation.
3. Add `backend/app/documents/migrations` to Alembic `version_locations`, alongside
   `backend/migrations/versions`; import document models for metadata discovery.
   Revision `0101_documents` branches from `0001_platform` and has branch label
   `documents`. It creates `documents` and `document_source_units`. Reconcile
   other module heads with a new merge revision, without rewriting published IDs.
4. Add and lock runtime dependencies `pypdfium2==5.14.0`, `Pillow==13.0.0`,
   `openpyxl==3.1.5` and `defusedxml==0.7.1`. Add `pypdf==6.21.4` to development
   dependencies for synthetic PDF tests. These exact versions were provisioned
   locally after installing the unchanged bootstrap lockfile. The manifests and
   lockfiles have intentionally not been edited by member 1.
5. Set capability `ocrConfigured` from `app.documents.ocr.ocr_configured()`.
   Credentials in `OCR_BASE_URL`/`OCR_API_KEY` alone do not enable an adapter.
   Forward the document environment variables below into API and worker containers.
6. Fix shared storage support before using Windows. `PrivateStorage.read` uses
   `os.O_NOFOLLOW`, which does not exist on Windows. Production calls fail visibly
   with `STORAGE_UNAVAILABLE`; no runtime bypass was added. Module persistence and
   browser tests opt into a named test-only flag shim for regular temporary files.
   Those checks do not verify Windows ACLs or symlink protection. Linux storage
   permissions were not reverified in this Windows session.
7. Enforce a total multipart request limit at the trusted proxy/ASGI boundary.
   FastAPI spools multipart bodies before the handler can apply domain limits.
   Preserve immutable UUID storage and add an orphan-file cleanup mechanism:
   shared storage has no delete API, so an I/O or DB failure after `put` can leave
   an inaccessible file without a committed document row. No user files are
   deleted by this module.
8. Make shared fixtures/CI portable if Windows is supported. The platform database
   fixture assumes `.venv/bin/alembic`. Local verification copied the installed
   Windows launcher into that ignored directory. Keep fixture CSV bytes as LF:
   Git's Windows CRLF conversion otherwise changes the documented content hash.
   The local reference CSV was restored byte-for-byte from its Git blob, with no
   tracked change. Shared frontend formatting also needs an explicit line-ending
   policy; `--end-of-line auto` passes on this checkout.

The existing frontend router already imports `UploadPage` from
`frontend/src/features/upload/index.ts`; no router change is needed.

## Intake, provenance and failures

Multipart field name is `files`, as frozen in OpenAPI. A direct multi-file request
is preflighted completely before persistence. Invalid content rejects the whole
request with 422 or 413; it accepts no documents and creates no jobs. Once accepted,
each file has its own document and job, so later processing failures are independent.
The UI submits one file per request, retaining successful uploads when another
file is rejected. Accepted files survive refresh through the paginated API list.
Unaccepted local files are held only in browser memory and disappear on refresh.

Original bytes are stored separately from database source units through the shared
`PrivateStorage`, using generated UUIDs exclusively. Filenames are display metadata,
stripped of path components and characters below U+0020, never storage paths. SHA-256
identifies duplicates; equal hashes are serialized with ordered PostgreSQL advisory
locks. Copies remain separate files and receive `duplicateOf` plus a warning.
Processing checks the stored hash again before publishing any source data.

Text PDFs are read through PDFium, one unit per page. Pages without usable text
are rendered for OCR. Images use page 1. XLSX uses cached formula results and
never executes formulas, macros or links. Missing cached results generate
`FORMULA_VALUE_UNAVAILABLE`. Each populated cell retains its sheet name and A1
coordinate. CSV uses sheet `CSV`, logical record numbers and A1 coordinates;
blank records consume a row number. Supported encodings are UTF-8, optional UTF-8
BOM and BOM-marked UTF-16. Comma, semicolon and tab delimiters are detected.
Malformed quoting, inconsistent widths, binary controls and unsupported encoding
fail explicitly. Empty sources never become a successful normalized document.

Parsing runs in a killable subprocess, outside database transactions. Linux also
receives a 768 MiB address-space limit; that memory limit is unavailable on Windows.
The full processing timeout fits inside the platform's fixed 60-second lease.
Domain publication locks and compares the document token and current job lease;
an expired or replaced worker cannot publish sources. Results and the ready state
commit together. Repeated ready jobs are no-ops. Crashed final leases are exposed
as `PROCESSING_INTERRUPTED` and persisted by reconciliation.

There are at most three processing attempts per document, including manual retries.
Transient 502 failures use platform backoff and remain `uploaded`, so UI polling
continues. Terminal failures are `failed`. Manual retry is accepted only after a
failed job has finished and attempts remain; concurrent retries enqueue once.

Member 4 can download `/api/v1/documents/{id}/content` through the gate and navigate
to `/documents?document=<UUID>&page=2` or
`/documents?document=<UUID>&sheet=<encoded-sheet>&cell=B4`. Optional `unit=<unitId>`
filters the exact unit. PDF page selection and spreadsheet filters are visible;
original images/PDFs and normalized cell/text sources are previewed privately.
The UI creates one review link per returned extraction ID and restores existing
links from the extraction list. Extraction and profile lists currently display
the first 200 records and disclose truncation. Document pagination uses 50 records.

## Configuration and provider verification

Document settings are owned in `app.documents.settings.DocumentSettings`, read
from environment or `.env`, and prefixed `DOCUMENT_`.

| Variable suffix | Default |
| --- | --- |
| `MAX_BYTES` | 20 MiB; cannot exceed shared storage's 20 MiB ceiling |
| `MAX_BATCH_FILES`, `MAX_BATCH_BYTES` | 20 files, 40 MiB |
| `MAX_PAGES` | 100 |
| `MAX_ROWS`, `MAX_COLUMNS`, `MAX_CELLS`, `MAX_SHEETS` | 10,000; 256; 100,000; 50 |
| `MAX_ZIP_FILES`, `MAX_UNCOMPRESSED_BYTES`, `MAX_COMPRESSION_RATIO` | 2,000; 50 MiB; 100:1 |
| `MAX_PIXELS`, `MAX_TEXT_CHARS` | 25,000,000; 2,000,000 |
| `PROCESSING_SECONDS`, `VALIDATION_SECONDS`, `OCR_SECONDS` | 40; 10; 10 |
| `OCR_PROVIDER`, `OCR_EXECUTABLE`, `OCR_LANGUAGES` | `disabled`; unset; `slk+eng` |

Row/cell limits are cumulative across workbook sheets, including sparse/blank
positions. Worksheet dimensions cannot hide rows from those limits. XLSX DTD/entity
payloads, VBA parts and encrypted archives are rejected. Animated images are not
supported. CSV field length is bounded by `MAX_TEXT_CHARS`.

To select the implemented alternative OCR adapter, install Tesseract plus Slovak
and English language data in the runtime and configure:

```dotenv
DOCUMENT_OCR_PROVIDER=tesseract
DOCUMENT_OCR_EXECUTABLE=/usr/bin/tesseract
DOCUMENT_OCR_LANGUAGES=slk+eng
```

The executable must be an absolute existing file. OCR uses private stdin/stdout
pipes, no shell and no filenames or recognized text in logs. Empty results,
timeouts and process failures have distinct safe codes. There is no automatic
fixture provider in live mode.

| Path | Verification |
| --- | --- |
| PDF text, XLSX, UTF-8/UTF-16 CSV | Real format parsing verified |
| Scanned PDF, JPEG, PNG OCR | Injected fake adapter verified in ordinary tests |
| Local Tesseract OCR | Not verified: executable/language data not configured |
| eGrant OCR | Unavailable: documentation and credentials not supplied |

The separate live smoke command was actually executed and exited 2 with
`{"status":"NOT_VERIFIED","errorCode":"OCR_UNAVAILABLE"}`. After installing and
configuring the provider, rerun it using a permitted sample:

```sh
PYTHONPATH=backend .venv/bin/python tests/documents/live_ocr.py \
  --sample .private/browser-sample.png --media-type image/png
```

This synthetic PNG is generated by the browser-test server. Fake OCR success
does not establish live OCR accuracy. Long documents that exceed the configured
budget must be split; the shared worker has no heartbeat or lease renewal.

## Verification evidence

Host: Windows, Python 3.12.10, Node 22+, PostgreSQL 16.15 on loopback port 55434.
Initial module checks also passed on the installed PostgreSQL 18 instance; the
final checks use 16.15. Tests use isolated `egrant_test*` databases, never SQLite.
The test fixture refuses to reset other database names. Ordinary tests force
disabled OCR and deterministic limits regardless of local provider settings.

Install shared locks first. Until member 5 updates dependencies, this temporary
verification setup is required; `uv sync` alone does not install the format parsers:

```sh
uv sync --locked
npm ci --prefix frontend
uv pip install --python .venv/bin/python pypdfium2==5.14.0 Pillow==13.0.0 \
  openpyxl==3.1.5 defusedxml==0.7.1 pypdf==6.21.4
export TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55434/egrant_test_documents
.venv/bin/python -m pytest tests/documents -q
```

On Windows, use `.venv/Scripts/python.exe` and set variables with PowerShell's
`$env:NAME=...`. The test database has local trust authentication and binds to
loopback; production database credentials are outside this handoff.

| Actual check | Result |
| --- | --- |
| Full `python -m pytest -q` on PostgreSQL 16.15 | 96 passed, 1 failed, exit 1 |
| `python -m pytest tests/documents -q` on PostgreSQL 16.15 | 65 passed, exit 0, 74.47 seconds |
| Shared failure | `test_private_storage_is_immutable_and_rejects_traversal`: missing Windows `os.O_NOFOLLOW` |
| `ruff check backend scripts tests` | Passed, exit 0 |
| `ruff format --check backend scripts tests` | Passed, exit 0 |
| `uv lock --check` | Passed, exit 0 |
| `python scripts/scan_secrets.py` | Passed, exit 0 |
| Contract export, client generation, frozen-file diff | Passed; no schema/client drift |
| `npm test --prefix frontend` | 7 tests passed, exit 0 |
| `npm run build --prefix frontend` | Passed, exit 0 |
| Prettier check of owned feature | Passed, exit 0 |
| Shared default Prettier check on CRLF checkout | Failed for existing shared line endings |
| Shared Prettier with `--end-of-line auto` | Passed, exit 0 |
| Document Playwright suite on PostgreSQL 16.15 | 2 passed, exit 0, 24.2 seconds |

Meaningful coverage includes real PDF text, fake OCR page ordering, images,
spreadsheet coordinates/cached formulas, CSV encodings/blank rows, corruption,
spoofing, traversal filenames, limits, macros/XML entities, false worksheet
dimensions, duplicates, concurrent retries, bounded retries, stale workers,
restart recovery, terminal crash reconciliation, access checks, exact OpenAPI
operations, log correlation and realistic synthetic secret/PII redaction.

`make` and Docker are unavailable on this host, so checks were run through their
underlying commands. The shared foundation E2E launcher was not executed: it uses
POSIX shell environment syntax and `.venv/bin/python`. The document-specific
Playwright configuration supplies a cross-platform launcher. Full Compose startup,
Linux file protection and the assembled extraction/review/export flow remain
unverified in this session.

Browser tests reuse the shared application and generated API client. They exercise
real upload/storage/normalization with test-only neighboring profile/extraction
routes, including consumption of `get_normalized`. These stubs exist only under
`tests/documents`; no fake integration was added to production modules. The Windows
storage flag shim is explicit in the test server. Run with dedicated database
`egrant_test_documents_e2e` and free API/frontend ports 8012/5175:

```sh
export DOCUMENT_E2E_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55434/egrant_test_documents_e2e
cd frontend
npx playwright install chromium
npx playwright test --config ../tests/documents/playwright.config.cjs
```

Screenshots in `.private/upload-desktop.png` and `.private/upload-mobile.png` were
visually inspected. Browser assertions check 375, 768 and 1440 pixel layouts for
overflow. They also check partial batch failure, source-cell preview, reload,
retry, distinct extraction links and review-route navigation. The initial invalid
PNG fixture was replaced with a deterministic PNG generated by the server.

## Logs and final review

Events use the shared logger: `document.uploaded`, `document.processing_started`,
`document.ready`, `document.failed`, `document.duplicate_detected`, and
`job.retry_scheduled`. Platform worker completion/retry events remain unchanged.
Context contains safe UUIDs, attempts, elapsed milliseconds and error codes.
Request correlation is copied into platform jobs. OCR content, source values,
filenames, credentials and arbitrary provider exception messages are excluded.

Author final-review inspected the actual diff and surrounding platform code.
The additional independent agent found missing binary OpenAPI metadata, premature
polling termination during retries, and preview focus/fixture issues. These were
fixed with contract, retry and browser coverage. Human-code guided implementation;
humanizer was applied only to this technical handoff, preserving executable blocks,
identifiers and claims. The assembled document-to-confirmed-export product still
needs the other modules and member 5's integration/review.

## Manual reproduction and publication

After member 5 completes registration and dependencies:

1. Start the existing Compose stack with permitted storage and configured access.
2. Open `/documents`. Upload a text PDF and CSV, then a corrupt PDF. Valid files
   remain listed; the invalid upload explains its failure in Slovak.
3. Open a ready preview. Check page 2 of the PDF and an exact spreadsheet cell.
   Download the original and compare its hash with `contentHash`.
4. Upload the same file twice. Both remain present and the second warns of a duplicate.
5. Upload a scan with OCR disabled. It fails with `OCR_UNAVAILABLE`; enable a real
   provider and retry while attempts remain. Refresh during processing.
6. Select a configured profile and ready documents. Launch extraction and verify
   a separate review link for each document. No confirmation/export/apply happens here.

With write access and GitHub CLI available, publish from this branch:

```sh
git push -u origin codex/documents
gh pr create --base main --head codex/documents --draft \
  --title "Implement private document intake and source normalization" \
  --body-file docs/handoffs/01-documents.md
git rev-parse HEAD
```

Attach the created PR to the task, then give member 5 its URL and exact head SHA
with `docs/team/06-PEER-REVIEW.md` in a fresh chat. Do not merge automatically.
