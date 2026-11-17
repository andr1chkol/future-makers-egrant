# Documents peer review

Verdict: **CHANGES REQUIRED** for published head `9a9bfa5be372fbac5a7408b0648f32ff75cb8460`.

Author: member 1. Independent reviewer: member 5, fresh chat. Review date: October 30, 2026.
PR: https://github.com/andr1chkol/future-makers-egrant/pull/10
Base / merge base / bootstrap-v1: `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
Recorded `BASE_BRANCH=main`. GitHub metadata and a fetch of `refs/pull/10/head` both confirmed the supplied head. The PR remains draft and unmerged.

The review used `/private/tmp/egrant-peer-documents-9a9bfa5`, a detached worktree created from the exact head. Neither the main checkout nor `/private/tmp/egrant-documents-integration` was edited. The report and accompanying fix belong to a separate review branch. This verdict does not approve a future PR head or the assembled release.

## Finding and fix

### P2: Linux address-space setup prevents every format from parsing on macOS

Location: `backend/app/documents/parse_worker.py:19-22` at the reviewed head.

The guard `sys.platform != "win32"` applies `resource.RLIMIT_AS` to macOS as well as Linux. On this macOS/Python 3.12.6 host, setting the requested limit raises `ValueError: current limit exceeds maximum limit`. Setup happens outside the error-to-JSON block, so the parser subprocess exits before validating any file. The parent maps this to `PARSING_FAILED` / HTTP 422. Valid CSV, PNG, PDF and XLSX inputs consequently fail in the documented host development workflow. This is a host-platform defect; it does not establish that the Linux deployment fails.

Reproduction on the unchanged head:

```sh
.venv/bin/python -c 'import resource; resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))'
# exit 1: ValueError: current limit exceeds maximum limit
.venv/bin/pytest tests/documents -q
# exit 1: 36 failed, 28 passed, 1 skipped
```

The review fix restricts this Linux-specific memory limit to `sys.platform == "linux"`. Byte, archive, image, text and subprocess time limits remain in place. It does not claim address-space enforcement on macOS or Windows. New `tests/documents/test_parse_worker.py` exercises the real worker entrypoint and CSV normalization with Darwin/Windows platform seams; Darwin simulates the observed resource error. The test was run against the original guard and produced one failure / one pass, then passes with the fix. Existing full subprocess format tests also pass after the change.

The accompanying fix is **not part of the published reviewed head**. Incorporate it and verify the resulting actual SHA before issuing a new verdict.

## Independent implementation assessment

Inspected all 24 changed files, module migration/model consistency, shared access, storage, jobs, database sessions, DTOs, worker/router assembly, generated-client callers, authoritative contracts/examples, the assigned prompt and author handoff. Applied human-code, backend-reliability-review and final-review. Report prose was checked with humanizer in a technical register; code and contracts were preserved.

- Upload preflight rejects invalid batches before persistence. Hash locks serialize duplicate detection in a stable order; duplicate originals remain separate UUID-addressed private files. MIME/signature checks, format limits and filenames are handled at the module boundary.
- Source publication and ready status commit together. Parsing/OCR runs outside database transactions. Ready data is immutable; stable IDs derive from document/location. Job token/lease checks fence stale publication, retries have a lifetime cap, and interrupted terminal leases are reconciled.
- Tests exercise PostgreSQL concurrency, restart/reclaim, stale workers, concurrent retries, migration downgrade/upgrade, missing resources, not-ready responses, content access, safe failures and stored-hash mismatch. No SQLite substitution was used.
- Real PDF text, XLSX cached formula behavior, source sheet/cell/page provenance and CSV encodings/blank rows are exercised. Fake OCR covers page ordering, images and provider failures; it proves no live OCR integration.
- Captured-log tests verify upload/duplicate/start/ready events, request correlation across worker execution, attempts and realistic synthetic PII/key redaction. Failure/redaction tests and shared logging tests pass. Logs are not treated as persisted audit data.
- Owned routes match the frozen document OpenAPI operations. Frontend uses the generated client and shared DTOs. Browser tests exercise real document persistence/processing with explicit neighboring profile/extraction stubs, partial rejection, source-cell preview, refresh, retry, distinct review links and navigation.
- Desktop and mobile screenshots were visually inspected. Fixture mode is visible; Slovak UI text and original source content are preserved. Browser assertions cover widths 375, 768 and 1440. This is module workflow evidence, not full review/confirmation/export acceptance.

## Commands and outcomes

Commands ran from the isolated review root unless stated otherwise. `TEST_DATABASE_URL` identified only `egrant_test_peer_documents` on the supplied PostgreSQL container at localhost:55435. The database was created specifically for this review. Test credentials are omitted here.

Dependency setup: `uv sync --locked`, then isolated `uv pip install pypdfium2==5.14.0 Pillow==13.0.0 openpyxl==3.1.5 defusedxml==0.7.1 pypdf==6.21.4`, and `npm ci` inside `frontend`: exit 0. Manifests and locks were not edited. `UV_CACHE_DIR=/private/tmp/egrant-peer-uv-cache` was used. Initial sandbox attempts hit an unwritable default cache and DNS restrictions; an authorized network-enabled retry succeeded.

| Command | Actual result |
| --- | --- |
| `.venv/bin/pytest tests/documents -q`, unchanged published head | Exit 1; 36 failed, 28 passed, 1 skipped, 11.83 s |
| Same command, parser guard fixed, before new regression tests | Exit 0; 64 passed, 1 skipped, 20.46 s |
| `.venv/bin/pytest tests/documents/test_parse_worker.py -q`, original guard | Exit 1; Darwin fails with observed resource error; Windows seam passes |
| `.venv/bin/pytest tests/platform -q`, fixed tree | Exit 0; 32 passed, 5.73 s |
| `.venv/bin/ruff check backend scripts tests` | Exit 0 |
| `.venv/bin/ruff format --check backend scripts tests` | Exit 0 |
| `.venv/bin/python scripts/scan_secrets.py` | Exit 0; 118 tracked files scanned |
| `.venv/bin/python scripts/export_contract.py` plus frozen OpenAPI diff | Exit 0; no drift |
| `npm test -- --run` in frontend | Exit 0; 7 tests across 2 files |
| `npm run build` in frontend | Exit 0; TypeScript and Vite production build |
| `npm run generate`, `npm run format:check`, generated-client diff | Exit 0; no drift |
| `frontend/node_modules/.bin/playwright test --config tests/documents/playwright.config.cjs` | Exit 0; 2 passed, 17.5 s, patched parser |
| `git diff --check` | Exit 0 |

The browser server normally insists on the hardcoded database name `egrant_test_documents_e2e`. A review-only wrapper temporarily substituted `egrant_test_peer_documents` in that test guard, supplied `DOCUMENT_E2E_DATABASE_URL`, and restored `serve.py` byte-for-byte in `finally`. No production boundary or assertions were weakened. Browser tests ran after database tests, with local ports 8012/5175. No Windows storage shim was active.

An initial attempt at `pytest tests/test_contracts.py` exited 4 because that path does not exist. The correct contract tests are under `tests/platform` and passed in the 32-test run. A transient lint run during the browser harness substitution flagged its temporary longer database-name string; the restored harness passes lint. Neither result is counted as a pass on the transient tree.

## Shared assembly requirements and remaining risks

These were explicitly delegated by the published PR/handoff. They are integration prerequisites, not newly discovered ownership violations by member 1:

1. Lock the requested dependencies in shared manifests and runtime images. A plain frozen install at this head lacks document parsers.
2. Replace document shell routes and the unavailable worker registration; include module migrations/metadata and reconcile migration heads. The production entrypoints at this head still use foundation shells. Test assembly does not fulfill this requirement.
3. Derive OCR capability from the actual adapter configuration and forward document settings to API/worker containers.
4. Enforce total multipart body limits before FastAPI multipart spooling, at the trusted proxy/ASGI boundary. Handler file limits alone cannot bound pre-handler disk consumption.
5. Address private-storage orphan cleanup after a successful put followed by an I/O/DB failure. Validate platform-specific immutable storage protection and permissions in the assembled deployment. macOS POSIX storage tests pass here; Windows ACL/symlink protection and Linux container behavior were not independently verified.
6. Re-run this review's regression and module tests, then the assembled workflow and release review on the actual integrated SHA. In particular, this review does not approve registration/storage/lock/upload-boundary changes being implemented elsewhere.

Live Tesseract OCR, Slovak language data/accuracy, eGrant OCR, live AI, full document-to-confirmed-export flow, real eGrant writes, Linux Compose startup and the fixed Linux resource-limit execution were **NOT VERIFIED**. The only skipped module case is Windows-specific storage behavior on this macOS host. A Starlette/httpx deprecation warning was present; no dependency compatibility failure occurred after isolated parser provisioning. No deployment, merge, GitHub review/comment or target-application write was performed.

## Final verification

The full backend suite and final diff are checked after the fix and regression addition; results are recorded below. The original published SHA retains CHANGES REQUIRED regardless of the patched checkout results.

Final `.venv/bin/pytest -q`: **exit 0, 98 passed, 1 skipped, 25.40 s**, with the parser fix and both new regression cases. Logs: `/private/tmp/egrant-peer-final-pytest.log`; earlier module/platform/browser logs: `/private/tmp/egrant-peer-documents-pytest-fixed.log`, `/private/tmp/egrant-peer-platform.log`, `/private/tmp/egrant-peer-browser.log`. Screenshots: `.private/upload-desktop.png` and `.private/upload-mobile.png` inside the review checkout.

The final formatter requested one blank line in the new regression test; it was applied. Final Ruff lint/format, offline `uv lock --check`, and whitespace checks pass. Final-review inspected the one-line production fix, regression test, report and surrounding worker/parser behavior. No shared files or contracts are included in the fix. The review commit can be cherry-picked for integration; it is not a replacement verdict for that integration's SHA.
