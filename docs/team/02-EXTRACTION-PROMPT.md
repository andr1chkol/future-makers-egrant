# Member 2 — AI extraction, evidence, and validation

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

Branch: codex/extraction. Own backend/app/extraction/**,
backend/app/validation/**, tests/extraction/**, and
docs/handoffs/02-extraction.md. Use migration prefix 020*.

Deliver a profile-driven extractor: normalized source units and a frozen
profile version produce validated fields, table rows, supporting sources,
and warnings that a person can review. The same extractor must support another
form without changing its code or hardcoding that form's destination tags.

## Implementation tasks

### 1. Extraction lifecycle

Implement creation, listing, detail, and failed-attempt retry routes exactly
as contracted. A batch creates one extraction per document. Persist the profile
snapshot and processing state. Implement extraction.process using the shared
worker. Obtain documents and profiles through their public module functions.
Do not access their private tables or manufacture a separate job system.

### 2. AI provider and schema-constrained output

Implement a backend-only AI adapter using the configured model. Consult the
available openai-docs skill and official SDK documentation if applicable.
Use profile-derived structured output and validate every provider response
against the shared types. Treat provider output and document contents as
untrusted data. Embedded instructions must not override extraction rules.

Handle timeouts, rate limits, malformed output, and provider errors with bounded
retries and meaningful failure states. Keep credentials, prompts, document text,
and response bodies out of logs. Tests use deterministic fake adapters; live
mode never silently substitutes a fixture.

### 3. Extraction behavior

Support invoice, receipt, bank-statement, and contract profiles through field
and table descriptions. Distinguish supplier from buyer and net from tax/gross
amounts. Keep currencies explicit. Return null when a value is absent rather
than guessing it. Preserve line-item correspondence and row IDs in saved output.
Do not merge separate input documents silently.

Validate supporting SourceRef values against actual normalized unit IDs. Check
exact quotes where supplied. Missing or unverifiable evidence must be reflected
in field status and warnings; do not invent page numbers or coordinates.
Normalize decimal strings and dates only when the interpretation is supported.

### 4. Domain validation

Check types, required fields, permitted option keys where applicable, date
ambiguity, currency consistency, and arithmetic relationships. Define and
comment monetary rounding tolerance. Report inconsistent totals without
rewriting extracted values to make the numbers match. Calculated suggestions
must not be presented as directly observed document facts.

Persist results atomically where appropriate. Retrying a failed attempt must
not erase a human review or regenerate row IDs on every read. Use the shared
failure and state-transition conventions.

### 5. Evaluation and operational evidence

Prepare permitted test documents with manually checked expected values.
Separate tuning examples from held-out evaluation cases. Implement a repeatable
evaluator for fields and table rows. Report sample counts, correct values,
missing values, unsupported/incorrect values, and invented values. Do not
publish accuracy percentages without an actual executed evaluation.

Emit extraction.started, extraction.validation_warning, extraction.ready,
extraction.failed, and retry events with IDs, duration, attempts, and safe codes.
Comment evidence-matching assumptions, provider quirks, normalization choices,
and validation tolerances where a maintainer needs the reasoning.

## Tests you must implement and run

- Missing fields, supplier/buyer confusion, monetary roles, currencies, dates,
  multi-page documents, and repeated table rows.
- Document prompt injection, invalid JSON, wrong types, unexpected keys,
  fabricated unit IDs, and unsupported evidence quotes.
- Arithmetic mismatches and OCR noise without silent invented corrections.
- Rate limits, timeout, bounded retry, duplicate job execution, and persistence.
- API/schema compatibility, state transitions, stable row IDs, and log redaction.
- A repeatable held-out evaluation; a separately enabled permitted live call
  when credentials are available.

## Acceptance and handoff

The review module receives schema-valid output with defensible evidence and
explicit uncertainty. A different profile works through the same extractor.
Document tested provider modes, exact evaluation commands/results, module
interfaces, job registration, migrations, limits, and external blockers.
Independent reviewer: member 1.
