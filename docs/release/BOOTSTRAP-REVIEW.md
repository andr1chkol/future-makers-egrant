# Bootstrap self-review and handoff

Reviewed code commit: `2efe0db6d35b40301cc70f0b019d6811de254779`.
Reviewed tree: `629dc73760b1008fedcebbb3278a77a7200357fd`.
Base: `787bf7bc97f1e3dfa22f455660e2e0ca22c6551c` on `main`.
Repository: https://github.com/andr1chkol/future-makers-egrant.
PR: https://github.com/andr1chkol/future-makers-egrant/pull/1.

Verdict for this SHA: PASS for the foundation scope; ready for independent review.
The assembled product is NOT READY. This is the author's self-review, not member
4's independent review. This report is a documentation-only follow-up to the
reviewed code commit. Member 4 must review the final PR head, including this file.

## Delivered scope

The repository preserves its main history and origin/master. The original main
contained only a README; no application architecture or CI needed reconciliation.
BASE_BRANCH is main; setup is codex/bootstrap. The instruction package and root
contract/quality copies are included. Tests enforce equality of the copies.

Public Pydantic DTOs generate the OpenAPI contract and TypeScript client. Linked
examples cover forms, profile versions, documents, normalized sources, money,
table rows, missing values, warning acknowledgement and a human correction.
Every frozen domain route is present as a typed unavailable shell. Exact module
imports, transactions, registration and migration ranges are in
contracts/internal.md. Feature pages export through the named index.ts files.

Platform scope includes PostgreSQL sessions, validated settings, private immutable
file storage, domain error envelopes, cookie sessions, CSRF Origin checks, request
correlation, stdout JSON logging with allowlisted context, and durable jobs.
Jobs use skip-locked claims, lease tokens, bounded attempts and expired-lease
recovery. Apply jobs never automatically repeat a possibly external effect.
Handlers remain explicit unavailable registrations until domain implementation.

Compose runs db/api/worker/frontend. The visible fixture shell starts without
paid providers. All provider capabilities remain false. Shared UI conventions,
contrast measurements and the requested UI UX Pro Max application are documented
in UI-CONVENTIONS.md. No live features are represented as successful demos.

## Final-diff findings fixed before the reviewed commit

- Upgraded the initial frontend test stack to compatible Vite 8.3.5, Vitest 5.0.5
  and plugin-react 6.1.2 after npm advisories. The resolved lock reports zero
  known npm vulnerabilities. Python and npm transitive versions are locked.
- Fenced job completion by lease token and expiry. A late-worker regression
  verifies that a reclaimed job remains owned by its replacement worker.
- Hid settings input values in validation errors. Redaction tests cover secret
  fields, personal filenames, financial values and exception messages.
- Specified the export attachment as an envelope-free SubmissionPayload and
  documented its filename convention. Cookie authentication is in OpenAPI.
- Made shared structured logs use stdout and preserved request-to-job IDs.
- Added the skip link, inline linked login error, focus restoration, reduced
  motion and scalable layouts. Login rejection in the browser test is an
  explicit mocked response; server-side cookie tests use real PostgreSQL.

## Executed verification

All results below apply to the reviewed code SHA. Python 3.12.6, Node 26.5.0
and Docker Desktop were used locally. Container frontend uses Node 22; CI uses
Node 22 and Python 3.12. PostgreSQL tests require major version 16.

| Check | Result | Evidence and scope |
|---|---|---|
| make check | PASS, exit 0 | Lock consistency, Ruff, Prettier, credential pattern scan, generated schema/client drift, TypeScript and Vite build |
| make test | PASS, exit 0 | 32 backend tests on isolated PostgreSQL 16 and one component test |
| make e2e | PASS, exit 0 | Three Chromium shell/accessibility scenarios; 375–1440 px, enlarged text, reduced motion, keyboard and login error |
| Empty database migration | PASS | Each database test resets its explicitly named egrant_test database and runs Alembic upgrade head |
| Session access/content gate | PASS | Unauthorized content blocked; durable hashed cookie sessions, expiry, revocation and Origin rejection |
| Worker reliability | PASS | Transactional enqueue rollback, concurrent locked claim, crash recovery, bounded retry, unavailable handlers and late completion |
| Fixture/source agreement | PASS | Seven examples validate as DTOs and JSON Schema; exact quotes, hash, rows and separate human correction match the CSV |
| No-provider startup | PASS | Fixture mode starts without provider keys; keys alone cannot enable unimplemented adapters |
| Clean-clone checks/tests | PASS | New clone, locked installs, check/test/e2e; working tree clean afterward |
| Clean-clone Compose | PASS | New database/private-files volumes; db and API healthy, worker/frontend running, migration 0001_platform and proxy capabilities verified |
| GitHub Actions | PASS | Push and PR runs succeeded for the reviewed code SHA |
| Independent member-4 review | NOT VERIFIED | Required in a fresh chat before baseline publication |
| Complete domain route compatibility | NOT VERIFIED | Explicitly pending assembly; shell coverage is not implemented-business-route coverage |
| Document → extraction → review → confirm → export | NOT VERIFIED | Domain modules are intentionally unavailable |
| Live OCR, AI, eGrant write/reconciliation | NOT VERIFIED | No adapters or authorized external write tests in this scope |

