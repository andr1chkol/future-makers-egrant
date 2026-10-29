# Shared contract v1

This is the internal contract of our application, not a claim about eGrant's
external endpoints. Use documented eGrant interfaces only.

## Stack and foundation

Frontend: React, strict TypeScript, Vite, npm/package-lock.json, Tailwind,
shared UI components, lucide-react. Backend: Python 3.12, FastAPI, Pydantic v2,
SQLAlchemy 2, Alembic, psycopg, PostgreSQL 16, uv.lock.
Member 5 verifies compatible versions against official documentation and locks
them at bootstrap. Everyone else installs from those locks.

Compose processes: db, api, worker, frontend. Store uploaded files in a private
volume, not public/static. Use one database-backed durable job worker, without
introducing separate Redis/Celery infrastructure. Commands: make dev,
make check, make test, make e2e. Ordinary checks do not call live providers.
API prefix: /api/v1. Frontend uses relative URLs through the shared proxy.

Inspect the existing repository before scaffolding. If existing architecture
conflicts with this proposed stack, member 5 records the discrepancy and obtains
a coordinated decision before publishing bootstrap-v1. Preserve useful code,
history, and instructions. Do not let different agents silently choose stacks.

## File ownership

| Owner | Owned paths | Migration prefix |
|---|---|---|
| 1 | backend/app/documents/**; frontend/src/features/upload/**; tests/documents/**; docs/handoffs/01-documents.md | 010* |
| 2 | backend/app/extraction/**; backend/app/validation/**; tests/extraction/**; docs/handoffs/02-extraction.md | 020* |
| 3 | backend/app/profiles/**; frontend/src/features/profiles/**; tests/profiles/**; docs/handoffs/03-profiles.md | 030* |
| 4 | backend/app/reviews/**; frontend/src/features/review/**; tests/reviews/**; docs/handoffs/04-review.md | 040* |
| 5 | backend/app/platform/**; backend/app/integrations/**; backend/app/main.py; backend/app/worker.py; frontend/src/app/**; frontend/src/shared/**; contracts/**; infra/**; compose.yaml; Makefile; manifests/locks; README; .github/**; tests/e2e/**; docs/release/** | 000*/050* |

Owners create their module tests, handoff, and migrations. Member 5 reserves
revision IDs and reconciles Alembic branches using merge revisions. Do not
rewrite published migrations. Shared files and dependencies are updated by
member 5 through coordinated changes. Record dependency/registration requests
in handoffs and PRs. Call other modules through public interfaces, not their
private database tables.

## Data conventions

JSON uses camelCase. Python uses snake_case with Pydantic aliases. IDs are UUID
strings. Timestamps are ISO 8601 UTC; calendar dates are YYYY-MM-DD.
Decimals are canonical strings with a decimal point, not JSON floating-point
numbers. Use Decimal for monetary calculations. Missing values are null.

FieldType: string | decimal | date | boolean | money.
Value by type: string | decimal-string | date-string | boolean |
{amount: decimal-string, currency: ISO-code}; each type also permits null.
FieldStatus: found | missing | needs_review. Human edits are separate from AI.
Stable keys identify fields/tables; stable rowId identifies each table row.

SourceRef: documentId, unitId, quote:string|null, page:integer|null,
sheet:string|null, cell:string|null. PDF/image pages start at 1. Spreadsheet
sources use sheet/cell and page=null. unitId must exist in the normalized
source. Quote is an exact supporting excerpt when available, otherwise null.
Do not fabricate bounding boxes, pages, or evidence.

Warning: code, message, fieldKey|null, tableKey|null, rowId|null. Bootstrap
specifies how warning identities are derived for acknowledgedWarnings so two
warnings cannot be accidentally acknowledged as one. Keep the representation
consistent across schemas, fixtures, validation, and review.

Document: id, filename, mediaType, status:uploaded|processing|ready|failed,
contentHash, duplicateOf|null, createdAt, pageCount|null, warnings[], error|null.
NormalizedDocument: documentId, units[{id,text,page,sheet,cell}].
Supported initial formats: PDF, JPEG, PNG, XLSX, CSV. Do not execute document
code or spreadsheet macros. Support for another format must be explicit.

