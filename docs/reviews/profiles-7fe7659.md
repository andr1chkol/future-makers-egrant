# Independent review: profiles (member 3)

Reviewer: member 2. Author: member 3. Guide: `docs/team/06-PEER-REVIEW.md`.

- Reviewed head: `origin/codex/profiles` at `7fe76595cb82475eb0350bc3045433705319c8f9`
- Base: `main` / `bootstrap-v1` at `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8` (merge base)
- No pull request existed for `codex/profiles` at review time, so the branch head
  was reviewed. The author was still working; any later commit needs its own review.

## Verdict

**CHANGES REQUIRED**, for one small fix (finding 1). The patch is on branch
`review/profiles-7fe7659`. With it applied, the module's acceptance criteria are
met as far as they can be checked without the documents module and a real eGrant
export. The other findings are low severity or belong to other owners.

## Scope reviewed

All 32 changed files: `backend/app/profiles/**` (importer, validation, service,
routes, models, `0301_profiles`), `frontend/src/features/profiles/**` (editor,
field editor, trial run, model, tests, Playwright configs), `tests/profiles/**`,
and `docs/handoffs/03-profiles.md`. No shared files, contracts, lockfiles or
generated client are changed (`git diff origin/main` on `frontend/src/app`,
`frontend/src/shared`, `backend/app/platform`, `backend/app/main.py`, `contracts`
is empty).

## Findings

### 1. Medium, fixed: browser integration test writes to a macOS-only path

`frontend/src/features/profiles/e2e/integration.spec.ts:116` and `:124` save
screenshots to `/private/tmp/...`. That directory exists only on macOS, so the
real-PostgreSQL browser integration fails on Linux and on the GitHub runner:

```
Error: ENOENT: no such file or directory, open '/private/tmp/egrant-profiles-desktop.png'
```

Fix: write them to `testInfo.outputPath(...)`, the per-test Playwright output
directory. After the fix the test passes on Linux (see Verification).

### 2. Low: profile list order is effectively random

`backend/app/profiles/service.py:124` orders `list_profiles` by `profile_id`, a
random UUID. Pagination is stable, but the visible order of profiles has no
meaning for a manager and changes with every new profile. Ordering by name (and
ID as a tie-breaker), as `list_forms` already does, would be more usable.

### 3. Low: option keys keep surrounding whitespace

`backend/app/profiles/importer.py:85` checks that an option key is not blank
after stripping but stores the raw value. `{"key": " rail "}` is imported as
`' rail '`. The extraction schema then offers that exact key to the model, and
an export writes it back unchanged. Rejecting keys that differ from their
stripped form (`INVALID_OPTION`) would prevent a subtle mismatch with the
destination system. It was reproduced directly with `normalize_form`.

### 4. Low, owner member 5: profile events lose their IDs in JSON logs

Already recorded in the author's handoff: `profileId`, `formId` and `version` are
dropped by the baseline `JsonFormatter` until member 5 extends `ID_KEYS` and
`NUMBER_KEYS`.

### 5. Info, owner member 2: arithmetic checks depend on tag-derived keys

Profile keys are generated from destination tags (`availableKey`). Extraction's
arithmetic checks recognize conventional keys (`quantity`, `unit_price`,
`line_total`, `net_total`, `vat_total`, `total`, ...). With the shared example
form they line up. A real eGrant form with other tags will extract normally but
skip those checks. This is a contract-level gap (no semantic role on profile
fields), not a defect in this module.

## Integration with extraction (member 2)

- `get_form` and `get_profile` match `contracts/internal.md`, never commit, and
  raise `NotFoundError` for unknown IDs and versions. Extraction calls them inside
  its own transaction, and that works.
- The profile built by the editor's mapping from `contracts/examples/form.json` has
  exactly the key/type structure of `contracts/examples/profile.json`, so the
  extraction fixture provider recognizes it and the fixture demo will run.
- A local assembly of `codex/extraction` with this branch, review and integration,
  plus a temporary merge revision, ran create form → create profile → extraction
  (fixture) → review confirm → export successfully. The document was stubbed
  because the documents module is not published.
- `TrialRun` posts exactly the contracted `CreateExtractions` body and navigates
  to `/review/:id`; it does not build a second extraction path.

## Checklist observations

- Transactions: writes own `session.begin()`; version allocation locks the head
  row; database triggers block snapshot updates and deletes. Concurrent saves are
  covered by tests.
- Validation at the boundary: depth, size, NUL, surrogates, non-finite numbers,
  duplicate tags/keys/options, type compatibility, column scopes.
- Imported text is rendered as React text only; no `dangerouslySetInnerHTML`,
  `innerHTML` or `eval` in the module.
- No TODO/FIXME, no console logging, no dead code found.
- The router carries `require_access` itself; member 5 adding it again at
  `include_router` is harmless (FastAPI caches the dependency per request).

## Verification

Run on Linux (Fedora 44) in a clean checkout of `7fe7659`, Python 3.12.16,
Node 22, PostgreSQL 16 under podman,
`TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test`.

| Command | Result |
|---|---|
| `uv sync --locked`, `npm ci` | ok |
| `make check` | passed (locks, Ruff, format, secret scan, contract drift, TypeScript, Vite build) |
| `uv run pytest` | 82 passed |
| `cd frontend && npm test` | 26 passed (3 files) |
| `make e2e` | 3 passed |
| `npx playwright test -c src/features/profiles/playwright.config.ts` | 2 passed |
| `npx playwright test -c src/features/profiles/playwright.integration.config.ts` | **failed** at `7fe7659` (finding 1); **1 passed** with the fix |

Not verified: a real eGrant form export (none available), a trial run against
real documents and a live AI provider, cross-browser history blocking (the
author documents the Chromium-only Navigation API guard), and screen-reader and
dark-mode behavior.
