# Independent review: human review module, PR 3

Verdict for the submitted head: **CHANGES REQUIRED**.

- PR: <https://github.com/andr1chkol/future-makers-egrant/pull/3>
- Author: member 4; independent reviewer: member 3, fresh review context.
- Reviewed head: `133e6ced9cbce21fb255fa77b45d3d335c47ec75`.
- Base and merge base: `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
- Recorded `BASE_BRANCH=main`; `bootstrap-v1` resolves to that base.
- Isolated branch: `review/human-review-133e6ce`.
- Safe fix, separately tested: `35b04707861657a9b79c92f758291bcd6a03c600`.

The original verdict is not upgraded by the fix commit. Currency validation
remains unresolved on the corrected review branch. Member 4 should adopt the
timestamp fix and address the validation finding before requesting review of a
new exact head. This review does not approve later integration changes.

## Findings

### P2: repeated confirmation changes its wire timestamp outside a UTC database session

Location at the submitted head: `backend/app/reviews/service.py:25-31`.
`as_review` returns `record.confirmed_at` without normalizing it. PostgreSQL
returns a `timestamptz` in the session timezone. The first confirmation constructs
a UTC datetime; subsequent requests read a session-local datetime from storage.

On the review database, the first HTTP response contained
`2026-10-30T19:45:53.647485Z`; repeating the current confirmed revision returned
`2026-10-30T20:45:53.647485+01:00`. The instant is unchanged, but the UTC wire
contract and identical repeated-confirmation result do not hold. The author's
existing `tests/reviews/test_routes.py:30` failed independently on rerun.

Reproduction at the submitted head:

```sh
TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_pr3_review \
  .venv/bin/pytest tests/reviews/test_routes.py -vv --tb=long
```

Actual result: exit 1, one failure at the repeated-response equality assertion.
The database session used `Europe/Bratislava`.

Fixed on the review branch by normalizing the outgoing timestamp with
`astimezone(UTC)`. The new
`test_confirmed_wire_result_stays_identical_in_non_utc_database_session` sets
`Europe/Bratislava` explicitly and checks first confirmation, repeat, reload and
the public confirmed-review consumer. It fails against the original serializer
with a 3600-second offset and passes with the fix. It restores the connection's
timezone after execution. No shared database setting was changed.

### P2: human corrections can confirm a currency outside the ISO code set

Location at the submitted head: `backend/app/reviews/validation.py:53-67`, used
by `backend/app/reviews/service.py:148-163` during confirmation.

The validator delegates money checking to `ExtractedField`. Shared `Money`
currently enforces only `[A-Z]{3}` in `backend/app/platform/contracts.py:22-24`.
A corrected value `{amount: "99.90", currency: "ZZZ"}` can therefore be saved,
confirmed and consumed as final data. The contract requires an ISO currency code.
Extraction-side provider validation cannot protect a later human correction.

Reproduced with the real review service and PostgreSQL using this temporary test
under `tests/reviews/test_currency_probe.py`:

```python
from app.platform.contracts import ConfirmReview, SaveReview
from app.reviews import service


def test_non_iso_human_currency_can_be_confirmed(
    review_database, review_context, corrected_snapshot
):
    extraction_id = review_context[0].id
    with review_database() as session:
        service.get_review(session, extraction_id)
    corrected_snapshot["fields"][5]["value"] = {
        "amount": "99.90", "currency": "ZZZ"
    }
    with review_database() as session:
        service.save_review(
            session, extraction_id,
            SaveReview(expectedRevision=0, **corrected_snapshot)
        )
    with review_database() as session:
        review = service.confirm_review(
            session, extraction_id, ConfirmReview(expectedRevision=1)
        )
    assert review.status == "confirmed"
    assert review.fields[5].value.currency == "ZZZ"
```

```sh
TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_pr3_review \
  .venv/bin/pytest tests/reviews/test_currency_probe.py -q
