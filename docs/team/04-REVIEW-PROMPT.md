# Member 4 — human review, correction, and confirmation

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

Branch: codex/review. Own backend/app/reviews/**,
frontend/src/features/review/**, tests/reviews/**, and
docs/handoffs/04-review.md. Use migration prefix 040*.

Deliver the main applicant workflow: inspect source evidence, correct scalar
values and table rows, save a draft, and explicitly confirm a valid revision.
The integration module must receive the person's final corrections rather
than the original AI proposal.

## Implementation tasks

### 1. Durable review state

Implement review retrieval/initialization, draft updates, and confirmation.
Initialize from a ready extraction only. Preserve the original extraction;
store a complete editable snapshot separately. Use expectedRevision for every
write. Return 409 on stale updates and preserve the user's unsaved edits in UI.

Validate field keys, table keys, stable row IDs, value types, and allowed
selection values. Give new human-created rows UUIDs. Once confirmed, a v1
review is immutable; clearly explain the new-run path for further changes.

### 2. Explicit confirmation

Confirm transactionally after checking required fields, types, warnings,
acknowledgments, and the pinned profile. Implement get_confirmed_review exactly
as the shared interface requires. Repeating an already acknowledged confirmed
revision returns the same result; stale confirmation uses the documented
conflict/re-fetch behavior. Never auto-confirm from background processing or
from an AI response.

### 3. Review interface

Export ReviewPage with document preview beside editable values and a useful
line-item table. Provide missing/needs-review/edited indicators, issue filtering,
source navigation, add/delete/edit rows, draft save, reload recovery, and a
final summary before confirmation. Keep AI proposals distinguishable from
human changes. Do not overwrite local edits on background refetch.

For PDF/images, navigate to a supported page; highlight only when actual
coordinates exist. For spreadsheets, show safe sheet/cell context without
executing content. Make keyboard interaction and narrow-screen layouts usable.

### 4. Hand-off to submission

Only after confirmation call member 5's shared submission interface. Offer JSON
export separately from eGrant apply, according to capabilities. Reuse the same
Idempotency-Key for retries of the same submission intent. Explain unknown or
failed external outcomes; do not blindly trigger another external insertion.

Show overwrite consequences before replace mode. If current target state cannot
be retrieved safely, external replace is unavailable. This module does not
write directly to eGrant or construct arbitrary destination tags from the UI.

### 5. Logs and comments

Emit review.saved, review.conflict, and review.confirmed with extraction ID,
revision, request correlation, and safe failure codes. Do not log corrected
values or document text. Comment revision-conflict behavior, immutable
confirmation, stable row identity, refetch protection, and submission retry
semantics where the reasoning is not obvious.

## Tests you must implement and run

- Missing required values, money/date edits, invalid types, unknown keys,
  duplicate row IDs, and row creation/deletion.
- Draft persistence, reload, stale PUT conflict, and preservation of local edits.
- Concurrent confirmation, repeated confirmation, stale revision recovery,
  and rejection of mutations after confirmation.
- Source navigation and loading/empty/error/retry/keyboard/mobile states.
- No submission/apply before confirmation; corrected human values appear in
  the subsequent payload rather than old extracted values.
- Structured log revision/ID assertions and content/secret redaction.

## Acceptance and handoff

A person completes review without losing edits or accidentally committing data.
Server-side rules enforce the same protections even if UI checks are bypassed.
The confirmed immutable revision is consumable by member 5. Document public
interfaces, migration, page export, confirmation semantics, commands/results,
manual scenarios, known limitations, and integration blockers.
Independent reviewer: member 3.