FormDefinition: id, name, isIllustrative:boolean, originalJson:object,
fields[{tag,label,type,required,options|null}],
tables[{tag,label,columns[{tag,label,type,required,options|null}]}].
Options: [{key,label}]. Preserve the original tree and unknown configuration in
originalJson. Real eGrant import uses an adapter verified against actual
exports. If only illustrative samples exist, show that status visibly.

Profile: id, version:integer>=1, name, documentKind, formId,
scalarFields[{key,label,type,description,required,targetTag}],
tableFields[{key,label,targetTag,writeMode:append|replace,
columns[{key,label,type,description,required,targetTag}]}].
Keys are unique within their scope. Validate targetTag against FormDefinition.
Select-like values use option keys rather than display labels. Versions are
immutable; editing creates a new version. Each extraction retains its profile
snapshot. Original tags do not change when a user renames a label.

Extraction: id, documentId, profileId, profileVersion,
status:queued|running|ready|failed, mode:live|fixture,
fields[{key,type,value,status,sources[]}],
tables[{key,rows[{rowId,cells[{key,type,value,status,sources[]}]}]}],
warnings[], error|null, createdAt.
ONE extraction processes ONE document. Batch requests create separate
extractions. Do not silently merge documents. Persist row IDs across reads.

Review: extractionId, revision:integer>=0, status:draft|confirmed,
fields[{key,value}], tables[{key,rows[{rowId,cells[{key,value}]}]}],
acknowledgedWarnings[string], confirmedAt|null.
This is a complete editable snapshot, not index-based patches. The original
Extraction remains immutable. PUT uses expectedRevision and increments revision;
stale writes return 409. Confirmation is an explicit human action after type,
required-field, and warning checks. Confirmed v1 reviews are immutable; further
changes require a new run. Human-created rows receive UUIDs.

Submission: id, reviewId(=extractionId), reviewRevision,
mode:export|egrant, targetContext:{applicationId:string|null},
status:prepared|exported|applying|applied|failed|unknown,
payload:{formId,profileId,profileVersion,
fields:[{targetTag,value}],
tables:[{targetTag,writeMode,rows:[{rowId,values:object(tag->value)}]}]},
externalReceipt|null, createdAt, error|null.
Build payload server-side from the confirmed Review and frozen Profile, not
arbitrary target tags supplied by the browser. Exported does not mean applied.
Persist the operation before an external call. A timeout after a possible write
means unknown until reconciliation. External replace requires known current
data, a preview of its effect, and acknowledgeOverwrite. If current state cannot
be obtained safely, external replace is unavailable.

## HTTP interface

All routes below are relative to /api/v1.
Success: {data:...}. Lists: {data:[],pagination:{limit,offset,total}}.
Default limit 50; maximum 200. Error: {error:{code,message,details:null|object}}.
Use 422 invalid input; 404 missing resource; 409 conflict/not ready;
503 integration not configured; 502 upstream failure; 413 upload limits.
Binary/attachment responses are explicit exceptions to the success envelope.

- POST /documents, multipart files[] -> 201 Document[].
- GET /documents -> paginated; GET /documents/{id} -> Document.
- GET /documents/{id}/content -> binary through the access gate.
- GET /documents/{id}/normalized -> NormalizedDocument; 409 unless ready.
- POST /documents/{id}/retries -> 202 Document.
- POST /forms {name,definition:object} -> 201 FormDefinition.
- GET /forms -> paginated; GET /forms/{id} -> FormDefinition.
- POST /profiles, profile definition without id/version -> 201 Profile v1.
- GET /profiles -> paginated latest versions.
- GET /profiles/{id}?version -> Profile; latest when version is omitted.
- POST /profiles/{id}/versions {expectedVersion,...definition} -> 201 new
  version, or 409 conflict.
- POST /extractions {documentIds:UUID[],profileId,profileVersion} -> 202
  {extractions:[{id,documentId,status}]}.
- GET /extractions -> paginated; GET /extractions/{id} -> Extraction.
- POST /extractions/{id}/retries -> 202 Extraction; failed attempts only.
  Retry keeps the same extraction ID and never erases human review.
