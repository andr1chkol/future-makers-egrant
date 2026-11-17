# Member 2 status audit: extraction at 78d84d7

Audited by member 2 (self-audit, not an independent review) on 2026-10-30.

- Branch: `codex/extraction`, head `78d84d780aedde04cae35a86b2774255d202ed0d`, identical
  to `origin/codex/extraction`. No unpushed commits.
- PR: https://github.com/andr1chkol/future-makers-egrant/pull/6 into `main`, **Draft**.
- Uncommitted local change: `docs/handoffs/report-2.md` is deleted in the working tree
  but still tracked and published. This is not a module change and was not committed.
- Shared state inspected: `origin/main` at `88d1b95` (bootstrap only),
  `origin/codex/integration` at `74da164`.

## Summary

The module works as a standalone, tested backend with a verified live OpenAI path on
synthetic documents. It is **not part of the assembled application**: the worker still
registers `unavailable_handler` for `extraction.process`, the `/extractions` shells are
still in place, `0201_extractions` is not in the integration migration graph, and
`aiConfigured` is false. Member 5 holds these until an independent review exists.

Two pieces of member-2 work are open:

1. `recover_terminal_extractions(session)`, an interface member 5 recorded in
   `contracts/internal.md` on `codex/integration` (`74da164`) and assigned to member 2.
2. An end-to-end provider deadline. `urlopen(timeout=40)` bounds each socket operation,
   not the whole call, so a slow response can outlast the 60-second lease.

No independent review of PR #6 exists yet (assigned reviewer: member 1, whose module
is unpublished).

## Acceptance checklist (from docs/team/02-EXTRACTION-PROMPT.md)

| Requirement | Status | Evidence | Remaining |
|---|---|---|---|
| Create/list/detail/retry routes as contracted | IMPLEMENTED AND VERIFIED (standalone) | `backend/app/extraction/routes.py`; `test_lifecycle.py::test_http_routes` against `contracts/api.yaml` with the router mounted ahead of the shells | Member 5 replaces the shells in `app/platform/routes.py` |
| One extraction per document in a batch | IMPLEMENTED AND VERIFIED | `test_batch_creates_one_queued_extraction_and_job_per_document` | — |
| Persist profile snapshot and processing state | IMPLEMENTED AND VERIFIED | `ExtractionRecord.profile_snapshot`, `option_keys`; lifecycle tests | — |
| `extraction.process` through the shared worker | IMPLEMENTED, NOT ASSEMBLED | `process_extraction`; tests drive `app.platform.jobs.run_once` | BLOCKED by member 5: `app/worker.py` still registers `unavailable_handler` |
| Documents and profiles via public functions only | PARTIAL | Profiles: real `get_profile`/`get_form` exercised in a local assembly (not pushed). Documents: stand-in only | BLOCKED by member 1: `app.documents.service.get_normalized` unpublished |
| Backend AI adapter with profile-derived structured output | IMPLEMENTED AND VERIFIED | `providers.py`, `schema.py`; live `gpt-4.1-mini` call passed `test_live_provider.py` on 2026-10-30 (synthetic invoice) | Team chooses the production model (`OPENAI_MODEL`) |
| Untrusted document content, prompt injection | IMPLEMENTED AND VERIFIED | `test_assembly.py` injection case; the live run kept total `2.48 EUR` despite the injected line | — |
| Timeouts, rate limits, malformed output, bounded retries | IMPLEMENTED AND VERIFIED with fakes | `test_http_failures_map_to_safe_codes`, `test_network_failures_are_retryable`, `test_transient_failures_are_retried_and_bounded`, `test_malformed_output_is_retried_then_fails` | — |
| Provider call fits the 60 s lease | PARTIAL | Local experiment: `urlopen(timeout=2)` against a server sending one chunk per second finished after 6.0 s without `TimeoutError`. The comment at `providers.py` ("the socket timeout bounds the whole call") is inaccurate | Add an overall deadline and a regression test (A2) |
| Credentials, prompts, document text, response bodies out of logs | IMPLEMENTED AND VERIFIED | `test_logs_never_contain_document_values`; `ProviderError` carries only a code | — |
| Invoice, receipt, bank statement, contract through one extractor | IMPLEMENTED AND VERIFIED | `tests/extraction/evaluation/profiles/*.json`; recorded and live evaluator runs | — |
| Null instead of guesses; explicit currencies; row correspondence | IMPLEMENTED AND VERIFIED | `assembly.py`, `values.py`; `test_assembly.py`, `test_values.py` | — |
| Evidence: real unit IDs, exact quotes, no invented locations | IMPLEMENTED AND VERIFIED | `validation/evidence.py`; fabricated unit and quote tests | — |
| Decimal/date normalization only when supported | IMPLEMENTED AND VERIFIED | `validation/values.py`; ambiguity, sign and date-with-time tests | — |
| Domain validation and monetary tolerance | IMPLEMENTED AND VERIFIED | `validation/rules.py`; mismatch tests | Checks depend on conventional keys (contract has no roles) |
| Atomic persistence; retries keep row IDs; no review erased | IMPLEMENTED AND VERIFIED | run-token fencing; `test_retry_keeps_the_id_and_only_applies_to_failed_runs`, stable row ID tests | — |
| Duplicate execution and stale workers | IMPLEMENTED AND VERIFIED | concurrent worker test; `test_old_worker_cannot_overwrite_a_retried_stale_run` | — |
| Queued/running recovery | PARTIAL | Manual retry after `STALE_AFTER` (5 min): `test_stale_runs_without_a_job_can_be_retried` | `recover_terminal_extractions` NOT IMPLEMENTED (A1) |
| Evaluation with tuning and held-out splits | IMPLEMENTED; accuracy NOT VERIFIED | `evaluation.py`; recorded runs; live runs 32/32 and 51/51 (2 invented) after instruction fixes | The held-out split informed those fixes and is no longer independent; 6 synthetic documents are not an accuracy sample |
| Events `extraction.started/validation_warning/ready/failed` and retry | IMPLEMENTED AND VERIFIED | lifecycle log tests; retries use `job.retry_scheduled` | Optional `extraction.retry_scheduled` deferred by member 5 |
| Handoff | DONE, needs update | `docs/handoffs/02-extraction.md` | Add A1/A2 once implemented |
| PR into `main` | DONE (Draft) | PR #6 at `78d84d7` | CI red, see below |
| Independent review by member 1 | NOT DONE | No review, comment or report for PR #6 | BLOCKED by member 1 |

