# Profiles implementation handoff

Repository: https://github.com/andr1chkol/future-makers-egrant.
Branch: `codex/profiles`. Target: `main` (`BASE_BRANCH`).
Verified baseline: `bootstrap-v1`, `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
Reviewed implementation commit: `5b1d3dfcc36005e478a5802a539cfb43530607f8`.
The final handoff commit changes documentation only.

This is the author's implementation handoff. Member 2 must independently review
the final PR head in a fresh chat using `docs/team/06-PEER-REVIEW.md`. Supplemental
agent reviews do not replace that review or approve the assembled release.

## Delivered behavior

Managers import a form, inspect its original JSON, search forms and destinations,
configure scalar/table extraction, save a profile, and create immutable versions.
Historical versions are read-only. The editor exposes keys, labels, descriptions,
types, required flags, destination tags, column mappings and append/replace mode.
It uses shared Button/Notice controls, generated DTOs/client, QueryClient, the
existing router, paper/green styling, Georgia headings and Slovak UI copy.

Editable starters cover invoices, receipts, bank statements and contracts. They
provide category-specific extraction/row instructions, not accuracy evidence.
Generated extraction keys are valid unique identifiers, independent of original
destination tags. Dots/spaces in tags survive; label edits never rename a tag.
Option keys are shown separately from labels and included in starter guidance.
Consumers must validate actual extracted option values against the form.

The trial control submits one ready document and a saved profile ID/version to
shared `POST /extractions`, then navigates to `/review/:extractionId`. Dirty
profiles, unavailable documents, failed capabilities and unavailable live AI
disable trial. Fixture mode and server failures remain visible. There is no
second extraction/review mechanism. The actual extractor is absent at bootstrap.

The UI includes loading/empty/error states, field errors, preserved conflict
drafts, explicit discard, version status and original configuration display.
Chromium back/forward cancellation uses Navigation API. Browsers without that API
retain reload, link, form and version-change guards; full cross-browser history
blocking requires a shared data-router decision.

## Import format and limits

`POST /forms` accepts `{name, definition}`. The supported illustrative definition
has explicit `illustrative: true` or `isIllustrative: true`, fields/tables arrays,
and optional nested sections containing the same arrays. Fields have tag, label,
type, optional boolean required (default false), and optional/null options made
of `{key,label}`. Tables have tag, label and nonempty columns. The supplied whole
`contracts/examples/form.json` also works as definition; the entire supplied
tree, including its nested originalJson, is preserved.

Supported types are string, decimal, date, boolean and money. Scalar/table tags
are unique across a form; column tags are unique within their table. String
options require unique nonblank keys; equal display labels are allowed.
Unsupported types fail explicitly. Unknown presentation/settings keys remain
unchanged in originalJson and visible as text. HTML/script-like text never
becomes executable markup. No real eGrant export adapter is claimed.

Limits: 64 JSON nesting levels and 2 MiB after ASCII-safe JSON serialization.
The UI limits uploaded JSON files to 2 MiB. Nonfinite numbers, NUL and unpaired
surrogates fail before JSONB persistence. Errors contain codes and structural
paths without imported values. Unverified formats fail IMPORT_FORMAT_UNVERIFIED.

Examples in `tests/profiles/examples/`:

- invoice-form.json: reference/total and description/price item rows.
- travel-form.json: traveller/transport option keys and destination/date rows.

They have distinct tags, types, option settings and table mappings. Both use the
same profile API and editor.

## Interfaces, transactions and migration

Public synchronous signatures match `contracts/internal.md`:

```python
from app.profiles.service import get_form, get_profile

