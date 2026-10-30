# Documents shared assembly

Date: 2026-10-30. Member 5. Target: main. Status: documents assembly implemented;
complete product NOT READY. No merge, deployment or eGrant write was performed.

## Provenance and reviewed state

- Baseline: bootstrap-v1, 88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8, unchanged.
- Existing local integration: f9aa015; existing published integration: 74da164.
  Their equivalent source trees and existing profiles/export work were retained.
- Member 1 source: 9a9bfa5be372fbac5a7408b0648f32ff75cb8460. The commit was
  fetched directly; no patch import was needed. Original source is preserved as
  a merge parent. Source publication: draft PR #10.
- Local source merge: 1db089f076ccde6629719acc1a466c3873820f4b.
- Formal fresh-chat review: docs/reviews/documents-9a9bfa5.md, CHANGES REQUIRED
  against original 9a9bfa5. Review correction source:
  af2765eade1be06b370bb4cb28efb39f2d5cb526; applied local SHA:
  4f18637381515ca869d73287033c97ad5d6a1e88.
- Local self-reviewed integration code: 8ae470ae17c323469a3ca9bf744a2ff819213d78.
- Published equivalent code: d807cbb040f88a84c1c9c3f1b87cfb8c5dac1180.
  Both have tree ee0d96234546f7f0e6c15e114c9e3b10f6e37a4d. API publication
  preserves published integration and original documents as parents. CLI push
  failed with `could not read Username ... Device not configured`; the connected
  GitHub account can publish. Local histories were not reset or force-pushed.

The handoff commit changes documentation only. Independent review must identify
its actual published head. Neither this self-review nor the original documents
review approves the new shared changes. Member 4 is the assigned integration
reviewer; member 5 must recheck the corrected documents scope at the new head.

## Production registrations and safety boundaries

All six document shells are removed. app.documents.routes.router is registered
under /api/v1 with require_access. Content remains binary with the frozen OpenAPI
metadata, no-store/nosniff/sandbox and a UUID-only disposition. No schema, generated
client, reference CSV bytes or fixture hash was changed.

build_registry registers process_document exactly once for document.process.
The existing durable queue, fresh handler sessions, 60-second leases, fencing,
backoff and lifetime document retry cap remain. The polling loop invokes
reconcile_interrupted in its own fresh session. Recovery locks up to 50 documents,
invalidates the processing token, commits failure and logs original job/request
correlation, attempt and sweep duration. Repeat recovery emits no duplicate event.

Alembic discovers backend/app/documents/migrations and imports document models.
Original 0101_documents still depends on 0001_platform. New merge revision
0503_documents_assembly joins 0101_documents and 0502_profiles_assembly. Published
migrations are unchanged. The profiles auxiliary migration config includes all
present locations so its owned migration checks also run on the assembled tree.

Runtime dependencies are locked: pypdfium2 5.14.0, Pillow 13.0.0, openpyxl 3.1.5,
defusedxml 0.7.1. Development fixture dependency: pypdf 6.21.4. Fresh worktree
installation used a newly created .venv and npm ci; no ad-hoc parser pip install.
The Linux runtime image installs from uv.lock with --locked --no-dev.

UploadBodyLimit bounds the entire raw stream before multipart parsing: configured
max_batch_bytes plus 1 MiB framing overhead. Both Content-Length and actual bytes
are checked; chunked or misdeclared bodies cannot evade it. Only bounded raw bytes
are temporarily buffered; multipart parsing starts after the size is accepted.
413 responses use the safe shared envelope. Per-file/batch content checks remain.

Linux is the supported production storage runtime; macOS POSIX development is
verified. Native Windows fails explicitly with STORAGE_UNAVAILABLE and must use
Linux containers. O_NOFOLLOW is never replaced with zero in production or the
assembled test harness. Linux verified 0700 directories, 0600 files, no overwrite,
UUID traversal rejection and no symlink following. Windows reparse/ACL behavior
is NOT VERIFIED because native Windows storage is unsupported.

Orphan cleanup: `uv run python -m app.documents.cleanup`. Run only after every
intake process uses this assembly. It considers UUID originals older than one hour,
tries the same transaction-scoped negative advisory lock as intake, and deletes
only when no committed document exists. Locked active uploads, accepted originals,
symlinks and non-UUID files survive. Concurrency regression tests verify this.
Dot-prefixed interrupted staging files are deliberately excluded.

Portability: test subprocesses use sys.executable; Playwright selects Scripts or
bin paths and uses env objects instead of shell assignments. .gitattributes keeps
source LF and CSV byte-exact; Prettier explicitly uses LF. Native Windows checks
were not run. The macOS parser guard and regression tests come from af2765e.

## Configuration and providers

Compose env_file forwards all DOCUMENT_* values to both API and worker. Every
implemented setting is listed in .env.example. The image includes /usr/bin/tesseract
and slk/eng language data. OCR capability delegates to ocr_configured(). Default
DOCUMENT_OCR_PROVIDER=disabled; executable remains unset. Explicit opt-in uses
DOCUMENT_OCR_PROVIDER=tesseract and DOCUMENT_OCR_EXECUTABLE=/usr/bin/tesseract.
No invented eGrant OCR endpoint or live-mode fixture text exists.

Host default smoke: exit 2, OCR_UNAVAILABLE. A separate Linux command explicitly
enabled Tesseract for one generated synthetic PNG: PASS, one page/unit, expected
synthetic text recognized. This is real local OCR, not a mocked provider. It does
not verify Slovak accuracy, poor scans, real applicant documents or eGrant OCR.
Regular containers remain capability=false. No paid provider or external write ran.

## Executed verification

