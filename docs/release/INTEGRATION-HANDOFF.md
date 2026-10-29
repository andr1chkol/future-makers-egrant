# Member 5 integration handoff

Repository: <https://github.com/andr1chkol/future-makers-egrant>.
Branch: `codex/integration`. BASE_BRANCH: `main`.
Immutable baseline: `bootstrap-v1`, `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`.
Self-reviewed published code: `e0e1f952c94a686029dd80ee154e344c12affadc`.
Tested local code: `38973034d735f5abac3ea8584bf0a9e396685e0b`.
Both commits have tree `e0a6054c4b560dfda4278eaa2a3cd9ed0fda2de7`.
The follow-up commit adds this handoff only; independent review must cover the
complete final PR head, including documentation.

Verdict for the code SHA above: **ready for independent review of member-5 export
and status scope**. The assembled product is **NOT READY**: members 1–4 are not
registered on this branch and live providers are unavailable. This is author
self-review, not member 4's independent review or member 1's release review.

## Behavior and interfaces

The integrations router replaces the three unavailable submission shells under
the existing `/api/v1` access gate. OpenAPI, public DTOs, examples and generated
client remain byte-for-byte compatible with bootstrap. No shared dependency was
added. The Node engine declaration and lock metadata match the already locked
test toolchain: Node ^22.12.0, ^24.0.0 or >=26.0.0.

Public synchronous services in `app.integrations.service`:

```python
create_submission(session: Session, request: CreateSubmission, idempotency_key: str) -> Submission
get_submission(session: Session, id: UUID) -> Submission
export_submission(session: Session, id: UUID) -> SubmissionPayload
apply_submission(session: Session, id: UUID) -> None
recover_interrupted_submissions(session: Session) -> None
```

Create/export/apply/recovery own short transactions and require a fresh Session.
GET only reads and never commits. Error types are the shared NotFoundError,
ConflictError, ValidationError and UnavailableError. The router produces shared
safe envelopes and the JSON attachment is an envelope-free SubmissionPayload.

New exports call the public `get_confirmed_review`, `get_extraction`,
`get_profile(session, id, version)` and `get_form` interfaces documented in
`contracts/internal.md`. No private domain table is accessed. Missing owner
modules return 503. Missing transitive dependencies or incompatible service
signatures surface as failures rather than being disguised as successful data.

The server checks exact requested review identity/revision, confirmed status and
timestamp, ready extraction, profile identity/version, form identity, exact
warning acknowledgement, exact field/table/cell keys, row uniqueness, unique
mapping tags, supported value types, option keys and required values. It builds
payload solely from the confirmed values and versioned mapping. Immutable profile
versions and form definitions remain owner obligations; integration does not
reconstruct their private snapshots. Human rows and corrections are preserved.
Null stays null; false and decimal strings do not become missing values.

Migration `0501_submissions`, parent `0001_platform`, creates `submissions`, a
unique idempotency key, immutable request hash/payload and an apply-recovery
index. Published baseline migrations are unchanged. The model is registered in
Alembic metadata. No cross-module foreign key is invented while owners' schemas
are absent. Reconcile additional migration heads after reviewed modules land.

Canonical intent hashing covers every CreateSubmission field. PostgreSQL INSERT
ON CONFLICT resolves simultaneous identical requests; the winning operation is
returned. Changed intent with the same key returns 409 and never overwrites the
winner. Validation and serialization failure leave no partial operation. Existing
operations can be read/downloaded even when an upstream module is unavailable.
Downloads lock the operation and move prepared/export mode to exported; repeated
downloads return the stored payload. Exported means the response was served, not
that the user saved a file or that eGrant accepted any values.

## Worker and external writes

`submission.apply` explicitly registers `apply_submission`. Document/extraction
handlers remain explicit unavailable handlers until their reviewed owners'
implementations are assembled. One queue, lease token, bounded retry and
transactional enqueue are retained; no second worker infrastructure was added.

No application-data API, receipt lookup, current-state reconciliation interface,
append/replace semantics or authorized eGrant test target is available here.
Form-structure editing is not an application-value write interface. Credentials
and acknowledgeOverwrite cannot enable an adapter: POST mode=egrant returns 503
without creating a submission or job. No external HTTP request is made.

The defensive handler fails seeded undispatched eGrant operations and turns
seeded interrupted applying operations into unknown. Worker polling recovers up
to 100 operations whose apply job is terminal, using row locks and skip-locked
selection. It never requeues them. Tests simulate restart by expiring a real
PostgreSQL job lease, exhausting its one attempt and invoking recovery. These
are local uncertain-state tests, not remote timeout or reconciliation evidence.
Applied/receipt transitions remain unavailable; no fake submission.applied event
is emitted. A future adapter needs atomic operation/outbox creation, explicit
human authorization, documented semantics and receipt/state reconciliation before
unknown can become applied or another write can be attempted.

## UI, access and logs

