# Shared platform and integration interfaces

BASE_BRANCH=main
SETUP_BRANCH=codex/bootstrap
SOURCE_SHA=787bf7b
BASELINE_TAG=bootstrap-v1
BASELINE_SHA=88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8

The published bootstrap-v1 preserves main history. Its immutable SHA is recorded
above; verify it with `git rev-parse bootstrap-v1^{commit}`. Member 4's independent
bootstrap report is published in PR #2 for head 70370b3; its tree matches the
baseline merge. Never move the tag. Integration work uses codex/integration.
Module implementations land through independently reviewed PRs to BASE_BRANCH.

## Runtime and DTOs

Python 3.12; PostgreSQL 16; Node 22.12+; npm; React; Vite; Tailwind 4.
`uv.lock` and `frontend/package-lock.json` are authoritative exact versions.
`CONTRACT.md` and `QUALITY.md` are authoritative root copies. Team prompt copies
must stay identical. `backend/app/platform/contracts.py` owns all public DTOs.
Import as `from app.platform.contracts import Document, Extraction, ...`.
JSON uses aliases; serialize with `model_dump(mode="json", by_alias=True)`.
`make generate` exports OpenAPI then generates TypeScript. Never edit generated
TypeScript. Frontend uses `api` from `frontend/src/shared/api.ts`.

## Public module interfaces

All functions below are synchronous. UUID is `uuid.UUID`. Session is
`sqlalchemy.orm.Session`. DTO names are from `app.platform.contracts`.
Domain owners implement these import paths before requesting assembly. The
integrations service is implemented on codex/integration; its upstream reads
return unavailable until the owners' services are present.

```python
# app.documents.service
get_normalized(session: Session, document_id: UUID) -> NormalizedDocument
process_document(session: Session, document_id: UUID) -> None
# app.extraction.service
create_extractions(session: Session, request: CreateExtractions) -> ExtractionBatch
get_extraction(session: Session, id: UUID) -> Extraction
process_extraction(session: Session, id: UUID) -> None
# app.profiles.service
get_form(session: Session, id: UUID) -> FormDefinition
get_profile(session: Session, id: UUID, version: int | None = None) -> Profile
# app.reviews.service
get_confirmed_review(session: Session, id: UUID, revision: int) -> Review
# app.integrations.service (member 5, integration phase)
create_submission(session: Session, request: CreateSubmission, idempotency_key: str) -> Submission
apply_submission(session: Session, id: UUID) -> None
```

Read functions do not commit. They raise NotFoundError for unknown IDs;
ConflictError for not-ready, stale, or unconfirmed state. ValidationError is 422;
UnavailableError is 503. Import these from `app.platform.errors`. Do not return
null for missing resources. Public writes use `with session.begin():` to own an
atomic transaction; callers supply a fresh session with no active transaction.
Read calls within a write reuse its Session and never commit. HTTP handlers use
`Depends(get_session)` from `app.platform.database`. Close sessions after use.
Handlers own their short transactions. They must commit results before returning;
the worker does not commit handler work. Provider calls happen outside transactions.

## Jobs and registration

```python
from app.platform.jobs import JobPayload, JobRegistry, enqueue
enqueue(session: Session, kind: JobKind, payload: JobPayload) -> UUID
registry.register_handler(kind: JobKind, handler: Callable[[Session, UUID], None]) -> None
```

JobPayload has only `resource_id: UUID`. It stores no document content or secrets.
Enqueue uses caller's transaction and flushes without committing. The canonical
requestId ContextVar is copied into the job. Claim uses FOR UPDATE SKIP LOCKED,
a 60-second lease, a fresh lease token, and increments attempt durably before
execution. Expired leases can be reclaimed; completion requires the current token
and unexpired lease. Backoff is min(2**attempt,60) seconds. Document/extraction
jobs have three attempts; submission.apply has one. Exhausted leases become failed.
Handlers must finish inside 60 seconds or split work into durable phases; v1 has
no lease renewal. At-least-once execution still requires idempotent domain writes.
A late worker cannot finalize the job, but domain writes need their own constraints.

