# Member 4 handoff: human review and confirmation

Repository: <https://github.com/andr1chkol/future-makers-egrant>.
Branch: `codex/review`. Target: `main`.
Verified `bootstrap-v1`: `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
Self-reviewed published code commit: `d715955254fb0b7da6e026a940c1ed5bfed73fc7`.
Its tree `98af8b32b4c32624a8c9bdbf9bf6190d38341bac` exactly matches the
locally tested code commit `011b7b7f7c66782fd86158af737c01e66ba0f92f`.
This handoff is a documentation-only follow-up to that tested code commit.
The final PR description identifies the complete head for independent review.

Self-review result for the code SHA above: **ready for independent module
review**, with the shared integration requests below still outstanding.
The assembled application is **NOT READY** on this branch: the baseline's
review shells and default migration discovery remain unchanged by ownership.
Independent reviewer: member 3, GitHub `dimaua12`, using a fresh chat and
`docs/team/06-PEER-REVIEW.md`. Author self-review does not replace peer review.

## Delivered behavior

The review module initializes a separate draft only from a ready extraction.
It freezes the extraction, exact profile version and form definition alongside
the editable snapshot. Every saved/confirmed revision is retained in a separate
audit table. It never changes the original extraction or reads other modules'
private tables.

PUT replaces the complete snapshot under a PostgreSQL row lock. Every write
compares `expectedRevision`; stale writes return 409. Validation rejects unknown
or duplicate keys, incomplete cell structures, duplicate row UUIDs, invalid
shared value types, invalid option keys and unknown warning acknowledgements.
Drafts may contain missing required values. Confirmation additionally requires
required values and acknowledgement of the exact frozen warning set. A confirmed
review is immutable. Repeating confirmation with its current confirmed revision
returns the same result; repeating the old pre-confirmation revision returns 409.

The generic Slovak `ReviewPage` uses the generated client, shared QueryClient,
Button/Notice controls and document-desk visual conventions. It provides original
AI values, human-change indicators, issue filtering, scalar/money/date/boolean
and option editors, stable UUID table rows, add/delete/edit, server-side draft
reload, explicit conflict comparison and a final confirmation summary.
Refetch never replaces local edits. Successful saves update the query cache;
initial remount waits for a fresh read. Unsaved SPA-navigation drafts stay in tab
memory; a full reload warns before discarding unsaved edits. Only explicitly
saved drafts are durable across a full reload.

Sources are read through the protected document endpoints. Spreadsheet text is
escaped, with real sheet/cell context; formulas/macros are not executed. Quotes
must occur in the referenced normalized unit. PDF links use supported normalized
page numbers; the iframe is sandboxed. Images have a visible failure/retry state.
No fabricated bounding boxes or coordinate highlights are drawn.

Submission controls appear after confirmation. They send only review identity,
revision, mode, target context and overwrite acknowledgement to the shared
submission endpoint. Destination tags and payload values come from the server.
JSON download is separate from apply. Apply requires capabilities, a target and
explicit consent. Its intent/key is stored before POST and survives reload;
unresolved intents keep their original target and key. Known submission IDs use
GET for status checks. Failed/unknown outcomes do not create another insertion.
External replace remains disabled because the frozen API has no safe current-
target preview interface. No new dependency or frozen-contract edit was made.

## Public interfaces and migration

Import DTOs from `app.platform.contracts`. Service functions are synchronous:

```python
from app.reviews.service import (
    get_review, save_review, confirm_review, get_confirmed_review,
)