Worktree: /private/tmp/egrant-documents-integration. Python 3.12.6, PostgreSQL 16,
Node 26.5.0; container frontend Node 22. Dedicated DBs only; no demo DB reset.
UV=/Users/Andrew/Documents/ChatGPT/FUTURE-MAKERS/future-makers-egrant/.tools/bin/uv.
UV_CACHE_DIR=/private/tmp/egrant-integration-uv. Test PostgreSQL localhost:55435,
user egrant, password local-test-only (test-only container).

| Command / scenario | Actual outcome |
| --- | --- |
| uv lock; uv sync --locked in new worktree/.venv; npm ci --prefix frontend | Exit 0; requested parsers installed from locks |
| make check with UV above | Exit 0; locks, Ruff, format, tracked-secret scan, OpenAPI/client drift, TypeScript, Vite |
| make test, TEST_DATABASE_URL ending egrant_test_documents_integration | Exit 0; 196 backend passed, 1 Windows-only case skipped; 32 frontend passed |
| pytest tests/documents/test_parse_worker.py -q | Exit 0; 2 passed |
| make e2e with TEST_DATABASE_URL ending egrant_test_documents_profiles | Exit 0; 3 passed |
| make e2e-integration with INTEGRATION_E2E_DATABASE_URL ending egrant_test_e2e_documents_submissions | Exit 0; 4 passed; neighboring review/extraction reads are explicit doubles |
| make e2e-profiles with TEST_DATABASE_URL ending egrant_test_documents_profiles | Exit 0; 2 UI-adapter scenarios plus 1 actual profiles API/PostgreSQL scenario |
| make e2e-documents with DOCUMENT_E2E_DATABASE_URL ending egrant_test_documents_e2e | Exit 0; 2 passed; real production document registration, explicit neighboring fixtures |
| DB_PORT=55439 docker compose -p egrant-documents-assembly up --build -d | Exit 0; empty volumes, API/DB healthy, worker/frontend running; one 0503 head |
| .venv/bin/python /private/tmp/egrant-compose-document-probe.py | Exit 0; ordinary API upload -> polling worker -> ready -> private content; ready retry 409 |
| Linux PrivateStorage probe via compose exec | Exit 0; permissions, immutable original, traversal and symlink rejection |
| Separate compose exec with DOCUMENT_OCR_PROVIDER=tesseract and executable=/usr/bin/tesseract, synthetic .private/browser-sample.png | Exit 0; real OCR, one page/unit, expected synthetic text |
| Actual Compose UI with Chromium at 375 and 1440 pixels | Viewed screenshots; one masthead, no horizontal overflow, fixture banner and OCR-disabled state visible |
| git diff --check | Exit 0 |

Backend coverage includes private access, duplicate concurrency, immutable ready
sources, late-worker fencing, retry budgets, restart/exhausted-crash recovery,
original recovery correlation, safe 413s before downstream parsing, invalid formats,
DB migrations, cleanup/active-upload locks and log redaction. The initial run
failed on macOS parser setup and outdated assembled test assumptions. These were
fixed; no failed initial run is counted as a pass. Browser foundation/profile
expectations were updated from unavailable document shells to the connected list.
Remaining warnings: Starlette/httpx deprecation, terminal color configuration and
optional fsevents script notice. No failing warning was hidden.

Final logs are /private/tmp/documents-check-final.log and
/private/tmp/documents-test-final.log. Browser logs:
/private/tmp/documents-browser.log, documents-foundation-browser-final.log,
documents-submissions-browser.log and documents-profiles-browser-final.log.
Actual Compose screenshots are .private/production-desktop.png,
production-mobile-top.png and production-mobile-list.png. Browser fixture
screenshots are not presented as proof of real extraction.

## Extraction compatibility blocker and remaining review

An isolated probe exported the existing extraction/validation code at f21eb84
without merging unreviewed owner code into the delivery branch. It used real
profiles and documents public services, uploaded unchanged synthetic-invoice.csv,
processed its actual 23 CSV cell units, then created and processed an extraction
through the existing public extraction functions. Outcome: durable failed
FIXTURE_NOT_AVAILABLE. No document/profile public read was stubbed. The probe
created only the extraction table in its own egrant_test_documents_extraction_probe
DB; this is an interface probe, not an extraction migration/production-registration
acceptance test.

Reproduction script: /private/tmp/egrant-documents-extraction-probe.py; exported
owner source: /private/tmp/egrant-extraction-compat-source; result log:
/private/tmp/documents-extraction-probe.log. Command:

```sh
DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_documents_extraction_probe FILE_STORAGE_PATH=/private/tmp/egrant-documents-probe-files .venv/bin/python /private/tmp/egrant-documents-extraction-probe.py
```

Member 2 must reconcile FixtureProvider's unit-ID fingerprint and recorded
row-based evidence with actual document-specific UUIDv5 cell units, preserving
real IDs, exact quotes and coordinates. The same bytes on a second upload have
different unit IDs, so simply recording one uploaded UUID is insufficient. Do not
change the CSV hash/bytes, return the old normalized example from documents, or
silently use fixture replies in live mode. This owner coordination is recorded
in contracts/internal.md. Live AI cannot substitute for an unavailable explicit
fixture without configured access and separate verification.

Extraction's exact-head independent review, registration and successful actual
fixture consumption remain pending; review registration/confirmation/export with
real owner modules also remains pending. Separate document extraction links pass
with explicit browser fixtures. No full successful document-to-confirmed-export
claim is made. Member 4 must independently review the actual new integration head;
member 5 must recheck corrected documents there. Member 1 performs the eventual
assembled main release review. No original CHANGES REQUIRED verdict was relabeled.