`app.worker.build_registry` explicitly reserves document.process,
extraction.process, submission.apply. The document handler is app.documents.service.process_document. Extraction handlers currently raise HandlerUnavailableError
(app.platform.jobs) and fail HANDLER_UNAVAILABLE. submission.apply uses
app.integrations.service.apply_submission, which makes no external calls while
the eGrant adapter is unavailable. It preserves interrupted applying operations
as unknown and fails undispatched operations. The worker recovers terminal
apply leases before polling again. The worker invokes app.documents.service.reconcile_interrupted with a fresh Session on every polling cycle. Owners request extraction replacement
imports/registration in their handoff. Register exactly once; duplicate registrations raise ValueError.
A submission timeout or exhausted apply lease requires owner reconciliation to
unknown before any new write. Never automatically retry a possibly applied effect.

## Router assembly

`app.platform.routes.router` contains typed 503 domain shells for all frozen
routes. Each owner supplies an APIRouter as `app.<module>.routes.router` with
paths relative to /api/v1. Member 5 removes the corresponding shell routes and
includes that router in `app.main.create_app` with `Depends(require_access)`.
No owner changes route prefixes or removes the access dependency. Frontend pages
have no props and use router params. Shared QueryClient is in app/main.tsx.

## Validation invariants

Scalar and table keys are unique in their scope; rowId is a UUID, persistent
across reads. Profile owners validate tags, column scopes and option keys against
FormDefinition. Profile versions and extraction snapshots are immutable. Review
owners validate the complete snapshot against the frozen extraction/profile,
including types, exact keys, row IDs, required values and warnings. A human may
supply missing information; it stays separate from source evidence. Null means
missing. Money has decimal strings and uppercase three-letter currency codes;
providers must validate supported ISO codes. Dates are YYYY-MM-DD; UTC timestamps
must be emitted in UTC even though the schema accepts timezone-aware input.

Warning identity is lowercase SHA-256 of UTF-8 JSON of the full Warning DTO,
including null fields and message, sorted keys, ensure_ascii=False, separators
(',', ':'). Use `warning_identity` from contracts.py. Exact duplicate warnings
collapse to one identity; any location/message change invalidates acknowledgement.
Confirmation requires acknowledgement of the current warning set, not old IDs.
PUT increments expectedRevision atomically. Confirm increments once; repeat with
current confirmed revision returns the same snapshot. A lost response requires
GET then resolution; an old revision returns 409, including after confirmation.
Confirmed reviews cannot be changed in v1. Submission keys are opaque 1–128
character values. Owners persist key + canonical request hash atomically before
external effects; same body/key returns the existing operation and changed intent
returns 409. The JSON export attachment is an envelope-free SubmissionPayload, named
submission-<UUID>.json. Export is not apply. External replace requires known-state preview
and explicit human acknowledgement. No external adapter is available in bootstrap.

## Migration and shared-file requests

0001_platform is the foundation revision. 0501_submissions owns submissions;
0301_profiles owns imported forms/profile versions. Their histories converge at
the new no-op merge revision 0502_profiles_assembly. Reserve 010* documents, 020*
extraction, 030* profiles, 040* reviews, 050* integrations. Each module's first
migration points to 0001_platform. Independent branches need a member-5 merge
revision before assembled release; never edit published revisions.

Record dependencies, exact import signatures, router and handler registrations,
migration IDs and checks in docs/handoffs/0N-<module>.md and the PR. Member 5
owns shared dependencies, locks, generated files and assembly. Contract changes
update DTOs, schema, generated client, examples and affected consumers together.

## Access and modes

Every /api/v1 domain endpoint and content route uses the same access gate.
POST /auth/login accepts an access code in the body and issues a random HttpOnly,
SameSite=Strict cookie; only its SHA-256 hash is stored, with an eight-hour expiry.
GET /auth/session is protected; DELETE revokes the current session. Unsafe
requests require exact PUBLIC_ORIGIN, including login, to prevent cookie CSRF.
There is no eGrant authentication or tenant isolation in this single-workspace demo.
Use TLS and COOKIE_SECURE=true for any deployment. Local bypass requires fixture
mode, a localhost public origin and a localhost request hostname. Compose binds
all published ports to loopback. Do not expose the development servers publicly.

