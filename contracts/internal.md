# Bootstrap interface freeze candidate

BASE_BRANCH=main
SETUP_BRANCH=codex/bootstrap
SOURCE_SHA=787bf7b
BASELINE_TAG=bootstrap-v1
BASELINE_SHA=PENDING_INDEPENDENT_REVIEW

The candidate preserves the existing main history. origin/master contains a
separate README commit; it has no application stack to reconcile. No competing
implementation or CI existed at inspection. Main is the remote default and PR
target. No bootstrap tag existed. Do not start module work until member 4 has
reviewed the exact candidate SHA and bootstrap-v1 is published. Resolve the
immutable tag with `git rev-parse bootstrap-v1^{commit}`; never move it.

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
Domain modules and these functions are intentionally not implemented by bootstrap.
Owners implement exactly these import paths before requesting assembly.

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
extraction.process, submission.apply. Current handlers raise HandlerUnavailableError (app.platform.jobs) and fail HANDLER_UNAVAILABLE;
they never pretend work succeeded. Owners request replacement imports/registration
in their handoff. Register exactly once; duplicate registrations raise ValueError.
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

0001_platform is the only foundation revision. Reserve 010* documents, 020*
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
