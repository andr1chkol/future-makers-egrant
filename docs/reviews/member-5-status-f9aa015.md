# Member 5 contribution audit

Audit date: 2026-10-30, Europe/Bratislava.
Assignment: shared platform, assembly, confirmed export, integration and release.
Repository: https://github.com/andr1chkol/future-makers-egrant.
Branch: codex/integration. PR: https://github.com/andr1chkol/future-makers-egrant/pull/4.
Local audited HEAD: f9aa0152c444262a733913d3e185e67b2510c7fd.
Published PR head: 74da1644f058f21e5eaf268406368a3e42904a25.
Both trees: fd7f72817b7a4ca934a6d9adb73df6136a7d9edb.
Target main/baseline: 88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8.

## Verdict and scope

For the two exact heads above: the implemented platform, profiles registration
and confirmed-export boundary are ready for scoped independent review. The
complete member-5 assignment and assembled product are not complete. Documents,
extraction and human review are unavailable in production assembly; complete
workflow and live-provider acceptance cannot be claimed from the passing tests.

This is the author's status audit, not independent peer review or release approval.
No new data-loss/startup defect was reproduced in the implemented scope. A required
observability detail remains incomplete: failure/recovery events do not include
durationMs. The larger blockers are missing registrations/dependencies and absent
full-workflow evidence. Source changes, contract changes, PR merges, deployments,
paid calls and external application writes were outside this audit and were not done.
Only this English report was created; it is intentionally uncommitted/unpublished.

Applied human-code and final-review to the actual baseline-to-HEAD diff and relevant
callers, transactions, queue, access, metadata/migrations, tests and UI. Applied
humanizer to this report in technical voice, preserving facts and commands.
No stylistic AI score was used. Existing handoff/review evidence was read and
checked against current source, remote heads and newly executed checks.

## Publication and review facts

- Working tree was clean at entry. Origin is the expected GitHub repository.
- Local history is seven commits ahead and three behind origin/codex/integration,
  because source commits were preserved while equivalent trees were published
  with the GitHub connector. git diff HEAD origin/codex/integration is empty.
  This is history divergence, not missing published source. Do not force-push it.
- PR #4 exists, is open/non-Draft and targets main. Its current head is 74da164.
- Exact-head GitHub Actions run 41050214602 completed successfully:
  https://github.com/andr1chkol/future-makers-egrant/actions/runs/41050214602.
- PR #4 has no formal GitHub reviews/comments. Member 4 (postaichukx) is requested.
- Member 4's report for 0816377 records CHANGES REQUIRED for recovery correlation
  and an ongoing-chat procedural limitation. PR #5 fixed that issue and is merged
  into integration at 9d28ff377729bcc1e67e1990284d96a88f17b572. Eight recovery
  regressions pass now. That old report is not a PASS for 74da164.
- Profiles source e84509990a84e3121b79b7cd0681912230a61887 is included in integration;
  its exact-head independent PASS is docs/reviews/profiles-e845099.md. The profile
  logging request is implemented, despite older report wording describing it as
  outstanding at that earlier source baseline.
- Review PR #3 is open at 133e6ced9cbce21fb255fa77b45d3d335c47ec75. No independent
  verdict is available locally or in the inspected remote review records.
- Extraction PR #6 is Draft at 78d84d780aedde04cae35a86b2774255d202ed0d. No independent
  verdict is available. Its code/recovery/provider behavior is not assembled here.
- No documents PR/branch/handoff was found among current remote refs and PRs #1-8.
- Integration is not merged into main. Main still contains bootstrap, not the
  current profiles/export assembly. An open PR is not delivery of the product.
- Member 5 still owes independent review of member 1's documents implementation
  once its exact PR/head is published. There is currently no documents PR to review.

## Acceptance checklist from 05-INTEGRATION-PROMPT.md

The classifications below apply to the audited source, not promised future work.
"Verified" means the named local checks or inspected exact-head CI provide evidence
for that bounded behavior. It does not turn a test double into a live integration.