- GET /reviews/{extractionId} -> Review; initialize draft lazily once ready.
- PUT /reviews/{extractionId} {expectedRevision,fields,tables,
  acknowledgedWarnings} -> Review at revision+1.
- POST /reviews/{extractionId}/confirm {expectedRevision} -> confirmed Review
  at revision+1. Repeating with its current confirmed revision returns the
  same confirmed result. A stale revision returns 409; the client re-fetches
  to resolve a lost response rather than creating another confirmation.
- POST /submissions {reviewId,reviewRevision,mode,targetContext,
  acknowledgeOverwrite:boolean}; required Idempotency-Key header -> 201
  prepared export, or 202 eGrant apply. Same key/body returns the existing
  submission; same key/different body returns 409.
- GET /submissions/{id} -> Submission.
- GET /submissions/{id}/export -> JSON attachment; export-mode transitions
  to exported. Repeated downloads do not modify an eGrant application.
- GET /capabilities -> {ocrConfigured,aiConfigured,egrantConfigured,mode}.

Member 5 defines exact schemas for every request, response, and error before
bootstrap-v1. Missing live behavior in the foundation returns an explicit
unavailable response, never a fake successful implementation.

## Internal Python interfaces

Import public DTOs from app.platform.contracts. Pass database Session explicitly.
Member 5 fixes exact argument/return types and sync/async signatures in
contracts/internal.md BEFORE other owners implement against bootstrap-v1.

- documents/service.py: get_normalized(session, document_id).
- extraction/service.py: create_extractions(session, request),
  get_extraction(session, id), process_extraction(session, id).
- profiles/service.py: get_form(session, id), get_profile(session, id, version).
- reviews/service.py: get_confirmed_review(session, id, revision).
- integrations/service.py: create_submission(session, request, idempotency_key).

Platform jobs: enqueue(kind,payload), register_handler(kind,handler), leases,
recovery, bounded retry. Registered kinds: document.process,
extraction.process, submission.apply. External HTTP calls stay outside long
transactions. Repeated jobs do not duplicate persisted results.

## Frontend assembly

Member 5 generates a typed API client from OpenAPI, shared DTOs and QueryClient.
Routes: /documents, /profiles, /profiles/new, /profiles/:id,
/review/:extractionId, /submissions/:id.
Feature entrypoints:
- features/upload/index.ts exports UploadPage;
- features/profiles/index.ts exports ProfilesPage and ProfileEditorPage;
- features/review/index.ts exports ReviewPage.

Pages require no props; use route parameters and the shared client. Feature
owners do not edit the router or create duplicate server models/clients.
Slovak UI examples: Nahrať dokumenty, Skontrolovať údaje, Nenájdené,
Vyžaduje kontrolu, Uložiť koncept, Potvrdiť údaje, Exportovať JSON.

## Modes, access, and configuration

APP_MODE=live|fixture. Show fixture mode through a banner and result mode.
Never fall back silently to fake data after a provider failure.
Server configuration: OPENAI_API_KEY, OPENAI_MODEL, OCR_BASE_URL, OCR_API_KEY,
EGRANT_BASE_URL, EGRANT_TOKEN, DATABASE_URL, FILE_STORAGE_PATH.
Document names, never secret values, in .env.example.

Bootstrap supplies the backend access gate and server-issued HttpOnly session
cookie; no secrets in URLs or VITE_* variables. Member 5 documents the local
login/bootstrap configuration. An explicit development bypass is restricted
to localhost fixture mode. Deployed live mode requires the access gate.
A single-workspace demo is not production multi-tenant authorization. Real
eGrant authentication and application writes require verified documentation.

## Freeze and change control

Member 5 creates contracts/api.yaml, contracts/internal.md,
contracts/examples/{form,profile,document,normalized-document,extraction,
review,submission}.json, public DTOs, generated frontend client, and tests
validating the examples. Reconcile all inconsistencies before bootstrap-v1.
Record BASE_BRANCH and exact baseline SHA. Preserve any existing tag.
After release of the baseline, contract/manifests changes are coordinated PRs
updating schemas, examples, clients, tests, and every affected consumer.