The credential check is a pattern scan of tracked content, not proof against
every possible secret format. No real credential was supplied or committed.
A Starlette TestClient deprecation warning for httpx remains; tests passed.
The npm whatwg-encoding deprecation and terminal color warnings are non-failing.

### Commands and clean-clone procedure

The uv executable was installed in the ignored project tools environment. The
same version is pinned in Docker/CI. These were the clean-clone commands:

```sh
git clone --branch codex/bootstrap --single-branch https://github.com/andr1chkol/future-makers-egrant.git /private/tmp/egrant-bootstrap-verify-20261029
cd /private/tmp/egrant-bootstrap-verify-20261029
make install UV='/Users/Andrew/Documents/ChatGPT/FUTURE-MAKERS/future-makers-egrant/.tools/bin/uv --cache-dir /private/tmp/egrant-bootstrap-uv-cache'
make check UV='/Users/Andrew/Documents/ChatGPT/FUTURE-MAKERS/future-makers-egrant/.tools/bin/uv --cache-dir /private/tmp/egrant-bootstrap-uv-cache'
TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test make test UV='/Users/Andrew/Documents/ChatGPT/FUTURE-MAKERS/future-makers-egrant/.tools/bin/uv --cache-dir /private/tmp/egrant-bootstrap-uv-cache'
make e2e
cp .env.example .env
docker compose up --build -d
docker compose ps
curl --fail --silent http://localhost:5173/api/v1/capabilities
docker compose exec -T db psql -U egrant -d egrant -Atc 'SELECT version_num FROM alembic_version'
git status --short
```

All commands exited 0; git status produced no tracked or untracked changes.
The isolated test PostgreSQL container was started using the README command
before these checks. Playwright Chromium was installed with
`npm exec --prefix frontend -- playwright install chromium`. Host access to
Docker, localhost sockets and package registries required sandbox escalation.
The implementation also passed the same checks in the primary clone.

CI evidence for the reviewed code SHA:
[push run](https://github.com/andr1chkol/future-makers-egrant/actions/runs/40931445366),
[PR run](https://github.com/andr1chkol/future-makers-egrant/actions/runs/40931651042).
Desktop/mobile captures are ignored local artifacts and uploaded by CI.

## Reliability limits and ownership requests

Handlers must complete within the 60-second lease or split work into durable
phases. There is no lease renewal in this baseline. Domain owners must make
persisted results idempotent; queue fencing alone cannot fence a provider effect.
Apply outcomes that may have written remotely need owner reconciliation to
unknown before further attempts. That integration remains unavailable.

The access gate is a single-workspace demo, not tenant authorization or eGrant
identity. Shared deployments require TLS, secure cookies, a random access code
and a trusted proxy with authentication rate limits. Keep development ports local.

Module owners provide their exact service imports, routers, handlers and migrations
through handoffs and reviewed PRs. They do not edit shared locks or assembly.
Migration prefixes are reserved; no domain schema or business logic was added.

## Release gate assessment using 07-RELEASE-REVIEW.md

The bootstrap startup, platform checks, contracts and UI shell have evidence.
The central assembled workflow, actual provider matrix and independent module
reviews do not. Do not present this foundation as a completed hackathon product.

bootstrap-v1 does not exist and was not published. After member 4 approves the
exact final PR head and checks pass, the team can merge through its process and
tag the approved baseline without moving an existing tag. Publish that immutable
SHA before members 1–4 start. Then continue 05-INTEGRATION-PROMPT.md on
codex/integration. Member 1 performs the assembled release review after integration.
