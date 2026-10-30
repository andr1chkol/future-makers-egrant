# Documents repeat peer review

**PASS for the corrected member-1 documents scope at `a5b283f129cf9caed7097d75d71ed0fbd365618a`.**

This scoped verdict closes the macOS parser finding. It does not approve member-5 shared changes, PR #11 as a whole, extraction compatibility or release readiness. Member 4 remains the independent reviewer for member-5 integration. The complete product remains NOT READY.

## Identity and scope

- PR: https://github.com/andr1chkol/future-makers-egrant/pull/11
- Published reviewed head: `a5b283f129cf9caed7097d75d71ed0fbd365618a`.
- Base / merge base / bootstrap-v1: `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`; recorded `BASE_BRANCH=main`.
- Module author: member 1. Independent module reviewer: member 5, continuing the fresh-chat review assignment.
- Previous source: `9a9bfa5be372fbac5a7408b0648f32ff75cb8460`; its original CHANGES REQUIRED report remains unchanged.
- Correction source: `af2765eade1be06b370bb4cb28efb39f2d5cb526`, applied by integration as `4f18637381515ca869d73287033c97ad5d6a1e88`.
- Review checkout: `/private/tmp/egrant-peer-documents-a5b283f`; newly created from the exact published head. Review date: October 30, 2026.

GitHub metadata and `git fetch origin refs/pull/11/head` independently confirmed the requested head, base and draft/unmerged state. The PR was attached to this chat. No changes were made to the main checkout, `/private/tmp/egrant-documents-integration` or `/private/tmp/egrant-documents-clean-a5b283f`.

Read the formal peer-review instructions, updated assembly handoff and internal interfaces; applied the previously loaded human-code, backend-reliability-review and final-review guidance. Humanizer was applied only to this report's technical prose. Compared the current module files against the originally inspected implementation and the review fix, and examined changed call sites and boundary tests.

## Finding closure

**Closed: P2, `backend/app/documents/parse_worker.py:19-22`.** The Linux address-space limit now runs only when `sys.platform == "linux"`. The Darwin/Windows entrypoint regression tests are present. These two files are byte-identical to the reviewed correction commit: `git diff --exit-code af2765e HEAD -- backend/app/documents/parse_worker.py tests/documents/test_parse_worker.py` exited 0.

Actual subprocess PDF, CSV and XLSX parsing now passes on macOS/Python 3.12.6. The suite also verifies PNG/JPEG and scanned-PDF behavior through explicit fake OCR. The former macOS failure no longer prevents valid uploads. Linux address-space enforcement is retained in source but was not independently executed in this repeat review.

No new unresolved finding was identified in member 1's corrected scope. Normalization, OCR adapter, route definitions, DTO use, original module migration/models, settings and upload frontend are unchanged from the original reviewed implementation. The original review's format, provenance, private access, immutable sources, retry/fencing and log-redaction assessment remains supported by freshly executed tests.

## Assembly changes and independence boundary

The new head additionally contains member-5 changes to recovery correlation/batching/token invalidation, intake advisory locks, orphan cleanup, shared storage, pre-parser upload limiting, registrations, dependencies, migration assembly and test launchers. These were inspected to understand documents compatibility and exercised by relevant tests. That evidence does not constitute independent approval of member 5's own work. Member 4 must evaluate their final diff and production reliability separately.

The document tests now instantiate the production application rather than replacing document shells with a test router. The production boundary test verifies upload -> actual registered document worker -> ready normalized sources -> private original content, rejects retry of ready documents, and checks repeat-job immutability. Contract tests verify document OpenAPI operations and shared examples. This establishes working module interfaces on the assembled head, not successful downstream extraction.

## Independently executed checks

A fresh `.venv` was created using `uv sync --locked --offline` with `UV_CACHE_DIR=/private/tmp/egrant-peer-uv-cache`; all requested parsers installed directly from the published lockfile. No ad-hoc parser installation or manifest change was needed. `npm ci` ran inside the new checkout's frontend. Both exited 0.

