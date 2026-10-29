# Bootstrap prompt — member 5 runs this first

You are preparing the shared foundation for five people implementing one eGrant
document-extraction product. Use the EXISTING repository:
https://github.com/andr1chkol/future-makers-egrant.
Do not create another GitHub repository or overwrite existing project history.

## Goal

Deliver one verified baseline that every member can clone and implement against:
shared runtime, contracts, types, UI conventions, database infrastructure,
fixtures, worker interfaces, logging, and reproducible commands. This step
prepares module development; it does not implement members 1–4's business logic.

## Required reading and skills

Read AGENTS.md, docs/team/README.md, CONTRACT.md, QUALITY.md, and the existing
repository instructions/code. Read the bundled human-code, humanizer, and
final-review skills. Apply api-and-interface-design and codebase-design if
available. Consult official documentation when choosing compatible versions.
Keep code/comments/logs/tests in English and product UI copy in Slovak.

## Step 1 — establish the real repository state

Inspect Git status, remotes, history, default branch, current branches, existing
application code, and CI. Preserve useful code and uncommitted changes.
If this local folder is not the team clone, clone the provided repository into
a suitable separate directory rather than combining unrelated histories.
If credentials are unavailable, report the exact access problem; do not create
a replacement repository. Never overwrite an existing origin without checking.

Create a setup branch, such as codex/bootstrap, from the real integration branch.
Record that branch as BASE_BRANCH in contracts/internal.md. If instruction files
already exist, reconcile them instead of blindly replacing team conventions.
Identify architecture conflicts with CONTRACT.md before implementing a competing
stack; propose the smallest coordinated resolution and record the outcome.

## Step 2 — freeze the interfaces before parallel development

Create contracts/api.yaml for every documented route, request, response, enum,
error envelope, pagination shape, binary response, and asynchronous status.
Define public Pydantic DTOs in app.platform.contracts. Generate the typed
frontend client and shared TypeScript types rather than duplicating them.

In contracts/internal.md specify exact function signatures, return DTOs,
Session usage, sync/async behavior, error classes, imports, job handler
registration, and module router assembly. Define warning identities,
acknowledgment behavior, and confirmation retry semantics consistently.
Resolve ambiguities before the baseline, not independently in five agents.

Create validated examples for form, profile, document, normalized-document,
extraction, review, and submission. Include money strings, table rows,
source references, a missing field, warnings, and human corrections.

## Step 3 — implement the foundation

Set up the agreed frontend/backend structure and exact dependency lockfiles.
Provide PostgreSQL sessions, settings, private file storage, domain errors,
request correlation, shared structured logging with redaction, and the access
gate. Create the initial database migration and reserve each module's migration
prefix. Provide one durable jobs implementation with leases, bounded retry,
crash recovery, and explicit document/extraction/submission handler registration.

Expose the shared UI primitives, palette, typography, generated API client,
QueryClient, and route assembly. Add named feature entrypoints as shells for
members 1–4. Unimplemented live features return an explicit unavailable state.
The initial shell is not evidence that business functionality is complete.

Provide fixture mode with a persistent visible banner. Include one synthetic
invoice whose actual text agrees with all expected extraction values and rows.
Do not depend on paid APIs to start or test the shared foundation.

## Step 4 — reproducible workflow and verification

Provide Compose for db/api/worker/frontend and documented make dev, make check,
make test, and make e2e commands. Configure CI and example-schema checks.
The fully assembled route-coverage test may start as a documented pending check;
do not fake passing coverage for unimplemented modules.

Test foundation behavior: migrations on an empty database, settings validation,
logger redaction/correlation, worker claim/recovery, access gate, generated
client build, fixture-schema validation, and no-provider startup behavior.
Document required dependency/registration requests so teammates can work without
editing shared files. Write .env.example with names and safe placeholders only.

Apply human-code, humanizer to prose, and final-review to the actual diff.
Fix findings and rerun relevant checks. Commit the verified baseline through
the team's PR process. Member 4 independently reviews bootstrap changes.
After approval/checks, publish the immutable bootstrap-v1 tag and exact SHA.
If the tag already exists, verify it; never move it to a different commit.
Provide the actual repository URL, BASE_BRANCH, baseline SHA, clone/start
commands, and any remaining access blockers. Do not claim a push that failed.

## Completion criteria

A clean clone starts using the README; contracts and examples validate; lockfiles
exist; shared imports and signatures are settled; logging/access/jobs work;
fixture mode is explicit; no secret is committed. Members 1–4 can implement
without inventing missing shared conventions. Then continue with
05-INTEGRATION-PROMPT.md on codex/integration.
