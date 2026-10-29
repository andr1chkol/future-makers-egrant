# Member 1 — document intake, OCR, and source normalization

## Product context and your responsibility

You are implementing one module of a shared document-to-form assistant for
eGrant. Managers configure extraction profiles against form definitions.
Applicants upload documents, review proposed values and table rows, make
corrections, and explicitly confirm them. Only confirmed data may be exported
or applied to an application. The product supports different forms through
configuration rather than hardcoded invoice fields.

Implement your assigned module end to end. Do not build a separate app,
replace the shared stack, or stop at a design report or static mockup.
The existing team repository is:
https://github.com/andr1chkol/future-makers-egrant.

## Read before writing code

Read the root `AGENTS.md`, `docs/team/README.md`, `docs/team/CONTRACT.md`,
`docs/team/QUALITY.md`, the application README, `contracts/api.yaml`,
`contracts/internal.md`, and `contracts/examples/*`. Inspect the existing
implementation and relevant call sites before introducing new code.

Read and apply the bundled skills:
- `.agents/skills/human-code/SKILL.md` for maintainable implementation;
- `.agents/skills/humanizer/SKILL.md` for technical prose only;
- `.agents/skills/final-review/SKILL.md` for the actual final diff.

Humanizer must preserve commands, schemas, identifiers, and code blocks. It is
not a source-code rewriter. Use human-code for naming, structure, comments,
and implementation choices. Do not sacrifice correctness for stylistic rules.

Verify the `bootstrap-v1` baseline, current branch, Git status, and recorded
BASE_BRANCH. If the shared foundation or machine-readable contracts are
missing, report that member 5 must complete bootstrap. Do not invent another
foundation while waiting. Preserve other people's local changes.

## Non-negotiable implementation rules

Write code, paths, identifiers, comments, docstrings, technical logs, tests,
and handoff documentation in English. Product UI copy stays in Slovak. Preserve
uploaded document content in its original language. Use precise domain names,
straightforward control flow, and the existing layout. Explain non-obvious
rules, workarounds, and failure behavior with concise English comments.

Work within your owned paths. Reuse the public DTOs, generated API client,
database sessions, access gate, job infrastructure, logger, and UI controls.
Request shared dependency/contract/router changes through member 5 and record
them in your handoff. Do not duplicate shared services or edit frozen contracts
unilaterally. Ordinary tests may use the shared fixtures. Live mode must use
configured adapters or return an explicit failure, never silently fake success.

## Required delivery workflow

1. Implement the responsibilities and acceptance criteria below, including
   the module's frontend/backend behavior where assigned.
2. Write and actually execute meaningful behavior, failure, and contract tests.
   Verify logging, redaction, relevant concurrency, and user-visible error states.
3. Review naming and comments with human-code. Edit handoff prose with humanizer
   in a technical voice, without changing facts or executable examples.
4. Apply final-review to the actual final diff and surrounding code. Fix safe
   in-scope findings, add regression tests where appropriate, and rerun checks.
5. Write the assigned handoff with interfaces, migration IDs, dependencies,
   required registrations, setup, test commands and actual results, log events,
   manual reproduction steps, verified provider modes, limits, and blockers.
6. Commit and open a PR into the recorded BASE_BRANCH if authorized repository
   access is available. Attach the PR to the chat using attach_artifact when
   available. Otherwise provide the local SHA and exact next commands. Do not
   force-push or merge your own PR automatically.
7. Hand the PR to the assigned independent reviewer, who uses
   `docs/team/06-PEER-REVIEW.md` in a fresh chat. Self-review is not peer review.

Report failed or unexecuted checks honestly. Missing external credentials block
that integration, not the rest of your implementation. Complete all independent
work and identify exactly what access is still required.

## Your ownership and expected outcome