`/history` consumes the generated extraction-list API with pagination and polling
for queued/running results. Empty, unavailable, loading and error states are real;
no fixture records are inserted into runtime history. `/submissions/:id` shows
durable status, confirmed revision/profile version, a protected JSON download,
payload preview and retryable loading/download errors. Unknown warns against
repeating the write. There is no new apply button. ReviewPage remains owned by
member 4; its existing PR supplies confirmation/export controls.

Slovak copy, the fixture banner, typography, shared controls and QueryClient are
retained. The JSON preview scrolls internally on narrow screens. React escapes
payload text. No payload is written to frontend console output or browser storage.
The cookie gate, Origin protection and private-file access are retained. This
remains a single-workspace demo, not eGrant identity or tenant isolation.

Logs use the existing JSON logger and redaction. New persisted operations emit
submission.prepared with requestId, extractionId, submissionId and durationMs.
Defensive apply/recovery emit submission.failed or submission.unknown with safe
codes. Worker handlers inherit requestId/jobId/attempt through ContextVars;
job completion/retry events retain correlation. Numeric revision is allowed in
formatted JSON, resolving member 4's shared logger request. Payloads, access
codes, financial values, filenames and idempotency keys are not logged.

## Integration requests and ownership

At inspection, `main` remains the bootstrap merge. PR #3 has member 4's review
module at `133e6ced9cbce21fb255fa77b45d3d335c47ec75`, awaiting member 3 review.
It was inspected as a dependency, not merged or rewritten. Documents, extraction
and profile PRs were not available. Bootstrap's independent report is in PR #2;
its reviewed head 70370b3 has the same tree as baseline 88d1b95.

| Owner | Required registration after independent review |
|---|---|
| 1, documents | Replace document shells with app.documents.routes.router; register document.process public handler; register owned 010* migration location/models |
| 2, extraction | Replace extraction shells; register extraction.process public handler; expose exact version identity; register 020* migrations/models |
| 3, profiles | Replace form/profile shells; public versioned get_profile and get_form; register 030* migrations/models |
| 4, review | Replace three review shells; include app.reviews.routes.router; discover backend/app/reviews/migrations and import models; preserve 0401_reviews; add dedicated review browser command to CI after merge |
| 5, integration | Merge migration heads through a new revision, regenerate/check schema/client, run assembled checks; route owners fix their own defects |

The numeric revision logging request is implemented. Other review registrations
remain pending its reviewed merge; adding absent import paths now would break
startup. No frozen wire-contract change is requested by this PR. Any future
change must update schemas, examples, generated client and affected consumers
together. External writes still require a separate explicit human confirmation.

## Executed verification

All final checks below exited 0 on the code tree identified above. Host tools:
Python 3.12.6, uv 0.13.6, Node 26.5.0; Compose frontend uses Node 22. PostgreSQL 16
ran in a dedicated local container, `egrant-integration-test`, port 55435.
Tests reset only explicitly named disposable test databases.

| Check | Result and boundary |
|---|---|
| make check | PASS: locked dependencies, Ruff, formatting, tracked-secret pattern scan, OpenAPI/client drift, strict TypeScript, Vite build |
| make test | PASS: 67 backend tests (35 integration, 32 platform) and one component test |
| Real PostgreSQL idempotency | PASS: concurrent same intent, concurrent changed intent, rollback after insert, exact persisted payload and repeated download |
| Invalid data | PASS: draft/stale/unconfirmed review, wrong extraction/profile, warnings, missing required values, invalid options/types/keys/rows/mappings |
| Worker safety | PASS: one-attempt apply, expired lease restart, unknown/failed recovery, active lease preservation, request/job correlation |
| Access/redaction/schema | PASS: protected submission/status/content, safe validation, attachment schema, request IDs and no document values or key markers in logs |
| Another profile | PASS at payload boundary: renamed target tags, replace export metadata, human row UUIDs, false/null and decimal string values |
| make e2e | PASS: three Chromium foundation scenarios |
| make e2e-integration | PASS: four Chromium scenarios; real submission API/database/download, explicit neighboring doubles, responsive status and UI error recovery |
| Clean-clone install/check/test/both E2E | PASS: new local clone with independent locked installs and clean working tree |
| Clean-clone Compose | PASS: new volumes; healthy API/DB; worker/frontend running; 0501_submissions; fixture capabilities all false; example submission ID returns 404 |
| GitHub Actions | See final PR checks; local results do not imply remote CI passed |
| Full upload -> extraction -> edit -> confirm -> export | NOT VERIFIED: domain services not assembled |
| Real provider failures / actual eGrant timeout / reconciliation | NOT VERIFIED: no documented adapter or authorized live tests |
| Independent module/release review | NOT VERIFIED: member 4 and later member 1 must review exact PR/release SHAs |

Earlier runs failed because Docker was stopped, foundation tests still expected
0001_platform/unregistered apply, the external browser-test path could not resolve
Playwright, and the mobile JSON preview widened the grid. Docker was started;
a dedicated test DB was created; assertions were updated for the registered
service/migration; browser tests moved beside the locked frontend dependency;
and the grid was fixed. Final tests preserve strong behavior assertions.
Non-failing warnings: Starlette TestClient/httpx deprecation, whatwg-encoding,
terminal color flags and host npm allow-scripts for optional fsevents.

