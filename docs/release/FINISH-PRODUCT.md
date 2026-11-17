# Assembled prototype verification

The full file-to-confirmed-JSON workflow passes in fixture mode. The production
API and worker parse a real uploaded copy of the shared synthetic CSV; only the
AI response is recorded. The browser test edits scalar and table values, saves
and reloads the draft, explicitly confirms it, and verifies the downloaded JSON.

This branch continues PR #13 at `b8870f3` and incorporates existing extraction
and human-review fixes. It registers both previously unavailable routers and
the extraction worker and terminal recovery. Alembic's new merge revision
`0504_full_assembly` combines the three previous heads without rewriting them.
OpenAPI and generated frontend types are unchanged.

CSV fixture recognition now hashes the complete ordered cell locations and
text plus the profile shape. Evidence binds to the actual uploaded cells on
every matching upload. Unrelated inputs fail, and live mode cannot substitute
a fixture. Review now waits for the extraction job, permits retry on failure,
and rejects unsupported currencies in draft values and table cells. Extraction
option scopes no longer collide, and valid keys keep their original whitespace.

## Checks run locally

- `make check`: locked dependencies, source formatting, tracked-secret scan,
  OpenAPI/client generation, TypeScript and frontend build passed.
- PostgreSQL 16 backend suite: 403 passed, two skipped (native Windows storage
  and the opt-in live OpenAI test).
- Frontend component suite: 42 passed.
- Chromium: 16 passed across foundation, submission/history, profiles,
  documents, review and full-product suites. The full-product test uses real
  neighboring modules; the smaller boundary suites use explicit test adapters.
- Clean Docker Compose build/start: PostgreSQL, API, frontend and worker started;
  empty database reached `0504_full_assembly`.
- Tesseract recognized the expected sample number from an opt-in synthetic PNG
  inside the Linux container. Default OCR remains disabled.

The self-review covered the final source diff, storage and access boundaries,
migration graph, recovery, provenance and confirmed export. This is not an
independent approval of the assembled branch.

## Limits

This pass did not call live OpenAI: a fresh authorized key and permitted input
are needed for live verification. The illustrative importer was not validated
against actual eGrant form exports. External eGrant writes remain disabled;
JSON is the delivery output. Neither synthetic OCR nor recorded extraction
establishes accuracy on applicant documents.
