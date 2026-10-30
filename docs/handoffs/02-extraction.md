# Handoff 02: extraction, evidence and validation

Owner: member 2. Branch: `codex/extraction`, from `bootstrap-v1`
(`88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`). BASE_BRANCH: `main`.
Independent reviewer: member 1, using `docs/team/06-PEER-REVIEW.md`.

## What the module does

Given a ready normalized document and a frozen profile version, the extractor
asks a provider for the profile's fields and tables, then validates the reply in
code. The result is a contract `Extraction` with typed values, verified
`SourceRef`s, per-value status and warnings. Nothing in the extractor refers to
invoice fields or form tags. A different profile is just a different schema; the
tests run invoice, receipt, bank-statement and contract profiles through the same code.

How a reply turns into values:

1. The provider gets a JSON Schema built from the profile (strict structured
   output). Each value comes back exactly as printed, with `{unitId, quote}` evidence.
2. The parser rejects anything outside that schema: missing or extra keys,
   wrong types, unbounded lists (`AI_OUTPUT_INVALID`).
3. `app.validation.values` reads numbers and dates deterministically. Ambiguous
   readings (`1,234`, `03/04/2026`) and unreadable text (`2l1,3O`) become `null` with a
   warning. They are not guessed or corrected. A minus directly before or after the
   number (`-12,50`, `12,50-`) or enclosing parentheses (`(12,50)`) make it negative;
   detached or conflicting signs (`- 12,50`, `(-12,50)`) make it unreadable.
4. Evidence: unknown unit IDs are dropped (`SOURCE_UNIT_UNKNOWN`). A quote must
   occur in its unit's text after whitespace is collapsed, otherwise it is dropped
   and the unit kept (`QUOTE_NOT_IN_SOURCE`). The printed value must occur in the quote,
   otherwise `VALUE_NOT_IN_EVIDENCE`. A value that starts or ends with a digit must not
   continue a longer number there: `234,50` is not supported by `1.234,50`.
   Page, sheet and cell always come from the unit.
5. Domain rules: required/optional missing, option keys, ISO 4217 currency
   present and mentioned in the document, currency consistency, and arithmetic
   (see below). A failed check sets `needs_review` and adds a warning. Values are never rewritten.

Status rules: `null` means `missing`. A value with any warning means `needs_review`.
Everything else is `found`.

### Arithmetic checks and tolerance

Profiles have no semantic roles in contract v1, so `app/validation/rules.py`
recognizes conventional keys (`quantity`, `unit_price`, `line_total`/`amount`,
`net_total`/`subtotal`, `vat_total`/`tax_total`, `total`/`gross_total`,
`opening_balance`, `closing_balance`). Profiles that use other keys still extract
normally and simply skip these checks.

- Line: `quantity × unit_price` against `line_total`. Tolerance is half a printed
  digit of the unit price times the quantity, plus half a digit of the line total.
- Lines against total: compared with the net total, or with the gross total when
  no tax amount was extracted. Tolerance is half a digit per line plus half a
  digit of the target.
- Net + tax against gross, and opening balance + transactions against closing
  balance: the half-digit tolerances of the operands added together.

Codes: `LINE_TOTAL_MISMATCH`, `DOCUMENT_TOTAL_MISMATCH`, `TAX_TOTAL_MISMATCH`,
`BALANCE_MISMATCH`, `CURRENCY_INCONSISTENT`. Calculated values are never stored.

## Interfaces

```python
# app.extraction.service  (all synchronous; Session = sqlalchemy.orm.Session)
create_extractions(session, request: CreateExtractions) -> ExtractionBatch
get_extraction(session, id: UUID) -> Extraction
list_extractions(session, limit: int, offset: int) -> tuple[list[Extraction], int]
retry_extraction(session, id: UUID) -> Extraction
process_extraction(session, id: UUID, provider: ExtractionProvider | None = None) -> None
```