| Requirement | Classification | Evidence | Remaining action |
|---|---|---|---|
| Shared PostgreSQL settings/sessions/storage/errors | IMPLEMENTED AND VERIFIED | backend/app/platform/{settings,database,storage,errors}.py; tests/platform/test_access.py and test_logging_storage.py | Retest after final module assembly; do not replace existing platform |
| Cookie gate, trusted Origin, protected APIs/content | IMPLEMENTED AND VERIFIED | access.py; main.py middleware/router dependencies; access tests and submission 401 checks | Real document-content implementation still belongs to member 1; tenant/eGrant identity is not provided |
| One durable queue, leases, bounded retries and late-worker fencing | IMPLEMENTED AND VERIFIED | platform/jobs.py:40-138; tests/platform/test_jobs.py | Domain handlers must honor the 60-second lease or adopt a coordinated solution |
| All three real job handlers connected | PARTIALLY IMPLEMENTED | worker.py:15-19 registers real submission.apply, unavailable document/extraction handlers | Register reviewed owners' process_document/process_extraction |
| HTTP outside long DB transactions | IMPLEMENTED AND VERIFIED for current export scope | integrations/service.py owns short transactions and makes no external HTTP call | Verify actual provider call boundaries once domain modules/adapter land |
| Shared DTOs, generated client, locks, schemas/examples | IMPLEMENTED AND VERIFIED | contracts/api.yaml parsed; runtime OpenAPI equal; platform contract tests; make check | Any later change must update examples/client/consumers together |
| Reconciled migrations for present modules | IMPLEMENTED AND VERIFIED | backend/alembic.ini, migrations/env.py and 0502_profiles_assembly; head/ancestor/table test | Add owned document/extraction/review locations and a new merge revision after review; never rewrite published revisions |
| Profiles router/models/page registration | IMPLEMENTED AND VERIFIED | main.py:141; profile shells removed; actual profile routes tested; profile E2E | Preserve the already-reviewed runtime module; no rewrite needed |
| ReviewPage and protected review router assembled | BLOCKED BY ANOTHER MEMBER OR EXTERNAL ACCESS | platform/routes.py:89-101 are 503 shells; frontend review entrypoint is a shell; PR #3 review pending | Member 3 reviews #3; member 5 then registers router/models/0401 migration and browser suite |
| Upload and document normalization assembled | BLOCKED BY ANOTHER MEMBER OR EXTERNAL ACCESS | platform/routes.py:28-66; upload shell; no documents source/handoff published | Member 1 publishes module; member 5 reviews it independently and registers it |
| Extraction assembled and terminal runs recovered | BLOCKED BY ANOTHER MEMBER OR EXTERNAL ACCESS | extraction shells at routes.py:69-86; worker unavailable; internal.md:196-234 only proposes recovery | Member 2 implements public recovery; member 1 reviews module; member 5 connects handler/router/capabilities |
| Shared navigation, controls, QueryClient, client, fixture display | IMPLEMENTED AND VERIFIED | frontend/src/app/{App,main,styles}; shared/{ui,api}; foundation/profile/browser tests | Verify real full workflow after neighboring pages become functional |
| History with genuine empty/loading/error/responsive states | PARTIALLY IMPLEMENTED | HistoryPage.tsx:14-96; E2E explicitly mocks returned extraction records | Connect real extraction list and verify real persisted processing history; no fixture insertion |
| Submission/status/download page | IMPLEMENTED AND VERIFIED | SubmissionPage.tsx; 4 submission browser scenarios | Applied/unknown remote status is not live-verified; retain safe no-repeat warning |
| Server-built payload from exact confirmed revision/pinned mapping | IMPLEMENTED AND VERIFIED at the boundary | integrations/service.py:49-64; payload.py; 30 submission cases plus 3 profiles-assembly cases | Actual review/extraction reads are test doubles until owners land |
| Reject draft/stale/invalid/unknown mapping and preserve human corrections | IMPLEMENTED AND VERIFIED at the boundary | test_unconfirmed_and_stale_reviews_leave_no_operation, test_invalid_mapping_and_values_are_rejected, pinned-profile export test | Repeat using actual review/extraction services; saved draft is not confirmed data |
| Store operation/hash atomically; concurrent Idempotency-Key semantics | IMPLEMENTED AND VERIFIED | models.py:23-24; service.py:30-93; identical/changed concurrent intent and rollback tests | Preserve existing logic; do not rebuild it |
| Durable JSON export independent of eGrant | IMPLEMENTED AND VERIFIED | service.py:114-125; routes.py:35-51; download/reload/dependency-loss tests | Real confirmed-flow acceptance awaits missing modules; exported is not applied |
| Honest unavailable eGrant capability | IMPLEMENTED AND VERIFIED | main.py:126-134; service.py:47-48; mode=egrant returns 503 without job/operation | Keep disabled until a documented adapter and safeguards exist |
| Real eGrant application-data adapter/outbox/apply/receipt reconciliation | NOT IMPLEMENTED | No provider call/outbox creation path; apply_submission is defensive terminal-state handling only | Obtain interface/authorized target, then implement durable pre-effect intent, adapter and receipt/current-state reconciliation |
| Safe append/replace external semantics/preview/acknowledgement | BLOCKED BY ANOTHER MEMBER OR EXTERNAL ACCESS | payload may retain writeMode metadata; there is no remote current-state/preview adapter | Require documented semantics/current state and explicit human confirmation; export metadata is not a remote write |
| Unknown after possible remote write; no blind duplication | PARTIALLY IMPLEMENTED | Seeded eGrant applying states become unknown; one-attempt queue and restart tests | Test an actual documented adapter timeout/reconciliation; seeded states are not remote evidence |
| Shared JSON logger, redaction, correlation and profile/review context | IMPLEMENTED AND VERIFIED for tested fields | platform/logging.py:41-108; recovery 8 tests; formatted profile and submission log captures | Keep raw document/prompt/provider/credential data out; member-4 correlation defect is resolved |
| Complete transition duration/event evidence | PARTIALLY IMPLEMENTED | submission.prepared has durationMs; service.py:148/201 failure/recovery logs and jobs.py:109 retry logs omit it | Define truthful duration semantics and add missing required fields/assertions; do not emit fake applied events |
| Release README/env/matrix/demo/evaluation links | PARTIALLY IMPLEMENTED | README, .env.example, INTEGRATION-HANDOFF.md include current startup, matrix and bounded demos | Complete actual assembled demo, module evaluation references and final release checklist after assembly |
| Full workflow/failure matrix with real modules | NOT IMPLEMENTED as an assembled test | tests/e2e/serve_submissions.py:55-58 substitutes all neighboring public reads; profiles assembly test substitutes review/extraction | Add real fixture flow and cases for duplicate upload, draft reload, missing values, provider failures, stale revisions and another profile |
| Clean-clone startup/migrations | IMPLEMENTED BUT NOT VERIFIED by a fresh clone/Compose run in this audit | Exact-head CI succeeded; handoff records historical clean-clone/empty-volume startup; fresh audit tests migrate new test databases | Repeat README from a clean clone/empty DB at final assembled release SHA; no claim of fresh audit Compose verification |
| Independent integration review/release review | BLOCKED BY ANOTHER MEMBER OR EXTERNAL ACCESS | No exact-current-head member-4 verdict; no complete assembled main SHA | Member 4 reviews 74da164/current successor; member 1 reviews final assembled main later |