get_review(session: Session, extraction_id: UUID) -> Review
save_review(session: Session, extraction_id: UUID, request: SaveReview) -> Review
confirm_review(session: Session, extraction_id: UUID, request: ConfirmReview) -> Review
get_confirmed_review(session: Session, id: UUID, revision: int) -> Review
```

The first three functions require a fresh Session and own their short atomic
transaction. `get_confirmed_review` only reads, never commits, and can share the
integration caller's transaction. Missing resources raise NotFoundError; stale,
not-ready or unconfirmed state raises ConflictError. Invalid snapshots return
safe 422 DomainErrors without echoing input values. Missing upstream modules
return UnavailableError, never synthetic success.

Upstream reads use exactly `app.extraction.service.get_extraction`,
`app.profiles.service.get_profile(session, id, version)` and
`app.profiles.service.get_form`. Frontend export remains
`frontend/src/features/review/index.ts: ReviewPage`, without props, using the
existing `/review/:extractionId` route. No worker handler is required.

Migration: `backend/app/reviews/migrations/0401_reviews.py`, parent
`0001_platform`, branch label `reviews`. Tables: `reviews`, `review_revisions`.
The migration stays inside member 4's ownership. Module tests register its
location explicitly and upgrade from the platform migration on PostgreSQL 16.
Do not rewrite it after publication; member 5 reconciles module heads.

## Required shared integration changes: member 5

1. Remove the three matching unavailable review route declarations from
   `app.platform.routes`, then include `app.reviews.routes.router` in
   `app.main.create_app` under `/api/v1` with the existing access gate. The new
   router also declares the gate, so direct inclusion remains protected.
   Leaving both routes registered risks the old 503 shells winning dispatch.
2. Register `backend/app/reviews/migrations` alongside
   `backend/migrations/versions` in Alembic version discovery, import review
   models for metadata/autogeneration, and reconcile heads after other modules
   land. Current default `make migrate` deliberately does not discover this
   owned migration. Module tests perform the actual migration, not create_all.
3. Add `revision` to `NUMBER_KEYS` in `app.platform.logging`. The module emits
   `revision` in every review LogRecord context, but the bootstrap formatter
   drops it from stdout. Tests verify raw revision context, formatted event/ID/
   level/correlation/redaction separately. **Formatted JSON revision output is
   blocked until this shared change; it is not claimed as passing.**
4. Add the dedicated review browser command below to shared CI/E2E orchestration.
   Default `make e2e` still runs the three foundation tests. Assemble the real
   document/profile/extraction/submission APIs before calling the complete
   application workflow verified. No runtime fixture adapter should be imported.

These are explicit integration requests, not silent edits to shared files.
No shared lock, DTO, generated client, main router or platform logger was changed.

## Executed verification

Environment: Python 3.12.6, uv 0.13.6, Node 22.23.4, isolated PostgreSQL 16.
Locked dependencies were reused from the verified foundation install. All final
commands below exited 0. The scan covered all 116 staged/tracked code files;
the handoff was scanned again before its commit.

```sh
npm exec --yes --package=node@22 -- sh -c 'make check UV=/private/tmp/egrant-peer-review-tools-70370b3/bin/uv'
npm exec --yes --package=node@22 -- sh -c 'TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55434/egrant_test_peer make test UV=/private/tmp/egrant-peer-review-tools-70370b3/bin/uv'
npm exec --yes --package=node@22 -- sh -c 'make e2e'
cd frontend
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55434/egrant_test_peer npx playwright test --config src/features/review/playwright.config.ts
```

The last command ran under the same Node 22 npm-exec wrapper. Replace the local
uv path with your installed uv. `TEST_DATABASE_URL` must name an isolated
`egrant_test*` PostgreSQL 16 database; tests reset it. Never point tests at data
you need to retain. The original root PostgreSQL fixture remains unchanged.

- `make check`: lock validation, Ruff, formatting, credential pattern scan,
  generated OpenAPI/client drift, strict TypeScript and Vite build passed.
- `make test`: **55 backend tests passed** (32 foundation, 23 review) and
  **11 frontend tests passed** (one foundation, ten review/source tests).
- `make e2e`: **three foundation Chromium tests passed**.
- Dedicated review E2E: **three Chromium tests passed** with real review API,
  migration and PostgreSQL; neighboring services are explicit test-only adapters.
  They cover correction/row creation, source navigation, save/reload, explicit
  confirmation, corrected values in the exported payload, stale revision
  preservation, keyboard/filter behavior, mobile and 200% text layout.
- PostgreSQL cases include concurrent initialization, two competing draft PUTs,
  concurrent confirmation, repeat/stale confirmation, immutable confirmed data,
  audit history, invalid values/options/keys/rows, warning identity, redaction
  and the public confirmed-review consumer.

Non-failing warnings: existing Starlette/httpx deprecation, Alembic's legacy path
separator deprecation and terminal color warnings. Early tests found a stale
cache remount, an empty-table mapping gap and screen-reader labels escaping the
table scroller at 200% text. Those were fixed and covered before the final run.
Duplicate warning identities now collapse consistently with the server.

## Manual fixture reproduction and limits

The dedicated browser command starts the real review API with
`tests/reviews/browser_server.py` and the normal frontend, then stops them.
For a manual session use that test server on 8012 with
`PYTHONPATH=backend:tests/reviews`, the isolated `TEST_DATABASE_URL`,
`APP_MODE=fixture`, `DEV_AUTH_BYPASS=true`, `COOKIE_SECURE=false` and
`PUBLIC_ORIGIN=http://localhost:5174`; point frontend `API_PROXY_TARGET` to
`http://127.0.0.1:8012` and start Vite on 5174.

Open `/review/00000000-0000-4000-8000-000000000004`. Inspect a source, change a
supplier/money/date value, add/delete a row, acknowledge the warning and save.
Reload and compare values. Open the final summary and explicitly confirm.
Export JSON and compare human values and rows. A second tab's stale PUT must
return 409 while preserving its local edits. The confirmed editor is read-only,
but evidence navigation remains available.

The adapter is test-only and visibly fixture mode. Its export consumer calls
the real `get_confirmed_review`; it does not establish member 5's implementation
or an external eGrant write. Production imports never reference it. Provider
matrix: fixture test adapters verified; live OCR/AI/eGrant unavailable and
unverified. Native PDF rendering, real images/XLSX from the documents module,
screen-reader sessions and authorized external writes remain unverified.
PDF page-link/sandbox and image-failure behavior have component coverage.

An unconfigured assembled baseline still returns visible 503 errors until the
shared registrations and neighboring modules land. No external credentials were
required for independent work. No application write, automatic merge or tag
publication was performed. Member 3 must review the exact PR head independently.

Publication used the connected GitHub tools after local HTTPS Git credentials
returned HTTP 403. Published code was checked against the exact tested Git tree;
local implementation commits were retained separately. No shared history was
rewritten. The active `codex/review` branch follows the published commits.