get_form(session: Session, id: UUID) -> FormDefinition
get_profile(session: Session, id: UUID, version: int | None = None) -> Profile
```

Reads never commit and raise shared NotFoundError for missing IDs/versions.
Nested original JSON is detached from the SQLAlchemy identity map. Versioned
reads do not follow the latest pointer. Extractions must persist their pinned
version/snapshot at creation. Pinned reads after editing are tested; the actual
member 2 worker's snapshot persistence remains unverified here.

`app.profiles.routes.router` implements the seven frozen operations: POST/GET
forms, GET forms/{id}, POST/GET profiles, GET profiles/{id} with optional version,
and POST profiles/{id}/versions with expectedVersion. The router includes the
shared access dependency. API tests exercise actual middleware/Origin checks,
UUIDs, pagination, shared error envelopes and frozen OpenAPI request/response DTOs.

Writes own `with session.begin()` and require a fresh inactive Session. Version
allocation locks the head before checking expectedVersion. Concurrent saves
produce one success and one ConflictError/409. Historical snapshot rows are
never updated. PostgreSQL triggers reject direct UPDATE/DELETE of imported forms
and version snapshots. Failed saves roll back the latest pointer atomically.

Migration: `0301_profiles`, parent `0001_platform`, branch label `profiles`.
It creates profile_forms, profile_heads, profile_versions, foreign keys, positive
version constraints, the form index, and profiles_reject_snapshot_change triggers.
Upgrade, downgrade and reapplication are tested. Existing revisions are unchanged.

## Required member 5 registrations

1. Remove the seven form/profile shells from app.platform.routes and include
   app.profiles.routes.router under `/api/v1` in app.main.create_app with
   require_access. Appending duplicate paths after shells does not replace them.
2. Register backend/app/profiles/migrations in shared Alembic version_locations,
   or relocate 0301_profiles in the coordinated assembly change. Import
   app.profiles.models for autogeneration metadata. Reconcile module heads using
   a new merge revision; do not rewrite released revisions.
3. Extend app.platform.logging.ID_KEYS with profileId/formId and NUMBER_KEYS
   with version. The module emits profile.created/profile.version_created with
   those fields after commit, but baseline JsonFormatter drops them from JSON
   stdout. Tests verify source context, request correlation and redaction;
   serialized profile/version correlation needs this shared fix and retesting.
4. Add the scoped browser commands below to assembled CI. Integrate document,
   extraction and review modules before claiming a real document trial completes.

No shared router, lockfile, dependency, public contract or generated-client edit
is included. The existing frontend router already imports ProfilesPage and
ProfileEditorPage through features/profiles/index.ts. No frontend registration
change is needed. No background job handler is owned by this module.

## Setup and verification

Used Python 3.12.16, uv 0.13.6, Node 22.23.4, PostgreSQL 16.15 and Chromium 156.
Dependencies come from existing locks. Tests use a real isolated PostgreSQL
egrant_test database; SQLite is not used. Start PostgreSQL 16 as described in the
root README and adapt TEST_DATABASE_URL to the isolated database and local role.
No paid/private provider is called.

This host used `/private/tmp/egrant-profiles-tools/bin/uv` through the Makefile's
UV override and `/private/tmp/node-v22.23.4-darwin-arm64/bin` prepended to PATH.
For example, the executed check command was:

```sh
PATH=/private/tmp/node-v22.23.4-darwin-arm64/bin:$PATH \
  make check UV=/private/tmp/egrant-profiles-tools/bin/uv
```

The commands below assume the same compatible tools are available on PATH.

```sh
uv sync --locked
cd frontend && npm ci && npx playwright install chromium
cd ..
export TEST_DATABASE_URL=postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_profiles
make check
make test
make e2e
DEV_AUTH_BYPASS=true APP_MODE=fixture DATABASE_URL="$TEST_DATABASE_URL" \
  uv run alembic -c backend/app/profiles/alembic.ini upgrade head