## Tests executed again during this audit

Commands were inspected in Makefile/configs before execution. Docker was available;
the dedicated egrant-integration-test PostgreSQL 16 container was started. Three new
isolated databases were created; no working/demo application database was reset.
The root fixture resets only the explicitly supplied egrant_test database.

```sh
docker start egrant-integration-test
docker exec egrant-integration-test createdb -U egrant egrant_test_audit5_f9aa015
docker exec egrant-integration-test createdb -U egrant egrant_test_e2e_audit5_f9aa015
docker exec egrant-integration-test createdb -U egrant egrant_test_profiles_audit5_f9aa015
UV_CACHE_DIR=/private/tmp/egrant-integration-uv make check UV=.tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_audit5_f9aa015 UV_CACHE_DIR=/private/tmp/egrant-integration-uv make test UV=.tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_audit5_f9aa015 make e2e
INTEGRATION_E2E_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_e2e_audit5_f9aa015 make e2e-integration
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_profiles_audit5_f9aa015 make e2e-profiles
```

| Check | Fresh audit result |
|---|---|
| make check | Exit 0: locks, lint, formatting, secret-pattern scan, OpenAPI/client drift, TypeScript and Vite build |
| make test | Exit 0: 123 backend tests (32 platform, 50 profiles, 41 integration); 26 frontend tests |
| make e2e | Exit 0: 3 foundation Chromium scenarios |
| make e2e-integration | Exit 0: 4 submission/history Chromium scenarios |
| make e2e-profiles | Exit 0: 2 mocked UI scenarios and 1 actual profile API/PostgreSQL browser scenario |
| Runtime OpenAPI comparison | Parsed complete contract equals create_app().openapi(); 22 paths; submission/capability DTOs inspected |
| Source publication parity | git diff HEAD origin/codex/integration exited 0; equal tree hashes |
| Whitespace | git diff --check exited 0 |
| Remote CI | Exact published head run 41050214602 completed success; independently read from GitHub |

