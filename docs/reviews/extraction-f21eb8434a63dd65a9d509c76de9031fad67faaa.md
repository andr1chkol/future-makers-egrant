# Independent extraction review: f21eb8434a63dd65a9d509c76de9031fad67faaa

**Verdict: CHANGES REQUIRED.** Five defects reproduced during this review are fixed on the separate review branch. The reviewed PR head still contains them, and an option-scope collision remains unresolved. This report does not approve PR #6 or declare the assembled product ready.

## Scope and provenance

- Reviewer: member 1, in a fresh review chat; module author: member 2 (`niknoir`).
- PR: [#6](https://github.com/andr1chkol/future-makers-egrant/pull/6).
- Reviewed head: `f21eb8434a63dd65a9d509c76de9031fad67faaa`.
- Base, merge base, and `bootstrap-v1`: `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`; recorded `BASE_BRANCH=main`.
- Review branch: `codex/extraction-peer-review-f21eb84`.
- Fix commit tested: `e847a02dbf3a2388f7c4a5ecf577cde5e18f508d`.
- Final head recheck: 2026-10-30 20:56 Europe/Budapest; GitHub still reports the reviewed head and base above.
- Followed `docs/team/06-PEER-REVIEW.md`; read AGENTS, root/team CONTRACT and QUALITY, API/internal contracts, shared examples, member-2 prompt, current handoff, and the older team summary. Applied bundled human-code and final-review, backend-reliability-review, and humanizer to report prose only.

The isolated clone is `D:/CodexWorkspaces/egrant-extraction-review-f21eb84`. The member-1 author checkout was not edited or reset. The review uses published PR #6 code and shared fixtures; it does not depend on unpublished document changes or on documents PR #9.

## Findings

Line references below identify the original reviewed head, not the repaired files.

### R1 [P1] A cropped amount quote can hide a debit sign: fixed

`backend/app/extraction/assembly.py:177` checks a printed value inside its quote. A provider can return positive `12,50` with quote `12,50` from source `-12,50 EUR`; the amount becomes `12.50` with status `found`. The same error occurs with trailing minus signs and accounting parentheses, including a null quote. A verified positive amount can therefore represent a printed debit.

The fix also checks the surrounding original source unit for sign markers. Contradictions keep the proposed value for human review and add `VALUE_NOT_IN_EVIDENCE`; they do not silently reverse its sign. Coverage includes leading/trailing Unicode minus, accounting parentheses, spaced markers, currency prefixes, and a numeric supplier name that must not be treated as a debit.

### R2 [P2] Whitespace matching persists a non-verbatim quote: fixed

`backend/app/validation/evidence.py:43` accepts quotes after whitespace normalization but stores the provider's original quote. Source `Demo   Paper\ns.r.o.` can produce stored quote `Demo Paper s.r.o.`, which is not a substring of the source. This violates the exact-excerpt contract and can break source highlighting.

Matching still tolerates OCR whitespace changes. The stored quote now comes from the exact matching span of the source text. Other quote differences remain unverified.

### R3 [P2] Active runs can starve terminal recovery: fixed

`backend/app/extraction/service.py:243` limits the candidate batch before checking job status. With batch size 1, put an older active run before a newer stranded run whose job failed. Repeated sweeps examine only the active run, leaving the stranded run queued forever. The production batch size of 50 has the same issue with 50 older active runs.

The query now excludes active jobs and requires a failed latest job before applying the limit. Row locks, `SKIP LOCKED`, the bounded write batch, the history recheck, and run-token fencing remain in place. Existing concurrent-retry, final-lease, late-worker, and repeat-sweep tests pass.

### R4 [P2] Database timezone leaks into extraction timestamps: fixed

`backend/app/extraction/service.py:435` returns the PostgreSQL timestamp unchanged. On this PostgreSQL instance, `Europe/Budapest` produces `+01:00`, although `contracts/internal.md` requires UTC output. The existing timestamp test failed on the original head.

The DTO conversion now calls `astimezone(UTC)`. A regression also supplies an explicit non-UTC timestamp without depending on server configuration.

### R5 [P2] An ambiguous currency symbol verifies a guessed ISO code: fixed

`backend/app/extraction/assembly.py:166` treats every possible currency associated with `$` or `¥` as verified. Source `Total: $12.50` and a provider choice of `USD` produce `found`, although the source does not distinguish USD from other dollar currencies.

The fix separates possible symbol matches from unambiguous codes/symbols. A guess supported only by an ambiguous symbol is `needs_review` with `CURRENCY_AMBIGUOUS`. An explicit `USD` code still verifies the value. The proposed currency is preserved for human review.

### R6 [P2] Scalar and table option scopes collide: unresolved

`backend/app/extraction/schema.py:38` encodes a table scope as `table.column`, while `backend/app/extraction/service.py:119` and `:125` store scalar keys in the same dictionary. Public profile keys are unrestricted strings, unique only within their own scope.

Reproduction with schema-valid shared examples:

1. Rename the `invoice_number` scalar key to `items.description` and give its form target option `scalar-choice`.
2. Give the `items` table's `description` target option `table-choice`.
3. Call `form_option_keys(profile, form)`.

Actual result: `{"items.description": ["table-choice"]}`. The scalar's allowed choice is lost; its provider schema uses the table's enum, and the valid scalar choice is rejected during assembly. `option_scope("items.description") == option_scope("description", "items")`.

Member 2 and member 5 must agree on an unambiguous persisted scope representation and compatibility for existing snapshots. A dictionary-only encoding change would misread existing `option_keys`; restricting profile keys would change the frozen public contract. This review leaves those decisions explicit rather than silently changing either contract or stored-data semantics. Add a regression covering both enums after the agreed fix. **This remains a module blocker even after taking the five fixes above.**

## Verification and reproducibility

Commands ran from the isolated clone. `PY` below denotes `D:/CodexWorkspaces/egrant-member1-documents/.venv/Scripts/python.exe`, reused only as a dependency runtime. `PYTHONPATH` and pytest's configured path resolve application imports to the review clone's `backend`, not the author checkout. All 13 direct runtime/check dependency versions matched `uv.lock`; `uv lock --check --offline` passed.

PowerShell environment:

```powershell
$env:PYTHONPATH='D:/CodexWorkspaces/egrant-extraction-review-f21eb84/backend'
$env:TEST_DATABASE_URL='postgresql+psycopg://egrant@127.0.0.1:55434/egrant_test_extraction_review'
$env:PYTHONUTF8='1'
$env:TEMP='D:/CodexWorkspaces/egrant-extraction-review-f21eb84/work'
$env:TMP=$env:TEMP
$env:PGCONNECT_TIMEOUT='3'
```

PostgreSQL: 16.15. Only `egrant_test_extraction_review` was created/reset. The documents test databases were not reset. The shared cluster was found stopped during a later run, started again on `127.0.0.1:55434`, and left running. The affected review-only test process was stopped and rerun; an interrupted run is not counted as a pass.

Windows compatibility setup: copied the existing `alembic.exe` launcher to ignored `.venv/bin/alembic.exe`, which satisfies the shared fixture's `.venv/bin/alembic` command. This changes no shared infrastructure. The extraction evaluator test now copies its small profile fixture tree instead of requiring privileged directory symlinks. UTF-8 mode is required for the Slovak fixtures. Contract export generated Windows CRLF only; normalized bytes matched the original exactly, and the original file bytes were restored. No schema/client changes are included.

| Command or check | Actual result |
|---|---|
| Original head: `PY -m pytest tests/extraction tests/platform -q --tb=short` | Exit 1: 174 passed, 3 failed, 1 skipped. Failures: UTC output, Windows symlink privilege, unchanged platform storage. An earlier setup attempt lacked the dedicated database; it was corrected before this baseline run. |
| First regression run before fixes: `PY -m pytest tests/extraction/test_peer_review.py -q --tb=short` | Exit 1: all initial 11 cases failed, reproducing R1–R4. Additional currency/sign cases reproduced R5 and exercised the repair. |
| Final: `PY -m pytest -q --tb=short --basetemp=work/verification-final --junitxml=work/final-verification.xml` | Exit 1: 200 passed, 1 failed, 1 skipped in 102.00 s; the sole failure is unchanged Windows platform storage, detailed below. |
| Extraction cases in that final run | 169 passed, 1 skipped, 0 failed/errors; extracted from the final JUnit result. The review adds 24 regression/behavior cases. |
| `PY -m ruff check backend scripts tests` | Exit 0. |
| `PY -m ruff format --check backend scripts tests` | Exit 0; 49 files formatted. |
| `PY -m app.extraction.evaluation tests/extraction/evaluation/tuning` | Exit 0; 2 recorded cases, 32 expected values, 32 correct, 0 missing/incorrect/invented. |
| `PY -m app.extraction.evaluation tests/extraction/evaluation/heldout` | Exit 0; 4 recorded cases, 51 expected values, 44 correct, 3 missing, 4 incorrect, 1 invented, 3 flagged; 9 expected rows, 8 returned. These are deliberately planted reply errors, not a model accuracy measurement. |
| `PY scripts/scan_secrets.py` | Exit 0; 132 tracked files scanned before adding this report and 133 files after staging it. |
| `PY scripts/export_contract.py`, normalized byte comparison, `git diff --exit-code -- contracts/api.yaml frontend/src/shared/api.generated.ts` | Exit 0 after removing export-only CRLF differences; no semantic or committed drift. |
| `uv lock --check --offline --cache-dir D:/CodexWorkspaces/egrant-extraction-review-f21eb84/work/uv-cache` | Exit 0; 42 packages resolved. |
| `git diff --check` | Exit 0. |
| R6 direct DTO-valid reproduction through `form_option_keys` | Scalar choice overwritten by table choice; remains reproducible. |

The final tests cover strict parsing, malformed JSON, wrong types/keys, nulls, money/date normalization, evidence fabrication, prompt-injection fixtures, another profile, arithmetic mismatches, frozen profile snapshots, multi-document rollback, provider execution outside a transaction, retries, stable rows, duplicate execution, concurrent claims, stale workers, recovery, route/schema agreement, pagination, access, and failure logging. Logging coverage passes realistic synthetic keys, authorization/cookie strings, a name, IBAN, amount, and filename through an unexpected exception. It verifies redaction, ERROR level, safe error code, request/extraction/document correlation, attempts, stack presence, and platform job retry IDs.

The final shared-storage failure is `tests/platform/test_logging_storage.py::test_private_storage_is_immutable_and_rejects_traversal`: Windows has no `os.O_NOFOLLOW`, used by unchanged `backend/app/platform/storage.py:32`. It is a platform portability blocker, separate from the extraction findings. The test was not skipped, weakened, or shimmed into a pass. An omitted database environment variable caused four setup errors in one intermediate targeted run; the final run used the environment above.

## Integration and provider status

| Area | Independent evidence and remaining work |
|---|---|
| Extraction module and PostgreSQL persistence | Tested with deterministic providers and public-interface stand-ins for documents/profiles. |
| HTTP behavior and access gate | TestClient exercises an explicitly assembled extraction router, error envelopes, and frozen schema compatibility. The default application at this PR head still serves the documented extraction shells. |
| Worker | Tests register the real handler. Member 5 still needs production registration and a call to `recover_terminal_extractions` in the worker loop. |
| Migrations | `0201_extractions` upgrades through the shared PostgreSQL fixture; the revised platform migration test checks one head, required revisions, and tables. Full assembly still needs its merge revision and union of module assertions. |
| Shared CSV fixture | Recorded extraction reproduces the shared normalized-document example. Actual upload/normalization and the complete document-to-export flow were not independently assembled in this checkout. Documents/profiles/reviews code is absent from the reviewed tree. |
| OpenAI transport | Fake HTTP failures and a local slow-response HTTP server verify request shape, safe errors, and the caller's overall deadline. Official [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs) supports the Responses `text.format` shape, required properties, and closed objects. |
| OpenAI live | **NOT INDEPENDENTLY VERIFIED.** The live test remains disabled. The author's current handoff reports earlier synthetic live calls; this reviewer did not repeat them, inspect credentials, or call paid providers. A fresh independent held-out set is still needed for model-quality claims. |
| Provider resource cleanup | The deadline abandons a daemon request thread rather than cancelling the network operation. A continuously trickled response can keep that thread alive beyond the caller deadline; bounded cleanup under sustained stalls was not verified and remains an operational limitation. |
| OCR and eGrant | Outside this extraction review; no independent live evidence or external writes. |

The original module isolates external calls from transactions, freezes profiles, uses shared DTOs/logger/jobs, and fences late result writes with a run token. Those choices held under the executed tests. The public contract, manifests, shared infrastructure, and published migration were not changed by this review.

Read `07-RELEASE-REVIEW.md` as required by AGENTS. Its assembled-release precondition is not met here; no release-readiness verdict is implied. Frontend checks, browser workflows, full `make check/test/e2e`, real document/provider quality, and deployed multi-tenant security were not verified.

## Required follow-up

Take the review fixes into the extraction implementation, resolve R6 with the relevant owners, and rerun an independent verdict against the resulting full SHA. Member 5 must complete and verify assembly separately. PR #6 remains draft and unmerged; this review publishes only the authorized repository report and a separate draft follow-up PR, without a GitHub approval or review comment.
