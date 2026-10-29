# Member 3 — form import and extraction profile builder

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

Branch: codex/profiles. Own backend/app/profiles/**,
frontend/src/features/profiles/**, tests/profiles/**, and
docs/handoffs/03-profiles.md. Use migration prefix 030*.

Deliver a usable manager workflow for importing a form and configuring what
information to extract and where it belongs. A manager can configure a second
form with different tags and table columns without editing extraction code.

## Implementation tasks

### 1. Form definition import

Implement form import, listing, and detail. Preserve the original JSON tree
including unknown configuration. Build a usable normalized view of sections,
fields, tables, tags, labels, required flags, types, and selection options.
Destination tags are stable addresses; changing a label must not rename a tag.

Verify the real eGrant importer against supplied exports. If those exports are
unavailable, support the agreed illustrative example and label it visibly as
illustrative. Do not claim universal eGrant compatibility. Treat imported text,
HTML, and script-like content as data, never executable UI code.

### 2. Profile persistence and versioning

Implement the contracted profile routes, immutable versions, and expectedVersion
conflict handling. Keep previous versions retrievable. Implement get_form and
get_profile using the exact shared signatures. Extractions must continue to
resolve the version/snapshot they were created with after a manager edits the
latest profile.

### 3. Manager configuration UI

Export ProfilesPage and ProfileEditorPage. Provide searchable form navigation,
field/table selection, extraction labels, types, descriptions, required flags,
and target-tag mapping. For tables, map individual extraction columns to form
columns and explicitly configure append versus replace.

Validate unique keys, existing destination tags, type compatibility, and option
keys rather than display labels. Preserve unsupported settings and explain
limitations rather than silently dropping them on save. Show field-level
validation errors, loading states, unsaved changes, version status, and failures.

Provide editable starter profiles for invoices, receipts, bank statements, and
contracts. A starter profile is a configuration example, not evidence that
extraction accuracy has been tested for that category.

### 4. Trial run and integration

Allow a saved profile version to be tested against an existing document using
the shared POST /extractions route. Navigate to the review route instead of
building a second extraction/review mechanism. Respect provider capabilities.
Prepare two distinct form examples with different scalar tags/table mappings
and demonstrate that both produce valid configuration for the same extractor.

### 5. Logs and comments

Emit profile.created and profile.version_created with profile/form IDs and
version. Use safe import error codes rather than logging the entire form,
field descriptions, or personal values. Add comments explaining immutable
versions, unknown-setting preservation, destination-tag stability, and the
option-key/display-label distinction.

## Tests you must implement and run

- Invalid and hostile form JSON, duplicate tags/keys, and unsupported types.
- Missing destination tags, incompatible mappings, and table column errors.
- Preservation of unknown configuration and original JSON across round trips.
- Stable tags after label changes, selection option keys, and required flags.
- Previous versions unchanged after updates and concurrent save conflicts.
- Public get_profile compatibility and extraction use of a pinned version.
- UI import, configure, save, reopen, unsaved changes, and trial-run navigation.
- Structured log events/version correlation without raw imports or PII.

## Acceptance and handoff

A manager can configure and save two meaningfully different form mappings and
launch a trial run without editing code. The extraction, review, and integration
modules consume the same immutable profiles. Document actual import formats,
illustrative limitations, routes/imports, migrations, UI entrypoints, tested
cases, and required shared registrations.
Independent reviewer: member 2.