No check failed in this audit. Existing Starlette/httpx, owned profile Alembic
separator deprecations and terminal-color warnings remain visible. Backend test
counts include pure validation cases; not every backend test touches PostgreSQL.
Concurrency, rollback, migration, session and persisted-submission cases do.
The submission browser server uses explicit test doubles. Profile UI/API browser
checks use actual profiles routes/database, with other domains unavailable.

Not performed: fresh clone/install/Compose in this audit; review/extraction module
suites from their unmerged branches; actual document upload/normalization; real
assembled draft save/reload/confirmation; full flow/duplicate/provider-failure
matrix; paid OCR/AI calls; eGrant writes/timeouts/receipt reconciliation; deployment;
independent member-4 review; member-1 final release review. Historical handoff or
owner results for these are not relabeled as fresh audit passes.

## Logging, readability and review findings

English names/comments/docstrings/technical errors/log events match project
conventions in the inspected member-5 code. User UI strings are Slovak. Payload
preview is React text, not executable HTML. No financial/document data is sent to
console storage by the status/history pages. Comments explain transaction ownership,
uncertain outcomes, immutable mapping, queue leases and idempotency. The small
public-service resolver handles absent owner modules explicitly rather than loading
fixtures. Existing abstractions do not require replacement for this scope.

Fresh tests captured formatted safe JSON with request/job/attempt/submission/profile
IDs, safe codes and redacted exception details. They assert that key markers,
personal filenames, document values, cookies and financial markers do not enter
logs. Source schema/client/payload fields have no frontend credential configuration.
The tracked-file secret-pattern scan passes; it is not a proof against every secret
format or an audit of every ignored local file.

Resolved: old P2 recovery correlation, profile/form/version logger allowlists,
profile router duplication in test harnesses, bootstrap-only head assertion and
browser startup on a new profile database. These do not need reimplementation.
Outstanding own completeness gap: transition/retry duration fields above. Missing
submission.applied logging is expected while there is no real applied path; adding
a fake event would be wrong. No source fix was made because this is an audit.

## Exact remaining-work plan

### A. Work member 5 must implement or fix

| Priority | Concrete action / interface | Owner and prerequisite | Observable completion criterion |
|---|---|---|---|
| P0 | Replace three review shells; include app.reviews.routes.router; import models; discover owned 0401 migration; run its actual browser suite | Member 5 after member 3's exact-head review of #3 | Draft/edit/confirm routes reach actual services under access gate; no duplicate route IDs; real saved correction can feed export |
| P0 | Replace four extraction shells; register process_extraction and public terminal recovery; compute aiConfigured from the actual adapter | Member 5 after member 2's recovery implementation and member 1's exact-head review | Real job reaches ready/failed; terminal jobs leave no orphan queued/running run; newer manual retries survive; capability follows configured adapter |
| P0 | Register published documents router/models/migration/process_document | Member 5 after reviewing member 1's published module | Upload/private content/normalization/retry work; fixture source units agree with extraction expectations |
| P1 | Add a new merge revision over current 0502 and newly reviewed module heads | Member 5 after modules are present | Exactly one head; required ancestor revisions/tables exist on empty DB and upgrade path; published history unchanged |
| P1 | Complete required transition/retry timing evidence in integrations/service.py and platform/jobs.py | Member 5; independent of other modules | Applicable emitted events carry a documented durationMs meaning and safe correlation; behavior/log assertions pass |
| P1 | Implement the actual eGrant adapter/outbox/reconciliation only if delivery requires live apply | Member 5 after external interfaces/authorization below | Operation+intent/job durable before call; real receipt/state reconciliation resolves unknown; no duplicate write or unsafe replace. Otherwise document capability=false and export-only limit |
| P1 | Update README/handoff/demo/evaluation references after actual assembly | Member 5 after real flow verification | Teammate can reproduce the stated demo without test doubles being mistaken for product adapters; provider matrix matches evidence |
| P2 | Reconcile local/remote equivalent histories through an agreed non-destructive process if ordinary Git synchronization is needed | Member 5; preserve existing local commits | Source tree remains unchanged and no force push/reset discards provenance. No content push is currently missing |

### B. Verification member 5 must perform