### Exact local commands

```sh
export UV_CACHE_DIR=/private/tmp/egrant-integration-uv
make check UV=.tools/bin/uv
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_integration make test UV=.tools/bin/uv
make e2e
INTEGRATION_E2E_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55435/egrant_test_e2e_integration make e2e-integration
```

Clean checkout: `/private/tmp/egrant-integration-verify-3897303`, cloned from the
local repository at the tested SHA with `git clone --no-hardlinks --branch
codex/integration`. `make install` used the pinned uv executable at
`/Users/Andrew/Documents/ChatGPT/FUTURE-MAKERS/future-makers-egrant/.tools/bin/uv`.
Then the same checks ran there with that absolute UV argument. No source from
the primary checkout was imported by the clean clone's app/tests. Chromium was
already installed on the host. Compose used the following commands:

```sh
cp .env.example .env
DB_PORT=55436 docker compose -p egrant-integration-verify-3897303 up --build -d
DB_PORT=55436 docker compose -p egrant-integration-verify-3897303 ps
docker compose -p egrant-integration-verify-3897303 exec -T db psql -U egrant -d egrant -Atc 'SELECT version_num FROM alembic_version'
curl --fail --silent http://localhost:5173/api/v1/capabilities
git status --short
```

Network, Docker and local sockets required sandbox escalation. CLI push lacked
GitHub HTTPS credentials. The connected GitHub API published the exact tested
tree as e0e1f95, using baseline as parent and a non-force ref update with the
expected previous SHA. `git fetch origin codex/integration` followed by
`git diff --exit-code HEAD origin/codex/integration` exited 0. Original local
commits were preserved; the connector publication has a different commit identity.
No other branch was reset, force-pushed or merged.

## Provider matrix and manual demo

| Capability | Classification |
|---|---|
| Cookie gate, storage, durable jobs | Fixture/local verified; no eGrant identity |
| Confirmed submission and JSON download | Fixture-boundary verified with real PostgreSQL; unavailable for new operations until domain public reads land |
| OCR/AI/document extraction | Unavailable on this branch |
| Illustrative form/example payloads | Reference data only; not runtime history |
| eGrant authentication, application write, receipt reconciliation | Unavailable; no live verification |

Run `make dev` from a clone using README. Open `/history`: an explicit unavailable
state is expected until extraction is registered. A random submission ID shows
a safe load error; it never reveals a reference record from examples.

For the reproducible submission demonstration, create the disposable E2E DB and
run `make e2e-integration`. Its test-only server supplies reference review/profile
reads. The browser creates a real operation, downloads JSON, verifies the human
correction, repeats the same key and rejects changed intent. The screenshot
`docs/release/integration-export.png` is an ignored local/CI artifact. This demo
must be described as submission-boundary evidence, not an assembled product.

After owners land, the user-facing demo is: import a form, configure a profile,
upload a permitted file, inspect evidence, correct a value/row, save and reload
the draft, acknowledge warnings, confirm, prepare export, download JSON and
compare the correction. Repeat with another profile and show stale-revision,
duplicate-document and provider-failure states. eGrant apply remains disabled
until the documented interface and separately authorized test write are supplied.

## Self-review and release checklist

Applied human-code and final-review to the baseline-to-code diff, new files,
surrounding routes, queue, DTOs, migrations, callers and tests. Applied humanizer
in technical voice to this handoff and README, preserving facts and commands.
Fixed unused frontend imports, mobile overflow, migration/handler test assumptions
and recovery query indexing. Confirmed no example loader is imported by runtime,
no private cross-module table reads, no schema/client drift, no new runtime
package, no fake provider success and no external write path. Backend reliability
review for e0e1f95 passes the implemented export boundary with the dependency and
live-write limits recorded above. Independent review is still required.

Release criteria from `07-RELEASE-REVIEW.md` for this code SHA:

- [x] Empty-database startup, migrations and reproducible locked checks.
- [x] Confirmed-payload boundary, concurrency, safe errors, access and redaction.
- [x] Narrow-screen status/download behavior and genuine unavailable states.
- [ ] Members 1–4 independently reviewed, merged through main and registered.
- [ ] Migration heads reconciled without editing published history.
- [ ] Full real module fixture workflow, draft reload and human corrections in export.
- [ ] Assembled duplicate/provider/revision-conflict and another-profile browser flows.
- [ ] Permitted real documents, OCR/AI credentials and data-handling approvals.
- [ ] Documented eGrant application write/current-state/receipt semantics and authorized target.
- [ ] Explicit human permission for any live application write.
- [ ] Independent member-4 integration review, then member-1 release review on final main SHA.

Evaluation procedure: `docs/team/07-RELEASE-REVIEW.md`; module review procedure:
`docs/team/06-PEER-REVIEW.md`; bootstrap evidence: `docs/release/BOOTSTRAP-REVIEW.md`
and PR #2. No challenge evaluation endpoint or submission channel is supplied.
The team must provide the exact October 30 submission time/timezone/channel.
Do not label this branch a completed assembled hackathon release.