- `create_extractions` owns its transaction. It reads the profile via
  `app.profiles.service.get_profile`, the form's option keys via `get_form`, and
  each document via `app.documents.service.get_normalized`. It then creates one
  queued extraction and one `extraction.process` job per document.
  Errors: duplicate IDs → 422 `VALIDATION_ERROR`; unknown profile, version or
  document → 404; document not ready → 409; live mode without `OPENAI_API_KEY`
  and `OPENAI_MODEL` → 503 `AI_NOT_CONFIGURED`.
- `retry_extraction` accepts failed runs and stale runs: `queued` or `running` and not
  updated for `STALE_AFTER` (5 minutes, longer than three 60-second leases plus backoff).
  Anything else is 409. It keeps the same ID, resets `attempt` and `run_token`, and
  enqueues a new job. None of these runs had a result, so no review can exist for it.
- `process_extraction` is the job handler. The other modules are imported at call
  time (`service.load_normalized/load_profile/load_form`), so this branch works
  before they are merged and tests can replace them.

Routes are in `app.extraction.routes.router`, relative to `/api/v1`:
`POST /extractions` (202), `GET /extractions`, `GET /extractions/{id}`,
`POST /extractions/{id}/retries` (202). Their request bodies, parameters and
response schemas are tested against the frozen `contracts/api.yaml`.

## Requests for member 5 (shared files I did not touch)

1. **Router:** remove the four extraction shells from `app/platform/routes.py`
   and include `app.extraction.routes.router` in `create_app` with
   `Depends(require_access)`. FastAPI 0.162 includes routers as one
   `_IncludedRouter`, so shells cannot be filtered out afterwards. In tests I mount
   the router in front of the shells (`tests/extraction/test_lifecycle.py::assembled_app`).
2. **Worker:** in `app.worker.build_registry`, register
   `registry.register_handler("extraction.process", process_extraction)`
   from `app.extraction.service`.
3. **Migrations:** `0201_extractions` (down revision `0001_platform`) creates the
   table `extractions`. Alembic `env.py` does not need my models; the migration is
   explicit. **`tests/platform/test_jobs.py::test_migration_and_transactional_enqueue`
   fails on this branch** because it asserts that head is `0001_platform`. The test
   is right for bootstrap, but any module migration breaks it. It needs a member-5
   change, e.g. asserting that `0001_platform` is an ancestor, or the merge revision.
4. **Capabilities:** `aiConfigured` is hardcoded to `false` in `app/main.py`.
   It can be `OpenAIProvider.from_settings(get_settings()) is not None` once the
   router is mounted. The adapter exists, but no live call has been verified (see Limits).
5. **Logging vocabulary:** there is no `extraction.retry_scheduled` event, so
   retries log `job.retry_scheduled` with `extractionId`, `attempt` and the provider
   code (`AI_RATE_LIMITED`, `AI_TIMEOUT`, ...). The platform logs its own generic
   `job.retry_scheduled` with `jobId` right after. Add an event if the duplication is a problem.
6. **No new dependencies.** The OpenAI adapter uses `urllib` from the standard
   library instead of the SDK so that the lockfiles stay untouched.

## Requests for members 1 and 3

- Member 1: fixture mode recognizes the shared example only when
  `get_normalized` returns exactly the unit IDs and texts of
  `contracts/examples/normalized-document.json` for `synthetic-invoice.csv`
  (`row-1` … `row-4`). Different IDs make fixture runs fail with
  `FIXTURE_NOT_AVAILABLE`, which is explicit but blocks the demo flow.
- Member 3: option keys are read from the form by `targetTag` at creation time
  and frozen with the run. Only `string` fields use them.

## Processing, retries and idempotency

The job runs in three phases, and the provider is never called inside a transaction:

1. Short transaction with `SELECT … FOR UPDATE`: skip runs that are already
   `ready`/`failed` (duplicate delivery), otherwise mark `running`, increment
   `attempt` and set a fresh `run_token`.