| Priority | Concrete verification | Owner / affected interface | Completion criterion |
|---|---|---|---|
| P0 | Real fixture upload -> normalize -> pinned extraction -> edit scalar/row -> save/reload -> explicit confirm -> download JSON | Member 5 with real owner services and worker | Persisted human corrections/row UUIDs appear in exact export; drafts/stale revisions rejected; no neighboring read doubles |
| P1 | Another profile, missing required value, duplicate file, provider failure, stale revisions, repeat intent and worker restart | Member 5 plus owners fixing their defects | Actual shared browser/API/DB cases pass; retries cannot duplicate operations or leave unowned work |
| P1 | Lease/provider delay test, terminal recovery/new retry race and late worker | Member 5 + member 2; jobs.py/public recovery | Bounded retry and token fencing hold under delays; no unsupported 40-second-socket-equals-whole-deadline claim |
| P1 | All shared/module suites and runtime contract/access/log checks after registration changes | Member 5 | Actual commands pass on the assembled exact head; duplicates, fake fallbacks and schema drift absent |
| P1 | Clean-clone README install/Compose/migrations on final assembled SHA | Member 5 | New clone/empty database starts with one head; actual flow works; documented setup contains every prerequisite |
| P1 | Authorized live OCR/AI and any permitted eGrant test separately | Member 5 + owners after access is supplied | Live evidence records permitted input/mode/results; fixture evidence remains separate; no unapproved write |

### C. Publication and review actions

1. P1, member 5: give member 4 the exact current PR #4 head and audit report. The
   request already exists; completion is a fresh independent report for that
   exact head, not the historical 0816377 report. A later code commit needs a
   new verdict. Scoped review can start now; complete assignment acceptance cannot.
2. P1, member 5: independently review member 1's documents PR when published,
   following docs/team/06-PEER-REVIEW.md. Completion is a recorded reviewed SHA,
   tests/findings and resolved blockers. This is an outstanding reciprocal duty.
3. P1, member 5: publish only intended follow-up changes to codex/integration and
   update PR #4 with actual test/provider evidence. Current intended source is
   already published despite different local commit identities. This audit file
   is local only and needs a separate explicit publication decision.
4. P1, team + member 5: arrange independent review/checks before final main merge;
   then member 1 runs docs/team/07-RELEASE-REVIEW.md on exact assembled main SHA.
   Completion is a supported release verdict. No final main merge was authorized
   or performed by this audit.

### D. Work other members must do

- P0, member 1: publish documents/uploads/normalization/OCR module and handoff,
  stable source-unit behavior and failure tests. There is no source for member 5
  to register/review yet. Member 1 also owes extraction's independent review.
- P0, member 2: implement/verify recover_terminal_extractions(session), including
  newer active retry protection, late-token invalidation and safe correlated logs;
  address provider/lease timing evidence, prepare #6 for review and coordinate its
  red standalone migration check with shared changes. Member 5's integration test
  fix does not alter that separate source branch's CI automatically.
- P0, member 3: independently review human-review PR #3 at its actual head.
- P1, member 4: review new member-5 assembled head; old recovery findings are fixed
  but do not approve new source. Member 4 owns any substantial review-module defects.
- P1, each domain owner: fix their own substantive bugs found during assembly.
  Member 5 coordinates shared registrations; it should not rebuild their modules.

### E. External access/documentation still needed

- P1, team/user + provider owners: permitted real documents, actual eGrant form
  exports and data-handling/model/budget decisions; configured authorized OCR/AI
  access. None is verified by the current fixture tests.
- P1, eGrant owner/team: documented application-data write interface, append/replace
  semantics, known-state/preview and receipt/reconciliation interface, authorized
  test application and credentials. Form-structure editing is not value insertion.
- P1, human applicant/operator: explicit confirmation before any external write;
  safe overwrite acknowledgement where applicable. No authorization is inferred
  from requesting this audit.
- P1, team/user: exact submission deadline/timezone/channel and evaluation target.
  Team instructions still identify these as inputs to obtain; a source PR is not
  a hackathon submission or deployment.

## Five next actions in execution order

1. Obtain member 3's review of #3 and member 2's reviewed recovery-capable #6;
   ask member 1 to publish documents. Coordinate those dependencies in parallel.
2. Once review #3 is cleared, register its router/models/0401 migration/browser
   suite; connect confirmed data to the existing export without rebuilding it.
3. Register reviewed extraction/recovery/capabilities and then reviewed documents;
   add a new migration merge and verify source units, handler completion and retry
   fencing. Complete own required logging duration fields alongside this work.
4. Run the complete real fixture workflow and failure matrix, all suites, and
   clean-clone startup on the resulting exact head; update evidence/matrix/demo.
5. Obtain member 4's exact-head integration verdict, fulfill member-1 peer-review
   duty, and hand final assembled main to member 1 for release review. Keep live
   eGrant unavailable until its interface/access/confirmation gates are satisfied.

No completion percentage is assigned. The existing export/platform functionality
should be retained; the remaining work is specific assembly, verification, review
and external-adapter scope rather than another bootstrap or another application.
