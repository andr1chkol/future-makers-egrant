# Member 5 — shared platform, integration, and release assembly

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

## Prerequisite, ownership, and expected outcome

First complete 00-BOOTSTRAP.md in the existing repository and publish the
verified bootstrap-v1 baseline through team review. Then use codex/integration.
Own the member-5 paths listed in CONTRACT.md, migration prefixes 000*/050*,
and docs/release/INTEGRATION-HANDOFF.md.

Deliver one runnable product connecting all four domain modules. Confirmed
human-reviewed data becomes a reliable export or a documented eGrant write.
A teammate can start the project from a clean clone using only the README.
You coordinate integration; each domain owner remains responsible for fixing
their module's defects.

## Implementation tasks

### 1. Complete and maintain the shared platform

Finish database/session/settings/storage/error infrastructure, shared logger,
request correlation, and the access gate. Maintain one durable job queue with
leases, bounded retries, recovery, and explicit handler registration. Connect
document.process, extraction.process, and submission.apply through public
interfaces documented in handoffs. Keep provider HTTP outside long database
transactions. Ensure worker crashes and duplicate jobs are handled deliberately.

Own manifests, locks, generated clients, shared DTOs, and contract maintenance.
Process teammates' dependency/registration requests promptly. A schema change
requires a coordinated PR updating every example, client, and affected consumer.
Reconcile migration branches without rewriting published migration history.

### 2. Assemble a consistent application

Provide the shared navigation, routes, UI controls, typography, spacing,
QueryClient, API client, and capabilities display. Connect UploadPage,
ProfilesPage, ProfileEditorPage, and ReviewPage. Implement processing history
and the submission/export status page. Handle real empty/loading/error states
and responsive layouts. Do not populate live history with fixture records.

### 3. Build confirmed submission payloads

Construct submission payloads server-side from the exact confirmed review
revision and frozen profile mapping. Reject draft, stale, invalid, or unknown
mapping data even if the browser submits it. Store the operation and request
hash before any external effect. Enforce Idempotency-Key through database
constraints and transaction-safe logic; same key/body returns the existing
operation, while changed intent with the same key is a conflict.

Implement downloadable JSON independently from live eGrant access. Export is
not proof of application. Expose durable prepared/exported/applying/applied/
failed/unknown states according to the contract.

### 4. Integrate eGrant honestly

Use the actual documented interface for writing application values. Form
structure editing is not application-data insertion. Do not invent endpoints.
If the required API or test credentials are unavailable, expose capability=false,
document the missing interface precisely, and keep export functional.

Apply through the durable job/outbox path. A timeout after a possible remote
write becomes unknown until receipt/state reconciliation, not an automatic
blind insert retry. Support append/replace only with documented semantics;
replace requires a known current state, preview, and explicit acknowledgment.

### 5. Access, logs, and operational checks

Protect APIs and file access through the agreed gate. Use server-issued HttpOnly
cookies and keep secrets out of frontend bundles, URLs, fixtures, and logs.
Keep local fixture authentication visibly distinct from verified eGrant auth.
Do not claim production tenant isolation from a single-workspace demo.

Implement and test the shared JSON logger/redaction and propagation from request
to jobs. Emit submission.prepared/applied/unknown/failed and worker retry events
with IDs, safe codes, durations, and attempts. Comment transaction/outbox,
idempotency, uncertain outcomes, reconciliation, and authorization limitations.

### 6. Integration discipline and release materials

Integrate independently reviewed PRs through the recorded BASE_BRANCH. Run
shared checks after merges and return domain defects to their owners. Maintain
README clean setup, .env.example, architecture/integration explanation,
provider-mode matrix, sample-data instructions, evaluation links, demo script,
and release checklist. Apply humanizer to prose without changing technical facts.

## Tests you must implement and run

- Example/schema validation, generated frontend typecheck/build, and runtime
  OpenAPI compatibility after all modules are registered.
- Real PostgreSQL transaction, concurrent submission, and idempotency tests.
- Worker restart/retry and uncertain remote outcomes without duplicate apply.
- Rejection of unconfirmed/stale reviews and exact export of human corrections.
- Access gate/content checks, request/job correlation, and log redaction.
- Playwright full flow, another profile, draft reload, missing value, duplicate,
  provider failure, revision conflict, and responsive application layout.
- Clean-clone README startup and migrations on an empty database.
- Separately authorized live provider/eGrant checks, distinguished from fixtures.

## Acceptance and handoff

The assembled product passes the documented checks or reports precise remaining
blockers. Each capability is honestly classified as live-verified, fixture-only,
or unavailable. A confirmed correction survives into the exported/applied result;
retries do not duplicate writes. Setup, operating modes, test evidence, integration
limits, and delivery steps are documented in English.

Independent reviewer: member 4, including bootstrap and later integration code.
After merges, member 1 runs 07-RELEASE-REVIEW.md on the exact final BASE_BRANCH
commit. Do not replace that independent check with your own self-review.