Branch: codex/documents. Own backend/app/documents/**,
frontend/src/features/upload/**, tests/documents/**, and
docs/handoffs/01-documents.md. Use migration prefix 010* as coordinated with
member 5. Shared infrastructure changes remain member 5's responsibility.

Deliver a real intake path: accepted files become private stored documents,
viewable previews, and normalized source units with accurate provenance.
Member 2 can consume your output without understanding file formats. Member 4
can retrieve original content and navigate to supporting pages or cells.

## Implementation tasks

### 1. Upload and storage

Implement document creation, listing, detail, content download, normalized
content retrieval, and retries according to OpenAPI. Support multiple PDF,
JPEG, PNG, XLSX, and CSV files. Validate actual file content as well as declared
type. Enforce configurable size/page/row/decompression limits. Store by generated
ID through the shared storage abstraction; never construct paths from filenames.
Protect content routes through the shared access gate.

Calculate a content hash and return duplicate warnings without deleting or
silently merging the user's files. Preserve the original file separately from
processing artifacts. Define predictable behavior for partially failed batches.

### 2. Normalization and OCR

Implement the document.process handler. Read usable PDF text directly; send
image-only pages and photos through a configured OCR adapter. Use the real
eGrant OCR interface only when documentation and credentials exist. Otherwise
support an explicitly configured alternative or report integration unavailable.
Do not invent an eGrant endpoint or return fixture text in live mode.

Create stable SourceUnit records with document/page provenance and correct page
order. For spreadsheets, preserve sheet names and cell coordinates. Read cached
formula results when available or warn that a value is unavailable; execute no
macros or arbitrary spreadsheet code. Handle CSV encoding, blank rows, and
malformed input explicitly.

### 3. Durable processing and public interface

Persist uploaded/processing/ready/failed status, attempts, and safe error codes.
Implement get_normalized exactly as specified in contracts/internal.md. A
not-ready result must not look like an empty successful document. Use the
shared worker and database sessions. Keep slow OCR outside long transactions.
Retried jobs and worker restarts must not duplicate source units or overwrite
already consumed source data without an explicit invalidation rule.

### 4. Upload workflow

Export UploadPage from the assigned feature entrypoint. Provide drag-and-drop
and a file picker, per-file processing state, preview, useful failures, retry,
profile selection, and extraction launch through the shared API client.
Use capabilities to explain missing provider configuration. Batch processing
creates separate extraction links, not an unexplained combined review.
Support refresh and partial failure without losing the list of accepted files.

### 5. Logs and maintainability

Emit document.uploaded, document.processing_started, document.ready,
document.failed, document.duplicate_detected, and retry events through the
shared logger. Include safe IDs, attempts, elapsed time, and error codes.
Do not log raw OCR, uploaded content, personal filenames, or credentials.
Add concise comments explaining storage protection, OCR selection, provenance,
format limits, and restart/idempotency behavior where not obvious.

## Tests you must implement and run

- Text PDF, scanned PDF through a fake OCR adapter, image, XLSX, and CSV.
- Correct document/page/sheet/cell source references and stable unit IDs.
- Corrupt files, empty OCR, unsupported content, MIME spoofing, oversized files,
  traversal filenames, and spreadsheet decompression/row limits.
- Duplicate files, OCR timeout/failure, bounded retry, repeated jobs, and worker
  restart behavior using the platform interfaces.
- Content access checks and normalized endpoint behavior before readiness.
- Log event/correlation assertions and redaction of realistic secret/PII samples.
- UI upload-to-ready-to-extraction navigation, partial batch failure, retry,
  refresh, and loading/empty/error states.

Run live OCR separately on a permitted sample when configured. Record whether
it was actually verified; fake-provider success does not prove OCR integration.

## Acceptance and handoff

A real supported file can be uploaded, previewed, normalized, and passed to
extraction. Invalid input fails safely and visibly. Sources point to the actual
file location. Tests and log checks have run. List exact OCR configuration or
an explicit blocker. Include public imports, worker registration, migrations,
limits, example commands, and tested formats in the handoff.
Independent reviewer: member 5.