### What is and is not proven

- Fake-provider tests vs live: ordinary tests use fakes. Live calls were made only for
  `test_live_provider.py` and the evaluator, with synthetic documents and `gpt-4.1-mini`.
- Standalone vs assembled: all extraction tests run the module alone. A local,
  unpublished assembly with profiles, review and integration ran profile → extraction
  (fixture) → review confirm → JSON export once, with a stubbed document. The shared
  application has not run extraction.
- JSON export is not an eGrant write; no eGrant adapter exists.

## Checks run (2026-10-30, PostgreSQL 16 under podman, isolated `egrant_test` database)

| Command | Result |
|---|---|
| `uv run pytest tests/extraction` | 134 passed, 1 skipped (live test, disabled by default) |
| `uv run pytest` | 165 passed, 1 skipped, **1 failed**: `tests/platform/test_jobs.py::test_migration_and_transactional_enqueue` |
| `uv lock --check` | passed |
| `uv run ruff check backend scripts tests` | passed |
| `uv run ruff format --check backend scripts tests` | passed |
| Earlier today at the same head: `scripts/scan_secrets.py` on a clean checkout, `scripts/export_contract.py` drift check | passed, no drift |
| Earlier today: live `test_live_provider.py` and `evaluation --live` (`gpt-4.1-mini`) | passed; 32/32 and 51/51 (2 invented) |
| Local slow-server experiment for the provider deadline | socket timeout 2 s, call took 6.0 s; no overall deadline |

Not run in this audit: paid provider calls (already recorded above), frontend checks
(the module has no UI), and any assembled-application test (extraction is not registered).

CI for PR #6 at `78d84d7`: `make install` and `make check` pass; `make test` fails on the
migration test. On `codex/integration` that test now checks for a single head and the
presence of `0301_profiles`/`0501_submissions`, so copying it to this branch would not
make the isolated PR green either; it turns green once the module is assembled.

## Code quality notes (final-review, human-code)

- Names, comments and logs are English; no UI in this module. Comments explain the
  three-phase processing, run-token fencing, tolerance rules and stale-retry window.
- One inaccurate comment: `providers.py` claims the socket timeout bounds the whole
  call. Fixed together with A2.
- No TODOs, dead code or unused abstractions found. The lazy imports of other modules
  in `service.py` are deliberate and documented.

## Remaining work

### A. Work member 2 must implement or fix