```

Actual result: exit 0, one successful defect probe confirming the invalid value.
The temporary probe was removed afterward; it is not a passing validation test.
The code above makes it reproducible without private inputs.

Requested action: member 4 and member 5 should agree on a reusable supported ISO
currency validator, apply it to scalar and table human corrections, and add
regressions for unknown codes and valid codes. Return a safe 422 without values
in errors or logs. No dependency, frozen DTO or other owner's validator was
silently changed during this review.

## Verified behavior and boundaries

The actual diff and surrounding contracts, access gate, session lifecycle,
logger, migrations, generated client and call sites were inspected. The bundled
human-code and final-review skills were applied; humanizer was restricted to
technical report prose. No backend-reliability-review skill was available.

PostgreSQL tests verify concurrent initialization, one winner for competing
draft writes and confirmation, stale-write conflicts, current-revision
confirmation retries, immutable confirmed data, revision history, draft reload,
stable UUID rows, addition/deletion, exact keys/cells, dates, decimals, money
shape, options, required values, warning acknowledgement and frozen context.
The public confirmed-review consumer returns human corrections and leaves its
caller's transaction active. Missing required values can be saved as a draft;
confirmation rejects them. There is no external call inside a review transaction.

HTTP tests exercise the real review router, origin checking and access gate.
Captured logs verify event names, levels, extraction ID, correlation, safe
conflict codes and omission of corrected person/IBAN/token-like text. Revision
exists in raw log context but is absent from formatted stdout because the shared
logger allowlist omits it. That existing integration request remains mandatory.

Frontend tests and Chromium exercise correction, row operations, source
navigation, save/reload, stale conflicts with local edits retained, explicit
summary/confirmation, read-only confirmed controls and corrected JSON export.
Component tests cover visible failure/retry, PDF links/sandbox, image failure, export retry keys,
apply consent, persisted original intent, unknown results and disabled replace.
The UI sends no arbitrary destination tags. Apply controls appear only for a
confirmed revision and configured capabilities. Desktop and 375px screenshots
were inspected; the source/editor layout and horizontally scrolling table are
usable. Browser assertions also check no page overflow at 200% text.

The review initialization rejects an option value outside the pinned set. This
was probed but is not reported as a general review defect: the separately checked
extraction implementation converts ordinary rejected options to null/missing with
a warning before review. The integration coordinator has separate extraction
concerns about whitespace in option keys and empty option lists. Those cases need
cross-module tests; this review does not certify their assembled behavior.

## Executed commands and results

Environment: macOS; Python 3.12.16; uv 0.13.6; Node 22.23.4; PostgreSQL 16.
Dependencies were installed from the unchanged locks into this worktree's own
`.venv` and `frontend/node_modules`. Tests used only the dedicated
`egrant_test_pr3_review` database at `127.0.0.1:55432`. Database-reset suites must
run sequentially against that database.

```sh
/private/tmp/egrant-profiles-tools/bin/uv sync --locked
PATH=/private/tmp/node-v22.23.4-darwin-arm64/bin:$PATH npm ci --prefix frontend
PATH=/private/tmp/node-v22.23.4-darwin-arm64/bin:$PATH \
  make check UV=/private/tmp/egrant-profiles-tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_pr3_review \
  .venv/bin/pytest
PATH=/private/tmp/node-v22.23.4-darwin-arm64/bin:$PATH npm test --prefix frontend
cd frontend
PATH=/private/tmp/node-v22.23.4-darwin-arm64/bin:$PATH \
  TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_pr3_review \
  npx playwright test --config src/features/review/playwright.config.ts
```

- Locked installs: exit 0.
- Exact submitted head `make check`: exit 0. Locks, Ruff, formatting, secret
  scan, contract generation/drift, strict TypeScript and frontend build passed.
  The committed schema and generated client remained unchanged.
- Exact submitted head backend suite: exit 1; 54 passed, one failed, due to the
  confirmation timestamp finding. Isolated HTTP rerun reproduced it.
- Exact submitted head frontend suite: exit 0; 11 passed.
- Exact submitted head dedicated Chromium suite: exit 0; three passed. It uses
  the real review router, migration and PostgreSQL, with explicit test-only
  neighboring adapters. It is not the assembled provider workflow.
- Corrected source `35b0470`: focused timestamp/HTTP tests exited 0, two passed;
  full `.venv/bin/pytest -q` with the same database exited 0, 56 passed.
- Corrected source: `.venv/bin/ruff check backend/app/reviews tests/reviews`,
  `.venv/bin/ruff format --check backend/app/reviews tests/reviews`, and
  `git diff --check` all exited 0. The new regression also failed as expected
  when run with the original serializer substituted in memory.
- The 17 shared contract tests passed in the full suites, including root/team
  contract equality, exact committed OpenAPI equality, example/schema validation
  and protected domain routes. They exercise the standalone baseline application;
  they do not establish schema equality after later router assembly.

Non-failing warnings: Starlette/httpx deprecation, Alembic legacy path-separator
deprecations and Node terminal-color warnings. The first backend suite and browser
suite overlapped in wall time; the failing HTTP test was rerun alone, and the
complete corrected backend suite ran after browser shutdown. Its result does not
depend on concurrent access to the reset database.

## Required integration and unverified scenarios

Member 5 still needs the handoff's review-router replacement, migration discovery
and metadata registration, formatted log revision allowlist, and E2E wiring.
Standalone production startup still exposes the unavailable shell routes; no
assembly success is claimed. The migration itself was applied by module tests.
JSON export used a test consumer of the real `get_confirmed_review`, not the
future production integration implementation.

Live OCR, AI and eGrant, real form exports, native PDF rendering, real image/XLSX
document-module integration, full screen-reader testing and authorized external
writes remain unverified. No secrets or `.env` files were copied. No author branch
was overwritten, no PR was merged, and no GitHub approval or review was posted.
