# Engineering quality requirements

## Language, naming, and structure

All source code, filenames, identifiers, database names, tests, comments,
docstrings, technical errors, and log events use English. Product UI copy is
Slovak, mapped from stable backend error codes. Preserve document content in its
original language. Write implementation handoffs and review reports in English.

Use precise domain names: document, sourceUnit, extractionProfile, extraction,
review, submission. An invoice is a document profile, not the whole product.
Prefer names such as `confirm_review`, `normalize_document`, or
`build_submission_payload` over generic `handleData`, `Helper`, or `Manager`.
Use the repository's established casing and file layout.

Read and apply the bundled `human-code` skill before implementation. Read and
apply `humanizer` to README/handoff/review prose using a technical voice and
preserving code blocks, commands, paths, identifiers, and factual claims.
Humanizer explicitly does not edit source code or structured data. Human-code
is the implementation standard. Neither skill justifies changing correct domain
terminology, inventing evidence, or weakening validation.

Prefer direct, cohesive modules and simple control flow. Add an abstraction
when it hides real complexity or supports a real variation, such as live and
fixture providers. Avoid decorative architecture, duplicate DTOs, pass-through
wrappers, unrelated rewrites, and TODOs standing in for required behavior.
Use the shared formatters and linters. Do not reformat unrelated files.

## Useful comments

Comment the reasons behind non-obvious decisions, especially:
- provider limitations and compatibility workarounds;
- evidence matching and source-coordinate limitations;
- monetary rounding and validation tolerances;
- transactions, retries, leases, and idempotency;
- optimistic revision conflicts and confirmed-data immutability;
- file-format limits and preservation of unknown imported settings.

Comments and docstrings must be concise English explanations a maintainer can
use. Public interfaces need a short description when side effects, error modes,
or preconditions are not obvious from types and names. Do not narrate obvious
loops, assignments, or return statements. Improve unclear names before adding
a comment to explain them. Keep comments accurate when behavior changes.

## Meaningful, runnable tests

Every owner writes and executes tests for observable behavior and failure modes.
Do not merely assert the implementation's internal steps or weaken assertions
until tests pass. Use regression tests for material bugs fixed during review.

- Backend: pytest; isolated PostgreSQL for persistence, concurrency, and
  transaction behavior. SQLite is not a substitute for PostgreSQL semantics.
- Frontend: the bootstrap-selected runner, behavior-focused component tests,
  and Playwright for user workflows.
- Contract: example payload validation, generated-client compatibility, and
  runtime API/schema compatibility after modules are assembled.
- Providers: deterministic fake adapters in ordinary tests; separately enabled
  live tests using permitted files and credentials.

Normal checks must not require paid requests or access to private services.
Fixtures are explicit, reproducible, and never silently substituted in live mode.
Each report states the actual command, exit status, scope, and unverified cases.
A passing mock test is not proof that a live integration works.

## Structured logging

Member 5 provides one logger at `backend/app/platform/logging.py`. All modules
use it. API and worker emit structured JSON to stdout with a shared vocabulary.

Fields: timestamp (UTC), level, event, message; requestId, jobId, documentId,
extractionId, submissionId, durationMs, attempt, and errorCode where applicable.
Middleware establishes requestId and propagates it into job metadata. Log IDs
rather than source content so a failed flow can be followed across modules.

INFO: important state transitions and completed operations.
WARNING: recoverable anomalies and scheduled retries.
ERROR: failed operations. Include a safe code and sanitized internal stack trace.
DEBUG: optional diagnostics, off by default. Avoid one log per cell or token.

Canonical events:
- document.uploaded, document.processing_started, document.ready,
  document.failed, document.duplicate_detected;
- extraction.started, extraction.validation_warning, extraction.ready,
  extraction.failed;
- profile.created, profile.version_created;
- review.saved, review.conflict, review.confirmed;
- submission.prepared, submission.applied, submission.unknown, submission.failed;
- job.retry_scheduled.

Never log API keys, authorization headers, cookies, raw OCR, PDF/base64,
prompts/provider response bodies, names, IBANs, financial field values, or
personal filenames. Sanitize exception messages as well as structured fields.
Frontend console output must not expose documents, form contents, or tokens.

Test event names, level, correlation IDs, and redaction with log capture.
Logs are not the audit record: review revisions, confirmations, and external
receipts belong in the database. Operational logs explain where processing
failed without exposing the document itself.

## Completion evidence

A module is complete when behavior works, errors are visible, relevant state is
durable, interfaces match the frozen contract, tests have actually run, naming
and comments are readable, logs are verified, and a handoff exists. The author
then performs final-review; a different person reviews the exact PR head.
The assembled product additionally requires a release review.
