# Final assembly continuation status

Verdict: **NOT READY**. Member 3 owns `codex/final-assembly` following member 5's
handover. Initial parent: `6d3843d43f00424601bd94dd0bba263bd9f6a728` from PR #11.
Its verified assembly code ancestor is
`a5b283f129cf9caed7097d75d71ed0fbd365618a`. No reset, force push, tag movement or
automatic PR merge was used. Available local worktrees were inspected and had
no intended unpublished changes at handover.

This continuation adds reproducible acceptance tests and delivery wiring. It
preserves the documents/profiles/export assembly, access gate, private storage,
upload limits, parser locks and existing recovery. It deliberately retains the
unavailable extraction/review shells until the required owner reviews pass.

## Required owner actions

| Module | Exact inspected head | Outcome and next action |
|---|---|---|
| Human review, PR #3 | `133e6ced9cbce21fb255fa77b45d3d335c47ec75` | Fresh-context member-3 review: CHANGES REQUIRED. Member 4 must adopt the UTC correction and prevent unsupported currency codes in human scalar/table edits, then request exact-head recheck. |
| Extraction, PR #6 | `f21eb8434a63dd65a9d509c76de9031fad67faaa` | Member 2's real-source fixture correction and member 1's independent exact-head review are absent. Option key preservation/empty options, recovery starvation and outstanding provider requests were reported for owner correction. |
| Documents | Included in PR #11 | Preserve corrected reviewed assembly. The member-1 code-scope PASS for a5b283f is not an independent PASS for the shared final assembly. |
| Profiles, PR #8 | `e84509990a84e3121b79b7cd0681912230a61887` | Included, with member-2 exact-head PASS. Imports remain illustrative; actual eGrant form exports were not verified. |

The human-review report and safe UTC patch are published on
`review/human-review-133e6ce`: report commit
`c5061f022f97fdbd6df7cd6e39477b2b6ada8718`, patch
`35b04707861657a9b79c92f758291bcd6a03c600`. The corrected review branch still
has CHANGES REQUIRED because invalid currency acceptance remains. Original
review checks were 54 backend passes / 1 failure, 11 frontend passes, 3 browser
passes using explicit neighboring adapters, and a passing `make check`. After
the UTC patch, 56 backend tests passed. These are module-review results, not
assembled-product results.

## Current-host verification

Locked `uv sync --locked` and frontend `npm ci` were used. Python 3.12, Node
22.23.4 and a local PostgreSQL 16 instance were used. All resettable databases
were dedicated `egrant_test*` databases. No SQLite substituted for PostgreSQL.

| Command | Actual outcome and scope |
|---|---|
| `make check UV=/private/tmp/egrant-profiles-tools/bin/uv` | PASS on inherited 6d3843d before continuation edits: locked dependencies, Ruff, formatting, secret scan, OpenAPI/client generation, frontend typecheck/build and no schema drift. |
| `make test UV=/private/tmp/egrant-profiles-tools/bin/uv` with `TEST_DATABASE_URL` | PASS on inherited 6d3843d: 196 backend tests passed, one Windows-only test skipped; 32 frontend tests passed. This predates the new failing acceptance tests. |
| `alembic -c backend/alembic.ini upgrade head` on an empty database, then `current` | PASS; one current merge head `0503_documents_assembly`. This verifies the inherited module set, not absent 0201/0401 migrations. |
| `make e2e` | PASS, 3 Chromium foundation/access/layout scenarios. |
| `make e2e-integration` | PASS, 4 Chromium submission scenarios; neighboring review/extraction reads are explicit test doubles. |
| `make e2e-profiles` | PASS, 2 UI-adapter scenarios and 1 real profiles/API/PostgreSQL scenario. |
| New public-flow backend acceptance, `pytest tests/integrations/test_full_product.py -x -q` | FAIL at actual extraction POST: 503 `FEATURE_UNAVAILABLE`, after genuine import, profile persistence, duplicate upload and worker normalization into 23 cells. No neighboring doubles. |

Final continuation checks on 2026-10-30:

- `make check UV=/private/tmp/egrant-profiles-tools/bin/uv`: PASS after correcting
  two formatting findings; no schema/client drift.
- `TEST_DATABASE_URL=.../egrant_test_final_assembly .venv/bin/pytest -q
  --tb=short --show-capture=no`: exit 1, 204 passed, 1 Windows-only skipped,
  3 failed. All failures are actual extraction POST 503 instead of 202.
- From frontend, `npm test`: exit 0, 32 passed. This was run separately because
  the earlier `make test` stopped before frontend execution on backend failure.
- `make e2e-documents`: exit 0, 2 passed with the dedicated
  `egrant_test_documents_e2e` database and explicit neighboring fixtures. An
  initial invocation with another test database name was rejected before startup.
- `FULL_PRODUCT_E2E_DATABASE_URL=.../egrant_test_full_product_e2e make
  e2e-full-product`: exit 2 through Make, 1 browser failure at extraction 503.
  Import, save, real upload and normalization completed without neighboring doubles.
- `pytest tests/platform/test_database_safety.py -q`: 8 passed. URL query
  overrides and non-PostgreSQL targets are rejected before destructive setup.
- `bash -n scripts/final-assembly-demo.sh` and `git diff --check`: PASS.

Node commands used `/private/tmp/node-v22.23.4-darwin-arm64/bin` first on PATH;
database URLs were supplied through environment variables. CI runs independent
checks after a failing acceptance test and retains that failure status. CI browser
artifacts explicitly collect synthetic trace directories. These workflow edits
have been inspected locally; their remote outcome is not claimed here.

Code/security self-review corrected dependent browser assertions to compare all
intended scalar/table edits against independent constants, a schema-invalid stale
revision assertion, query-override reset guards and graceful subprocess cleanup.
Prepared later assertions do not establish successful draft editing, confirmation,
exact exports, second mapping or assembled recovery. The other inherited module
browser launchers were not comprehensively hardened by this narrow change.

## Provider-mode matrix

| Capability | Current evidence | Limit |
|---|---|---|
| Form import | Illustrative configuration, tested persistence/mapping/versioning | Actual eGrant exports were not verified. |
| Document normalization | Production upload/storage/worker and genuine CSV cell sources exercised locally; inherited parser tests passed | Full release PDF/photo/XLSX input matrix remains pending. |
| OCR | Unavailable on this host: no configured OCR executable and Docker daemon unavailable | Historical Linux smoke evidence is in DOCUMENTS-ASSEMBLY.md; no new live OCR pass is claimed. |
| AI extraction | Unavailable in this assembly; no configured AI access on this host | No live request was made; no failed processing was replaced with fixture success. |
| Extraction fixture | Owner source is incompatible with actual normalized CSV cell IDs at inspected f21eb843 | Real-source owner correction and exact-head review required. |
| Human review | Independently reviewed standalone module has material defects | Not registered in the assembled application. |
| JSON export | Real submission persistence, idempotency and downloads tested with neighboring adapters | Full upload-to-confirmed-export flow has not passed. |
| eGrant writes | Disabled; capability false | Documented interface, authorized target and explicit write authorization absent. Export is not apply. |

## Remaining delivery gates

After owner corrections/reviews, merge their reviewed histories normally. Replace
the corresponding shells, register `extraction.process` and public terminal
recovery with fresh sessions, add model/migration discovery and a new merge
revision joining `0503_documents_assembly`, `0201_extractions`, `0401_reviews`.
Published revisions remain unchanged. Then run all checks again, clean-start
migration, the full deterministic flow, missing/duplicate/stale/retry/recovery
scenarios and separately configured live providers.

Member 4 is the assigned independent reviewer for the exact final assembly head
using `docs/team/06-PEER-REVIEW.md` in a fresh chat. Member 1 performs release
verification using `07-RELEASE-REVIEW.md` after assembly; that does not replace
independent coverage of member 1's document implementation. This continuation
and its tests are author work and do not approve their own assembly. Keep the PR
Draft until material correctness and acceptance blockers are resolved.
