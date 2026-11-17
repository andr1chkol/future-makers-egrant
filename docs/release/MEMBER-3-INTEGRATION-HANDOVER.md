# Integration handover to member 3

Repository: https://github.com/andr1chkol/future-makers-egrant

The user assigned member 3 as the single active integrator. Continue on `codex/documents-integration`, PR #11, targeting `main`. Member 5 stops edits to shared integration source after this transfer and remains available for factual questions and scoped document review. Receipt by member 3 has not yet been confirmed.

## Starting point and history

The verified published assembly is `a5b283f129cf9caed7097d75d71ed0fbd365618a`. This handover adds documentation only; use the current published branch head for continuation. Base `main` and `bootstrap-v1` are `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`. Do not rerun bootstrap.

PR #4 (`codex/integration`, published `74da1644f058f21e5eaf268406368a3e42904a25`) is an ancestor of PR #11. Its profiles/export work is already included. Do not apply it again. Local integration `f9aa0152c444262a733913d3e185e67b2510c7fd` has the same tree as published PR #4 despite different history. Local documents assembly `e35596d9b07834fe230789f80c97b48f2ab78d34` has the same tree as published a5b283f: `f93e10d68452e97a9ff26e622581afb7a96b6b73`. These are publication-history differences, not missing implementation. Never force-push to reconcile them.

## Already connected

Read `docs/release/DOCUMENTS-ASSEMBLY.md` and `docs/release/INTEGRATION-HANDOFF.md` for implementation details and earlier evidence.

- Profiles from PR #8, source `e84509990a84e3121b79b7cd0681912230a61887`, with member 2 exact-head PASS; submissions/export and recovery from PR #5 are included.
- Documents from PR #10 source `9a9bfa5be372fbac5a7408b0648f32ff75cb8460`, plus assembly fixes and the corrected Linux-only parser resource guard, are included. Real document routes replace six shells under `/api/v1` with access protection.
- `document.process` invokes `process_document`; the worker calls `reconcile_interrupted` with a fresh session. Profiles and submissions use real modules. Extraction and review remain shells.
- Document models and migration locations are registered. `0503_documents_assembly` joins `0101_documents` and `0502_profiles_assembly`; the latter already joins profiles and submissions. Preserve published revisions.
- Parser dependencies and lockfiles, Linux Tesseract runtime, raw upload-body limits, private storage checks, orphan cleanup, platform-aware test launchers and document browser CI are included. OCR remains disabled by default. Cleanup entry point: `uv run python -m app.documents.cleanup` from backend.

## Remaining implementation and coordination

1. Obtain independent reviews before assembly: member 1 reviews extraction PR #6 at `f21eb8434a63dd65a9d509c76de9031fad67faaa`; member 3 reviews member 4's review module PR #3 at `133e6ced9cbce21fb255fa77b45d3d335c47ec75`. Green module CI alone is not approval. Reverify heads before applying changes.
2. Member 2 owns the CSV fixture/source-ID blocker. Actual CSV normalization in the assembly produces 23 document-specific UUIDv5 cell units; extraction's old fixture fingerprint returns `FIXTURE_NOT_AVAILABLE`. Preserve authentic source IDs, quotes, coordinates, bytes and hashes, including a second upload with different IDs. Do not substitute the old example document or hardcode an upload UUID. Probe locations: `/private/tmp/egrant-documents-extraction-probe.py`, `/private/tmp/egrant-extraction-compat-source`, `/private/tmp/documents-extraction-probe.log`.
3. PR #9 at `751eef1d8b61e091cd6dafd6203bacb45376a515` is a separate, newer documents candidate, not part of PR #11. It proposes CSV row IDs and a delayed duplicate-handler fix. Coordinate its narrow reviewed changes with member 2. Its parser guard fails the scoped macOS recheck; see `docs/reviews/documents-751eef1-scoped-followup.md`. Do not replace the assembled documents directory wholesale.
4. Connect reviewed extraction through its public interface: remove the four extraction route shells, include its router with `Depends(require_access)`, register `extraction.process` to `process_extraction`, and call `recover_terminal_extractions(session)` in a fresh session alongside submission/document recovery. Set `aiConfigured` using `OpenAIProvider.from_settings(get_settings()) is not None`. Review recovery batch starvation and outstanding HTTP requests after logical provider deadlines; these require reviewer assessment, not an assumed approval.
5. Connect the reviewed review router, models, migration `0401_reviews` and module browser suite. Preserve logger `revision` support and verify review events. Add extraction migration `0201_extractions` and review migration locations, then create a new merge revision joining the current assembly and incoming heads. Do not rewrite `0503_documents_assembly` or earlier published revisions. Update the transactional enqueue migration test with the union of required ancestors and tables; retain its single-head and transaction assertions.
6. Run the combined flow and provider/failure matrices. Check application failure/retry duration logging and carry forward unresolved module review findings from the existing handoffs. Keep frozen contracts and generated client checks intact.

