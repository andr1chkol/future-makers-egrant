# Team implementation prompts

Build one product for hackathon challenge 1: document extraction that proposes
form values, lets a person review them, and exports or applies confirmed data.
The five prompts describe five connected modules of that product.

Team repository: https://github.com/andr1chkol/future-makers-egrant.
This package contains instructions, not an implemented application. The current
local folder may not yet be connected to the existing remote repository.

## Start here

1. Assign members 1–5. Member 5 is responsible for the shared foundation and
   integration, not for implementing everyone else's work.
2. Member 5 runs the complete prompt in `00-BOOTSTRAP.md` against the EXISTING
   repository. Inspect its branches, history, code, and CI first. Do not create
   another repository or overwrite existing code with a new scaffold.
3. Agree on the actual integration branch. Record it as `BASE_BRANCH` in
   `contracts/internal.md`; use the real branch rather than assuming `main`.
4. Member 5 publishes the reviewed foundation, machine-readable contract,
   shared fixtures, lockfiles, and an immutable `bootstrap-v1` tag. Publish
   the exact baseline SHA in the team chat. Never move an existing tag.
5. Everyone clones the same repository, opens the clone's root in Codex, and
   pastes the ENTIRE matching implementation prompt. The prompt tells Codex
   which shared documents to read. Do not start independent apps.
6. Each author opens a PR into BASE_BRANCH after implementation and self-review.
   A different person reviews that PR in a fresh Codex chat. Member 5 coordinates
   merges after independent review and checks. Run the release review afterward.

If this instruction package is not yet in the team repository, member 5 first
copies `AGENTS.md`, `docs/team/`, `docs/planning/TEAM-PLAN.md`, and the bundled
skills into a setup branch. Reconcile any existing instructions instead of
blindly overwriting them. Commit these files through the normal PR workflow.
The ZIP is a distribution artifact; it does not need to be committed.

## Clone and branch

```sh
git clone https://github.com/andr1chkol/future-makers-egrant.git
cd future-makers-egrant
git fetch origin --tags
git switch -c codex/documents bootstrap-v1
```

The last line is the example for member 1. Other members use their own branch:

| Member | Branch | Prompt |
|---|---|---|
| 1 | codex/documents | 01-DOCUMENTS-PROMPT.md |
| 2 | codex/extraction | 02-EXTRACTION-PROMPT.md |
| 3 | codex/profiles | 03-PROFILES-PROMPT.md |
| 4 | codex/review | 04-REVIEW-PROMPT.md |
| 5 | codex/integration | 05-INTEGRATION-PROMPT.md |

If the branch already exists, inspect and resume it; do not recreate or reset it.
Synchronize with `git fetch origin` and merge the recorded BASE_BRANCH after
saving your own work. Do not force-push shared branches or rewrite other work.

## External inputs to obtain

- Test eGrant access for manager and applicant roles.
- Actual form JSON exports and permitted sample documents.
- OCR API documentation and credentials.
- The documented interface for writing confirmed values into an application.
- Allowed AI providers, data-handling rules, and budget.
- The exact submission time, timezone, and channel for October 30, 2026 EOD.

Replace previously exposed keys. Configure new credentials locally; never place
them in a prompt package or repository. Use anonymized or synthetic Git fixtures.
Missing external access blocks that integration, not unrelated implementation.

## Shared contract and parallel work

`CONTRACT.md` is the authoritative design specification; `QUALITY.md` defines
engineering quality. Bootstrap turns the contract into `contracts/api.yaml`,
`contracts/internal.md`, generated types, and validated example files.
Resolve inconsistencies BEFORE publishing bootstrap-v1. Afterward, contract
changes require a coordinated PR updating schemas, examples, clients, and tests.

Work against the same fixtures while neighboring modules are being implemented.
Run the first assembled flow after roughly 2–3 hours, then integrate regularly.
Each owner fixes defects in their module. Do not wait until all five modules
are supposedly finished before connecting them.

## Independent review assignments

- Member 5 reviews member 1.
- Member 1 reviews member 2.
- Member 2 reviews member 3.
- Member 3 reviews member 4.
- Member 4 reviews member 5, including bootstrap and later integration changes.

Use `06-PEER-REVIEW.md` in a fresh chat with the exact PR URL and head SHA.
Member 1 performs `07-RELEASE-REVIEW.md` on the assembled release. Because member
1 also wrote the documents module, member 5's independent review must cover
that module; member 1's release review does not replace it.

Matching prompts alone cannot guarantee compatible code. Compatibility is
established by one repository, frozen interfaces, shared fixtures, generated
clients, contract tests, and evidence from the assembled application.