Database commands used only the previously authorized dedicated `egrant_test_peer_documents` database on the supplied local PostgreSQL test container at localhost:55435. Credentials are omitted from this report. Tests ran sequentially with respect to database resets; no unrelated database was reset.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/documents tests/platform tests/integrations/test_document_boundary.py -q` | Exit 0; **105 passed, 1 skipped**, 33.63 s |
| `npm test -- --run` in frontend | Exit 0; **32 passed**, 4 files |
| `npm run build` in frontend | Exit 0; TypeScript and Vite production build |
| `.venv/bin/ruff check backend scripts tests` | Exit 0 |
| `.venv/bin/ruff format --check backend scripts tests` | Exit 0; 74 files formatted |
| `.venv/bin/python scripts/scan_secrets.py` | Exit 0; 179 tracked files scanned |
| `.venv/bin/python scripts/export_contract.py` and `git diff --exit-code -- contracts/api.yaml` | Exit 0; no OpenAPI drift |
| `npm run generate`, `npm run format:check`, generated-client diff | Exit 0; no client drift |
| `uv lock --check --offline` | Exit 0 |
| `frontend/node_modules/.bin/playwright test --config tests/documents/playwright.config.cjs` | Exit 0; **2 passed**, 14.3 s |
| `git diff --check` | Exit 0 |

The backend selection includes both platform-seam parser regressions, actual subprocess formats, source coordinates and stable IDs, duplicates/concurrent retries, late workers, restart recovery, migration round trips, content access, not-ready behavior, log correlation/redaction, production document registration, raw body limits, storage symlinks and cleanup/intake-lock compatibility. The one skipped test concerns Windows-specific behavior on a macOS host. A Starlette/httpx deprecation warning remains.

The browser server's test-only database guard requires `egrant_test_documents_e2e`. As in the original review, a wrapper temporarily substituted only that guard's database name with `egrant_test_peer_documents`, supplied the matching URL and restored `tests/documents/serve.py` byte-for-byte in `finally`. No production code or assertion was changed. The final working tree was clean before this report was added.

The browser checks use production document routes and actual document processing, with explicitly supplied neighboring profile/extraction fixtures. They verify partial upload rejection, source-cell preview, refresh, retry, distinct extraction links, navigation and layouts at 375/768/1440 pixels. They are not proof that the owner extraction implementation succeeds.

Logs: `/private/tmp/egrant-peer-a5b283f-tests.log` and `/private/tmp/egrant-peer-a5b283f-browser.log`. Browser screenshots are under `.private/` in the isolated review checkout.

## Blockers and unverified scenarios

The assembly handoff records `FIXTURE_NOT_AVAILABLE` when extraction f21eb84 consumes actual normalized CSV units. Documents produces document-specific UUIDv5 cell units; the extraction fixture expects older row evidence and fingerprints unit IDs. The uploaded CSV bytes/hash and true source provenance must be preserved. Member 2 must reconcile fixture recognition and evidence rebinding, followed by exact-head extraction review and an actual successful assembled workflow.

This repeat review inspected that explanation and the available auxiliary provider fingerprint code. It did not independently rerun the separate extraction probe or approve that out-of-tree extraction revision. The current published worker still reserves an unavailable extraction handler. Therefore no successful full document -> extraction -> human confirmation -> export result is claimed.

The assembly author's 196-backend-test/12-browser-scenario totals, Linux Compose/storage probes and live Tesseract smoke remain author evidence; the independently rerun totals are the ones above. Live Tesseract, Slovak OCR accuracy, poor scans, Linux deployment, native Windows ACL behavior, live AI, eGrant OCR and target-application writes were not verified in this repeat pass. No external write, GitHub review/comment, merge, deployment or force push occurred.

## Delivery

The only new deliverable from this repeat review is this report; no further code fix was required. The original `documents-9a9bfa5.md` verdict remains valid for its original SHA. This scoped PASS applies only to member 1's corrected documents behavior at the exact head named above. A later head needs its own applicable review, and member 4's independent shared-integration review and the assembled release review remain required.