## Reviews and evidence boundaries

`docs/reviews/documents-a5b283f.md` is member 5's completed independent recheck of corrected member 1 document code at exact a5b283f: PASS for that scope only. Its source parity was checked against the reviewed correction. It is not independent approval of member 5's shared assembly. Recheck any document changes adopted after that SHA.

Member 4 reviews the shared/final assembly independently. Member 1 performs final release checks using `docs/team/07-RELEASE-REVIEW.md`, while independent coverage of member 1's own document code remains separate. Use `docs/team/06-PEER-REVIEW.md`; every verdict must name an exact SHA.

Previously recorded assembly evidence: 196 backend tests passed, one Windows skip; 32 frontend tests; 12 browser tests across foundation/submissions/profiles/documents; empty-volume Linux Compose upload/worker/storage checks. Exact a5b283f CI run `41111273890` succeeded. The independent document recheck recorded 105 backend tests passed, one skip, 32 frontend tests and two document browser tests, plus lint/format/lock/schema checks. Logs: `/private/tmp/egrant-peer-a5b283f-tests.log` and `/private/tmp/egrant-peer-a5b283f-browser.log`.

Those are earlier scoped results, not a fresh full-suite run for this documentation handover. The latest candidate follow-up exercised only a simulated Darwin resource-limit failure. Synthetic Tesseract smoke evidence is separate from live paid-provider checks and real Slovak OCR accuracy. Full extraction → review → export acceptance is still pending.

## Reproduction

Use a fresh clone or an available worktree; preserve existing dirty worktrees.

```sh
git clone https://github.com/andr1chkol/future-makers-egrant.git
cd future-makers-egrant
git fetch origin --tags
git switch --track origin/codex/documents-integration
git rev-parse HEAD
cp .env.example .env
make install
make dev
```

Follow README and DOCUMENTS-ASSEMBLY for local services and separate test database setup. Never point tests at production data. Database guards require an `egrant_test` name; the document browser suite specifically expects `egrant_test_documents_e2e` through `DOCUMENT_E2E_DATABASE_URL`.

```sh
make check
make test
make e2e
make e2e-integration
make e2e-profiles
make e2e-documents
```

After connecting incoming modules, include their module checks/browser suites in CI and rerun the full combined acceptance path. Existing shell responses are not proof that an incoming module is connected.

## Configuration and final acceptance

Use `.env.example` for exact defaults. Safe variable names include `APP_MODE`, `DATABASE_URL`, `FILE_STORAGE_PATH`, `PUBLIC_ORIGIN`, `DEV_AUTH_BYPASS`, `COOKIE_SECURE`, `ACCESS_CODE`, `POSTGRES_PASSWORD`, `DB_PORT`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OCR_BASE_URL`, `OCR_API_KEY`, `EGRANT_BASE_URL`, `EGRANT_TOKEN`, and `DOCUMENT_*` parser, upload, deadline and OCR controls. No secret values are part of this transfer. Set the OpenAI model explicitly with the team; an earlier live gpt-4.1-mini check does not select the final model. Tesseract is opt-in through document OCR configuration.

Acceptance must use a real upload, persisted normalization, extraction draft, reload, human correction and confirmation, then export of confirmed scalar and row values. Cover a second profile/upload, duplicate requests, provider failures, recovery, revision conflicts and idempotency. Missing values stay null, fixture mode stays visible, drafts stay separate from confirmed data. Export is not application submission. External eGrant writes require an identified test target and explicit human confirmation; no live application write is authorized by this handover.

## Preserved work and publication

The handover commit contains this document, the previously unpublished scoped a5b283f review, the bounded PR #9 follow-up, and `docs/reviews/member-5-status-f9aa015.md`. The latter is a historical status snapshot of the older profiles/export integration, not current acceptance evidence or required runtime implementation. Its original untracked copy remains untouched in the main local checkout.

Existing integration, assembly and peer-review worktrees/commits are preserved. No credentials, environment files, private uploads or unrelated source edits are included. Publication uses a normal fast-forward update of PR #11's branch; local and connector-created commit identities may differ while trees match. Member 3 should fetch the published head, implement on that continuation branch, publish normal commits to PR #11, request the stated independent reviews and keep the PR Draft until acceptance is complete. Do not merge PRs, move tags, deploy or force-push as part of this transfer.