Capabilities remain false until adapters exist, even if credentials are present.
The UI reads mode from session and keeps the fixture banner visible on every
route. Linked fixture examples are reference data only; they do not make domain
routes functional. Full domain-route coverage and the complete fixture workflow
remain pending until owners' implementations are assembled.


## Submission persistence and assembly status

The protected integrations router replaces exactly the three submission shells.
Wire DTOs, examples, OpenAPI and generated client are unchanged. New operations
read the exact confirmed review revision, extraction profile identity/version,
versioned profile and form via the public interfaces above. Mapping validation
checks exact keys, unique destination tags, row UUIDs, field types, required
values, options and current warning acknowledgements before persisting payload.
The immutable profile-version contract remains a prerequisite; no private domain
table is read. Existing idempotent operations use their stored payload even if
an upstream owner becomes unavailable.

A PostgreSQL unique constraint protects the opaque idempotency key. Canonical
request hashing covers all CreateSubmission fields, including overwrite intent
and target context. INSERT ON CONFLICT DO NOTHING plus a fresh READ COMMITTED
read resolves concurrent inserts; changed intent returns 409. Failed validation
rolls back the operation. No external side effect occurs in the transaction.
GET export locks the operation, allows only prepared/exported export mode and
returns the stored envelope-free payload. Exported means the download was served,
not that the browser saved it or eGrant accepted it.

EGRANT capability remains false in both modes. POST mode=egrant returns 503 and
does not enqueue a job, regardless of credentials or acknowledgeOverwrite.
No append/replace HTTP adapter, remote timeout handling or receipt reconciliation
is claimed. Those require documented interfaces and explicit write authorization.
The defensive apply handler/recovery tests use seeded operations only.

The logger carries requestId/jobId/attempt through handlers and recovery; it
permits numeric revision/version and UUID profileId/formId. PR #5 fixes recovery
correlation and is merged into integration. The seven profile/form operations
from reviewed e845099 replace their shells. Profiles models and migration location
are registered; production profile routes are used by both API/browser tests.
The continuation registers the document, extraction and review modules. Its
verification and review limits are recorded in docs/release/FINISH-PRODUCT.md.

## Extraction and review assembly

The shared worker registers `process_extraction` and invokes
`recover_terminal_extractions` in a fresh session on each polling cycle.
A terminal job can fail an orphan run, but a newer active job takes precedence.
The worker lease is 60 seconds and the provider call has a 40-second caller
deadline. Outstanding OpenAI request threads share four slots per process.

The extraction and review routers replace their bootstrap shells. Alembic
revision `0504_full_assembly` joins `0503_documents_assembly`,
`0201_extractions` and `0401_reviews`. Original published revisions are unchanged.
Option snapshots distinguish scalar and table scopes. Legacy flat snapshots
are reconstructed from the immutable form, where colliding options cannot be
recovered from the flat keys themselves.

## Documents assembly

The six document shells are replaced by app.documents.routes.router with the
shared access dependency and unchanged binary response metadata. Normalized reads
use app.documents.service.get_normalized without committing. Recovery uses
reconcile_interrupted(session: Session) -> None, a bounded batch of 50, and logs
the original job correlation after commit. The production registry contains one
document.process handler. Alembic imports document models and discovers their
owned migration directory. 0503_documents_assembly joins the published
0502_profiles_assembly and original 0101_documents; published migrations are unchanged.

Intake holds a negative bigint advisory lock derived from each generated document
UUID across private storage and database commit. app.documents.cleanup uses the
same lock before checking row absence and deleting an old orphan. Positive hash
locks remain reserved for duplicate serialization. See the documents assembly
handoff for supported runtime and multipart boundary limits.

The CSV fixture matches the ordered normalized text and cell locations without
depending on upload-specific IDs. The recorded cell evidence is rebound to the
actual normalized units only after a match. The original row-based reference
still works for existing tests. Neither recording is used in live mode.