| Priority | Action | File / interface | Done when |
|---|---|---|---|
| P1 | A1. Implement `recover_terminal_extractions(session) -> None` exactly as recorded in `contracts/internal.md` on `codex/integration`: own short transaction, lock a bounded batch of `queued`/`running` rows with SKIP LOCKED, act only when the resource's latest `extraction.process` job is `failed` and none is queued/running, set `failed` with a safe code, clear `run_token`, keep `attempt`, log `extraction.failed` after commit with the job's requestId/jobId/attempt | `backend/app/extraction/service.py`; tests in `tests/extraction/test_lifecycle.py` | The eight listed regressions pass: final-lease crash, queued after last failed attempt, newer active retry skipped, ready run untouched, concurrent sweep/retry, late worker fenced, repeat sweep is a no-op, correlated safe logs |
| P1 | A2. Enforce an overall provider deadline that keeps claim + call + persist inside the lease; correct the comment | `backend/app/extraction/providers.py` | A slow-server test raises `AI_TIMEOUT` within the deadline |
| P2 | A3. Update handoff and PR description for A1/A2 | `docs/handoffs/02-extraction.md`, PR #6 | Both list the new interface, deadline and test counts at the new head |
| P2 | A4. Decide on `docs/handoffs/report-2.md`: restore it or delete it in a commit | working tree | `git status` is clean |

### B. Verification member 2 must perform

| Priority | Action | Done when |
|---|---|---|
| P1 | Rerun module tests, lint, secret scan and contract drift at the new head after A1/A2 | Results recorded with the new SHA |
| P1 | After member 5 registers the module, run extraction inside `codex/integration`: worker processes `extraction.process`, recovery sweep runs from the worker loop | A queued extraction reaches `ready` through the real worker; a crashed final attempt ends `failed` without user action |
| P1 | After member 1 publishes documents, run one real file end to end in fixture mode and once in live mode | Stable unit IDs; the shared CSV yields `row-1`…`row-4`; review opens evidence by unit ID |
| P2 | Build a fresh held-out set before quoting any accuracy | Live evaluator run on documents not used for tuning |

### C. Publication and review actions

| Priority | Action | Done when |
|---|---|---|
| P1 | Commit and push A1/A2 to `codex/extraction` | PR #6 shows the new head; CI `make check` green |
| P1 | Ask member 1 to review PR #6 at that exact head with `docs/team/06-PEER-REVIEW.md` | A report for the exact head SHA exists |
| P1 | Address review findings, then mark PR #6 ready for review | PR #6 not Draft; no open blocking finding |
| — | Review owed to member 3 | Done: PASS for `e845099`, which is still the head of PR #8 and the commit member 5 assembled |

### D. Work other members must do

| Priority | Owner | Action | Done when |
|---|---|---|---|
| P0 for the product | Member 1 | Publish `app.documents.service.get_normalized` with stable unit IDs | Branch and PR exist; extraction can load a real document |
| P1 | Member 1 | Independent review of PR #6 | Report for the exact head |
| P1 | Member 5 | After review: replace the four `/extractions` shells, register `process_extraction`, add `0201_extractions` to the merge revision, compute `aiConfigured`, call `recover_terminal_extractions` in the worker loop | Assembled tests run extraction through production routes and worker |

### E. External access and documentation

- Production model choice for `OPENAI_MODEL` (team decision); live checks so far use
  `gpt-4.1-mini`.
- The OpenAI and OpenRouter keys were shared in a chat and should be rotated after the event.
- Permitted real documents for evaluation; eGrant OCR access (member 1).

## Update after the audit

A1 and A2 are implemented in the commit that follows `78d84d7` on `codex/extraction`:

- `recover_terminal_extractions(session)` in `backend/app/extraction/service.py`, with
  nine regressions in `tests/extraction/test_recovery.py`. With the function body
  disabled, seven of them fail; the other two check that nothing is touched.
- `providers.post_within` enforces the 40-second overall deadline. Two tests against a
  local HTTP server cover a slowly sent reply (`AI_TIMEOUT` before the deadline plus
  margin) and a prompt reply. With the old direct `urlopen` call the slow-reply test fails.
- `uv run pytest tests/extraction`: 145 passed, 1 skipped. `uv run pytest`: 176 passed,
  1 skipped, 1 failed (the same migration test). Ruff and `uv lock --check` passed.
  One paid live call (`test_live_provider.py`, `gpt-4.1-mini`) passed through the new path.

The independent review by member 1 must cover the new head, not `78d84d7`. Member 5
still needs to call the sweep from the worker loop after that review.
