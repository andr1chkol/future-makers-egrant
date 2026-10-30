# Member 5 integration handoff

Repository: <https://github.com/andr1chkol/future-makers-egrant>.
Working branch: `codex/integration`. Target: `main`. PR: #4.
Baseline: `bootstrap-v1`, `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8` (unchanged).
Self-reviewed published assembly code: `a00989b108988d2a2a66f4a4ced4611f24f0be0a`.
Tested local assembly: `dbf2d8cecea490506d2f88b687f72e377dc61a5b`.
Both have tree `b828e0f79295b70f8b1cd83b6300a5aed8790047`.
The follow-up handoff commit changes documentation only. Member 4 must review
its actual final PR head; the old review of 0816377 does not approve this head.

Verdict for a00989b: **implemented profiles/export assembly is ready for renewed
independent review**. The complete product is **NOT READY**. Review and extraction
lack independent verdicts; documents is unpublished. Their code is not registered
or replaced with hidden fixtures. No final integration PR was merged into main.

## Actual module disposition

| Module | Source/integrated commit | Review evidence | Current tests | Remaining blocker |
|---|---|---|---|---|
| Recovery fix #5 | 07576383dbf81b6970d58f644f36a3f359fd4fd6, merged into integration at 9d28ff377729bcc1e67e1990284d96a88f17b572 | Member 4 reproduced P2 at old 0816377; supplied and tested fix. Report records ongoing-chat procedural limitation | 8 recovery tests pass, including 3 new correlated-log cases | New assembled PR head needs member 4 review |
| Profiles #8 | e84509990a84e3121b79b7cd0681912230a61887, preserved as parent of a00989b | Member 2 PASS for exact e845099; reports copied unchanged into docs/reviews | 50 module backend tests, 25 module frontend tests, 3 profile browser scenarios; additional assembly tests | Real eGrant form format remains unverified |
| Submission/export #4 | Existing implementation plus recovery fix and a00989b registrations | Old 0816377 verdict was CHANGES REQUIRED; P2 fix now included. No new independent PASS claimed | 41 integration tests, 4 browser scenarios; public profiles-to-export probe uses real PostgreSQL | New exports need real review/extraction services |
| Human review #3 | 133e6ced9cbce21fb255fa77b45d3d335c47ec75, not merged/registered | No independent verdict/report found; member 3 review requested on PR | Owner reports 23 backend, 10 frontend, 3 browser tests; not rerun as assembled behavior here | Exact-head independent review, then router/models/0401 migration/browser registration |
| Extraction #6 | 78d84d780aedde04cae35a86b2774255d202ed0d, Draft, not merged/registered | No independent verdict found; assigned reviewer member 1 | Owner reports 134 ordinary tests; not rerun as assembled behavior here | Review, terminal-job recovery implementation, handler/router/migration/capability registration |
| Documents/OCR | No published source/PR found | None | No module tests available | Owner publishes implementation/handoff; normalized-unit compatibility; permitted provider access |

Formal GitHub review lists are empty; the profiles PASS is a repository report,
not an invented GitHub approval. Its reviewed SHA exactly matches PR #8. PR #8
remains open against main; its reviewed source was assembled in codex/integration
without merging that PR into main. PR #5 targeted codex/integration and was
explicitly accepted after inspecting its diff, green CI and running recovery
tests. Local histories and original commits were retained; no force push/reset.

## Registered production behavior

The seven form/profile shells are removed from app.platform.routes. The actual
app.profiles.routes.router is included with the shared access dependency. Its
existing ProfilesPage/ProfileEditorPage entrypoints are reached by the existing
frontend router. Form import, complete original JSON preservation, configurable
scalar/table mappings and immutable versions use the actual services/database.
Imports remain visibly illustrative; no real eGrant form-export compatibility is
claimed. The two low profile findings remain owner follow-ups: UUID list ordering
and preserved whitespace in option keys. No option values were silently changed.