2. Provider call with a 40-second timeout, inside the 60-second lease that has no
   renewal. Inputs over 200,000 characters fail with `DOCUMENT_TOO_LARGE` before any call.
3. Short transaction that writes the result only
   `WHERE run_token = <mine> AND status = 'running'`. A worker whose lease was
   reclaimed loses the token and discards its result. Tested, including two
   concurrent workers.

Failures: retryable codes (`AI_TIMEOUT`, `AI_RATE_LIMITED`, `AI_UNREACHABLE`,
`AI_UPSTREAM_ERROR`, `AI_OUTPUT_INVALID`, `EXTRACTION_INTERNAL_ERROR`) re-queue
the run and raise `ExtractionRetryScheduled`, so the platform applies its backoff
until attempt 3. The third failure is stored as `failed` and the job completes.
Permanent codes (`AI_AUTH_FAILED`, `AI_REQUEST_REJECTED`, `AI_REFUSED`,
`AI_NOT_CONFIGURED`, `DOCUMENT_TOO_LARGE`, `DOCUMENT_UNAVAILABLE`,
`FIXTURE_NOT_AVAILABLE`) fail immediately. Row IDs are generated once when the
result is stored and are returned unchanged on every read.

## Provider modes

- `fixture`: `FixtureProvider` replays `backend/app/extraction/fixtures/*.json`,
  matched by a fingerprint of the unit IDs/texts and the profile's key/type
  structure. For the shared example it reproduces `contracts/examples/extraction.json`;
  only the warning message wording differs, since messages here are generic per code.
  Any other document fails with `FIXTURE_NOT_AVAILABLE`. A provider whose mode
  differs from the run's mode is refused.
- `live`: `OpenAIProvider` calls `POST https://api.openai.com/v1/responses`
  with `text.format = json_schema, strict: true` and `store: false`. The
  instructions treat document content as untrusted data; the document is sent
  only in the user input. **Verified only with a faked HTTP layer.** No live call
  has been made: no credentials were provided.

## Logs

`extraction.started` (INFO), `extraction.validation_warning` (WARNING, one per
distinct code), `extraction.ready` (INFO, `durationMs`), `extraction.failed`
(ERROR, safe `errorCode`, stack of file/line only), `job.retry_scheduled`
(WARNING). All carry `extractionId`, `documentId`, `attempt` and the propagated
`requestId`. Tests check that document text, amounts and unit IDs never reach
the log, including from the text of an unexpected exception.

## Evaluation

Synthetic documents only, with values checked by hand: `tests/extraction/evaluation/`.
The tuning split (2 cases) and the held-out split (4 cases) share no documents.
Without `--live` the evaluator replays the reply recorded in each case. That
measures this module's parsing, normalization and validation of a given reply,
**not the accuracy of a model.** The held-out replies were written by hand to
contain typical model mistakes.

```sh
cd backend
uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/tuning
uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/heldout
# Paid, needs OPENAI_API_KEY and OPENAI_MODEL:
uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/heldout --live
```

Results of the recorded runs (2026-10-29):

| Split | Cases | Expected values | Correct | Missing | Incorrect | Invented | Flagged |
|---|---|---|---|---|---|---|---|
| tuning | 2 | 32 | 32 | 0 | 0 | 0 | 0 |
| held-out | 4 | 51 | 44 | 3 | 4 | 1 | 3 |

The held-out errors are the planted ones: swapped supplier and buyer (2), wrong
contract type (1), a total taken from an injected instruction (1, caught by the
total check), an invented due date (flagged), and a dropped bank transaction
(3 cells, caught by the balance check). Swapped parties are not detectable in code
when both names are quoted correctly; the evaluator reports them as incorrect.
No live evaluation has been run, so there is no model accuracy figure.

## Verification

Against PostgreSQL 16 (`docker.io/library/postgres:16` under podman) with
`TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test`:

| Command | Result |
|---|---|
| `uv run pytest tests/extraction` | 129 passed, 1 skipped (live test, not enabled) |
| `uv run pytest` | 160 passed, 1 skipped, **1 failed**: `test_migration_and_transactional_enqueue` (request 3) |
| `uv run ruff check backend scripts tests` | passed |
| `uv run ruff format --check backend scripts tests` | passed |
| `uv lock --check` | passed |
| `uv run python scripts/scan_secrets.py` | passed |
| `scripts/export_contract.py` + `git diff contracts/api.yaml` | no drift |

Not run: the frontend half of `make check`, `npm test` and `make e2e` (this branch
has no frontend changes and `npm ci` was not run), and the live provider test.

Manual reproduction without other modules: run the evaluator commands above,
or `uv run pytest tests/extraction/test_lifecycle.py -k worker_produces`.

## Limits and known risks

- **Runs can be left `running` or `queued` without a job; they recover only by a
  manual retry.** If the worker dies during attempt 3, the platform marks the job
  `LEASE_EXHAUSTED` without calling the handler, and the run stays `running`. If a
  claim transaction rolls back (for example a database error while loading the
  document) or the worker dies between claiming the job and claiming the run, the
  job's attempt count runs ahead of the run's; on the job's last attempt the handler
  still raises `ExtractionRetryScheduled`, the platform fails the job, and the run
  stays `queued`. After `STALE_AFTER` both can be retried through
  `POST /extractions/{id}/retries`, and the old job cannot overwrite the new attempt
  (tested). Nothing retries them automatically: a platform failure hook or a periodic
  sweep (member 5) would close the gap without a user action. A run waiting more than
  five minutes in a long job queue also counts as stale; retrying it only adds a
  second job, and whichever finishes second skips the finished run.
- Rate limits use the platform backoff (2 s, 4 s) and ignore `Retry-After`. A
  sustained 429 exhausts the three attempts quickly; the user can retry later.
- If the model returns ISO dates instead of the printed form, the value is
  still read but marked `needs_review` (`VALUE_NOT_IN_EVIDENCE`).
- Space-grouped numbers are not checked for continuation: `600,00` is accepted as
  evidence inside `48 600,00`, because table columns are also separated by single spaces.
- Arithmetic checks depend on the conventional keys listed above. A `role` in the
  profile contract would make this explicit.
- A document over 200,000 characters is rejected rather than split.

## Assembly check against the other branches (2026-10-30)

Run locally, not pushed: `codex/extraction` merged with `origin/codex/profiles`
(`7fe7659`), `origin/codex/review` (`133e6ce`) and `origin/codex/integration`
(`0757638`), plus a temporary merge revision over `0201_extractions`,
`0301_profiles`, `0401_reviews` and `0501_submissions`. The merge had no conflicts.

- `tests/extraction`: all passed on the assembled tree.
- One throwaway end-to-end test ran the real modules: `create_form` and `create_profile`
  from `contracts/examples`, `create_extractions`, `process_extraction` (fixture mode,
  document stubbed with `contracts/examples/normalized-document.json` because no
  documents branch is published yet), `get_review`, `save_review`, `confirm_review`, and
  `create_submission` in export mode. The run was `ready`, the review `confirmed` and the
  submission `prepared`.

Found for member 5 during assembly (not changed here):
- `0301_profiles` and `0401_reviews` live in `backend/app/<module>/migrations`, which
  `backend/alembic.ini` does not list in `version_locations`. Four heads need one merge revision.
- `tests/profiles/test_routes.py` and `tests/reviews/test_routes.py` share a basename,
  so a full `pytest` run stops at collection. Add `__init__.py` packages or rename.
- `tests/integrations/test_submissions.py::test_unavailable_owner_and_egrant_fail_honestly`
  assumes the reviews module is absent and fails once it is merged.