cd frontend
npx playwright test -c src/features/profiles/playwright.config.ts
npx playwright test -c src/features/profiles/playwright.integration.config.ts
```

Run database-resetting pytest before browser integration, never concurrently.
The integration config accepts TEST_DATABASE_URL, requires an egrant_test name,
and uses ports 8012/5175. Other browser tests use 8011/5174. The owned
tests/profiles/browser_app.py assembles real module routes with the foundation
middleware and remaining 503 shells for tests; it is not a production app.

Verification recorded before final delivery:

- make check: exit 0; locks, Ruff, formatting, secret scan, generated contract
  drift, TypeScript and Vite build.
- make test: exit 0; 82 backend tests (50 profiles tests) and 26 frontend tests.
- make e2e: exit 0; three foundation Chromium/accessibility scenarios.
- Scoped profiles Playwright: exit 0; two explicitly mocked domain-HTTP
  scenarios for import/configure/save/reopen, dirty history, trial navigation,
  375/768/1440 px, and 200% text.
- Real PostgreSQL browser integration: exit 0; both supplied forms imported,
  saved as versions 1/2, reopened, and retrieved as immutable historical versions.
  The final run starts after pytest leaves the migrated profiles tables empty.
  No forms/profile HTTP response is mocked. Distinct mappings, options,
  original JSON and append/replace mode are checked.

Backend tests cover hostile/invalid JSON, duplicate tags/keys/options, unsupported
types, missing/incompatible destinations, column scopes, required/option metadata,
original JSON preservation, stable tags, safe Unicode failure, detached reads,
immutable rows, concurrent conflicts, rollback, pinned lookup, HTTP schemas and
access checks. Frontend tests cover stale cached state, failed capabilities,
invalid mappings, conflict drafts and extraction failures. Coverage percentage
is not measured. Locked Starlette/httpx and Alembic path-separator deprecation
warnings remain visible. No dark-mode or screen-reader audit is claimed.

## Manual reproduction

1. Apply 0301_profiles and assemble the module router as described above, or use
   the owned browser test harness. Open `/profiles` in fixture mode.
2. Give the form a name and upload tests/profiles/examples/invoice-form.json.
   Import it and edit an extraction label. Verify invoice.reference stays fixed.
3. Save version 1, edit the label again, and save version 2. Reload, select
   version 1 and verify its old label and disabled editor, then return to latest.
4. Edit without saving, follow the profiles link, and decline the discard prompt.
   Verify the draft remains. Explicitly discard the edit.
5. Import travel-form.json, select the contract or bank-statement starter, inspect
   rail/air option keys, configure column mappings and replace mode, and save.
6. With assembled document/extraction modules, choose a ready document and launch
   the saved version. Verify navigation to the shared review route. In the
   baseline harness, verify a visible unavailable error and disabled trial instead.

## Review and publication

Applied human-code to implementation, humanizer to technical prose and final-review
to actual changes and surrounding code. Supplemental specification, Python,
code-quality and security reviews found JSONB-unsafe names, nested snapshot
aliasing, stale capability state and incomplete table/column search; these have
regression tests and fixes. A deferred first-list regression reproduces and fixes
the first-import race with the shared 30-second cache lifetime: pending stale
queries are cancelled before caching the authoritative imported form.
Shared contracts and locks have no diff. Actual OCR/AI/eGrant and the assembled
extraction worker remain unverified.

GitHub CLI has no authenticated account. HTTPS push credentials are absent, but
the existing SSH key authenticates as dimaua12 and an SSH push dry-run confirms
write access. Publication uses that authorized SSH transport. Creating a PR still
requires GitHub API authentication; no remote PR is claimed. Browser fallback
was rejected by automatic tool approval with `approval policy: never`.
After GitHub authentication:

```sh
cd /Users/dima/future-makers-egrant-profiles
gh auth login --hostname github.com --git-protocol https --web
gh pr create --repo andr1chkol/future-makers-egrant --base main --head codex/profiles \
  --title "Implement form import and immutable profile builder" \
  --body-file docs/handoffs/03-profiles.md
```

Do not force-push or merge automatically. Give member 2 the resulting PR URL and
exact final head SHA for the fresh-chat review.