The three submission routes remain protected and build payload server-side from
the exact confirmed revision, pinned profile/form mapping, complete keys/rows,
required values, permitted options and warning acknowledgements. A PostgreSQL
unique key and canonical intent hash resolve concurrent duplicate requests and
reject changed intent. Failed validation/serialization rolls back. Stored payloads
survive upstream module unavailability; repeated JSON downloads return the same
human corrections. Exported records mean a response was served, not an eGrant write.

Public app.integrations.service functions remain synchronous:

```python
create_submission(session: Session, request: CreateSubmission, idempotency_key: str) -> Submission
get_submission(session: Session, id: UUID) -> Submission
export_submission(session: Session, id: UUID) -> SubmissionPayload
apply_submission(session: Session, id: UUID) -> None
recover_interrupted_submissions(session: Session) -> None
```

Create/export/apply/recovery own short transactions with a fresh Session; reads
never commit. Shared safe errors/envelopes, generated client and public DTOs are
retained. New tests use real profile/form public reads after creating version 2
with a different mapping, then prove export still uses extraction-pinned version
1 and includes the human purchase-order correction. Only missing review/extraction
reads are explicit test doubles. This is not a full extraction/review workflow.

Wire schemas, examples and generated TypeScript are unchanged. Contract generation
preserves file ordering when parsed OpenAPI is equal; any actual schema change
still writes a new artifact and fails drift checks until coordinated. The runtime
OpenAPI equality and module request/response compatibility tests still pass.

## Database and shared infrastructure

Registered metadata: platform, integrations and profiles models. Shared Alembic
version_locations includes backend/migrations/versions and
backend/app/profiles/migrations, using newline-separated paths. New no-op merge
revision 0502_profiles_assembly joins 0301_profiles and 0501_submissions. Published
0001_platform, 0301_profiles and 0501_submissions are unchanged. There is exactly
one current head. The migration test verifies actual heads, required ancestors,
all platform/profile/submission tables and transactional enqueue rollback; it
no longer assumes a bootstrap-only head.

Do not create a merge revision referencing absent 0201/0401 yet. Once their
reviewed modules land, register their owned locations/models and add a new merge
revision joining them with 0502. Do not rewrite 0502 after publication.

Pytest uses importlib collection to avoid basename collisions such as module
files named test_routes.py. The old profile test fixture/harness no longer mounts
the router a second time: it tests production create_app directly. The browser
harness checks an egrant_test database name and applies production migrations,
so a new CI database does not depend on a previous pytest run. The unavailable-
owner submission test injects an explicit unavailable public read instead of
assuming an owner package can never be installed.

No runtime dependency or lock was changed. Fixtures are test/reference data only.
The gate remains a single-workspace HttpOnly-cookie demo with Origin checks;
it is not eGrant identity or tenant isolation. Secrets are server-side. Document
content and financial values never become logs or frontend bundle configuration.

## Worker recovery, logging and member-2 coordination

submission.apply is registered explicitly. Document/extraction handlers remain
explicit unavailable handlers. One durable queue retains leases, fencing and
bounded retries. The accepted #5 fix selects one deterministic failed job per
recoverable submission, locks only submission rows and emits logs after commit
with the stored requestId/jobId/attempt. Repeat recovery produces no duplicate
transition. Interrupted applying -> unknown; undispatched terminal work -> failed.
There is no automatic remote write/retry or fake submission.applied event.

The JSON logger now permits UUID profileId/formId and numeric version, in addition
to revision and existing IDs/attempt/duration. Real HTTP profile creation/versioning
tests capture formatted JSON, check both request IDs and versions and prove names
are absent. Shared redaction, access and job-correlation tests pass.

Member 2 supplied the extraction requests in this chat: four shell replacements,
process_extraction registration, migration heads, terminal-job recovery and
aiConfigured from OpenAIProvider.from_settings. Shared registrations belong to
member 5 and need no separate duplicate scaffold/shared-files branch.

The proposed owner interface is recorded in contracts/internal.md:

```python
# Pending implementation/review in app.extraction.service
recover_terminal_extractions(session: Session) -> None
```

Member 2 owns the domain transition; member 5 will call it in the worker polling
loop using a fresh Session. It must lock a bounded batch with SKIP LOCKED, handle
queued/running runs with terminal failed jobs, and skip every resource with an
active queued/running job, especially a newer manual retry. Invalidate run_token,
mark failed with a safe code, preserve confirmed data and log original correlation
after commit. Do not reset the attempt budget or silently issue more paid calls.
Required regressions: final-lease crash, queued after last failed attempt, newer
retry, ready result, concurrent sweep/retry, late token, repeat sweep and safe logs.
This interface is pending, not implemented/registered here. Existing manual retry
is owner behavior. No private extraction table write was added by integration.

Lease is 60 seconds, current provider socket timeout 40 seconds. The provider code
was inspected: a socket timeout alone does not prove an end-to-end deadline across
body reads, parsing and validation. Member 2 must verify delay behavior before
claiming the whole handler always fits its lease. No renewal is claimed.

After independent review, member 5 will register process_extraction and compute
aiConfigured from the actual configured adapter. Optional separate retry vocabulary
is deferred; current job.retry_scheduled events remain. The corrected migration
assertion is on integration; it does not magically make the isolated Draft #6 CI
green. Member 2 must synchronize the reviewed shared changes or request a scoped
backport and rerun that exact head. A subsequent module code change needs renewed
review. No unreviewed module is merged into main to hide a red check.

## Verification on 2026-10-30

All final commands below exited 0. Local Python 3.12.6, uv 0.13.6, Node 26.5.0,
PostgreSQL 16 and Chromium; Compose frontend uses Node 22.

| Check | Actual result and limit |
|---|---|
| make check | PASS: lock validation, Ruff/format, tracked-secret scan, runtime OpenAPI/generated-client compatibility, strict TypeScript/Vite build |
| make test | PASS: 123 backend tests = 32 platform + 50 profiles + 41 integration; 26 frontend tests = 1 platform + 25 profiles |
| Recovery regression subset before accepting #5 | PASS: 8 tests including original request/job/attempt on both terminal states and deterministic selection |
| Profile/export assembly | PASS: production protected routes, persisted versions, formatted logs, pinned mapping after later edit and exact human correction |
| make e2e | PASS: 3 foundation Chromium scenarios |
| make e2e-integration | PASS: 4 submission/history scenarios; explicit neighboring doubles, real submission HTTP/DB/download |
| make e2e-profiles | PASS: 2 UI-adapter scenarios + 1 real production UI/API/PostgreSQL workflow with invoice/travel forms, versions, reload and narrow layout |
| Clean local clone | PASS: locked install/check/test/all 10 browser scenarios; no tracked/untracked changes afterward |
| Empty-volume Compose | PASS: healthy API/DB, worker/frontend running, head 0502_profiles_assembly; real forms/profiles lists empty; provider capabilities all false |
| Final-head GitHub CI | See PR #4; do not infer a remote result from local checks |
| Full upload/normalization/extraction/review/draft reload/confirm/export | NOT VERIFIED: review/extraction review gates and unpublished documents block assembly |
| Live OCR/AI and real eGrant write/timeout/reconciliation | NOT VERIFIED in this integration; no live request or external write performed |

The first profiles-only assembly had duplicate operation-ID warnings because the
module test harness still mounted a now-registered router. It was corrected to use
production assembly; final tests have no duplicate warnings. A new browser DB also
needed its own migration step, now handled by the guarded test server. Remaining
non-failing warnings: legacy separator configuration in the unchanged owned
profiles Alembic config, Starlette/httpx deprecation, terminal colors and optional
host fsevents install-script notice. No warning is hidden as a passing live test.

Commands in the main checkout:

```sh
export UV_CACHE_DIR=/private/tmp/egrant-integration-uv
make check UV=.tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_integration make test UV=.tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_integration make e2e
INTEGRATION_E2E_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_e2e_integration make e2e-integration
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_profiles_fresh make e2e-profiles
```

The dedicated egrant-integration-test container exposes PostgreSQL on 55435;
test databases were created explicitly. The fresh profile browser DB began with
no schema and was migrated by its harness. No test used the Compose demo DB.
Clean clone: /private/tmp/egrant-profiles-verify-dbf2d8c, cloned locally with
--no-hardlinks at dbf2d8c. make install/check/test used the existing pinned uv
executable by absolute path; the cloned app imported only its own source and
independent .venv. All suites were rerun there. Compose used copied .env.example,
new project egrant-profiles-verify-dbf2d8c, DB_PORT=55437 and new volumes.

Git CLI previously lacked HTTPS push credentials. Publication uses the connected
GitHub API with identical tested tree, a non-force expected-SHA update and both
parents: accepted recovery merge 9d28ff3 and reviewed profiles e845099. Thus module
history is retained in the published integration commit. Original local commits
are preserved. The final documentation commit does not change executable code.

## Provider matrix and manual reproduction

| Capability | Classification |
|---|---|
| Form import/profile configuration | Local/fixture verified through real HTTP/PostgreSQL; real eGrant format unavailable |
| Confirmed export and status | Boundary verified with real persisted submissions/profiles; review/extraction reads are explicit doubles in tests |
| Source normalization/OCR | Unavailable: documents not published |
| AI extraction | Unregistered; owner reports synthetic OpenAI runs with gpt-4.1-mini, not rerun/claimed as assembled evidence here |
| eGrant identity/application writes/current-state/receipt lookup | Unavailable, capability=false; mode=egrant returns 503 without enqueue |

Follow README on codex/integration, then open /profiles. Import either JSON in
 tests/profiles/examples, configure scalar/table destinations, save, edit to v2,
reload and select v1 to verify immutability. The fixture/illustrative banners stay
visible. Trial is disabled with an explicit missing-document/extraction message.
/history reports unavailable rather than inventing records.

Use make e2e-integration to demonstrate persisted JSON download with exact human
corrections. Use make e2e-profiles to demonstrate two distinct real form/profile
configurations. The adapter browser scenario and boundary probes must be labeled
as such. The second one is not a document-to-export demo.

Full demo remains gated: real upload -> normalized evidence -> pinned extraction
-> source/field/table review -> save/reload -> explicit confirmation -> JSON
containing the human correction. Then exercise another profile, missing values,
provider failure, duplicates, stale revisions and repeated intent. Actual eGrant
apply additionally needs documented application-data semantics, authorized test
target, known-state overwrite safeguards and explicit human confirmation.

## Final review and release gates

Applied human-code, backend-reliability-review and final-review to the actual
baseline-to-assembly diff, public interfaces, queue, migrations, tests and UI.
Inspected profiles' existing implementation and unchanged runtime source against
its exact-head independent report. Fixed shared registrations, duplicate harness
mounting, schema-order churn, migration discovery/head assertions, test collection
mode and new-DB browser startup. Inspected desktop/mobile test captures. Applied
humanizer only to technical documentation, preserving code/commands/evidence.

For a00989b: no unresolved in-scope defect was found in the registered profiles /
submission boundary after those fixes and checks. This is author self-review;
member 4 must independently review the new complete PR #4 head. The earlier
0816377 CHANGES REQUIRED remains historical, with its recovery finding resolved
by accepted #5. No PASS for the newly assembled release is claimed.

Release procedure is docs/team/07-RELEASE-REVIEW.md. Member 1 performs it on the
exact final main SHA only after modules are independently reviewed, assembled,
heads reconciled and the full workflow verified. There is no final assembled main
SHA to review yet. Member 4 remains the requested integration reviewer; source
review/extraction owners must obtain member 3/member 1 verdicts respectively.
No new chat, deployment, final main merge or live application write was created.
