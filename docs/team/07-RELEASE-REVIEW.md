# Independent assembled-product release review prompt

Member 1, or another person who did not implement the main integration, runs
this in a fresh Codex chat after the five modules have been merged into the
recorded BASE_BRANCH. Member 5's independent review of member 1's document
module remains required; this release pass does not replace module peer review.

You are reviewing the assembled product in the existing repository:
https://github.com/andr1chkol/future-makers-egrant.
The goal is evidence that the complete workflow works, not five individually
convincing implementation reports.

## Required context

Read AGENTS.md, CONTRACT.md, QUALITY.md, the machine-readable contract,
internal interfaces, examples, module handoffs, and prior peer-review reports.
Apply bundled final-review and human-code. Apply humanizer to the English
release report only, preserving commands and evidence.
Inspect the release diff from bootstrap-v1 and surrounding code. Also inspect
the bootstrap/platform implementation and its review report: base code is
part of the delivered product, even when outside the release diff.

## Verification tasks

1. Record the exact release SHA. Use a clean checkout and follow the README
   from scratch, including environment setup and migrations. Do not depend
   on unexplained local files, cached database state, or hidden credentials.
2. Run make check, make test, and make e2e. Check lockfile consistency, generated
   types, runtime API/schema compatibility, shared imports, handler registration,
   and migration-head reconciliation. Capture actual command outcomes.
3. Run the fixture workflow: import form -> configure profile -> upload ->
   extract -> review -> edit -> confirm -> export. Compare exact corrected
   values and table rows with the generated submission payload.
4. Verify no target application write occurs before confirmation. Exercise stale
   revisions, repeated submit, missing required values, invalid mappings,
   append/replace behavior, duplicate files, worker restart, and uncertain
   provider outcomes. Confirm retries cannot silently duplicate remote writes.
5. With permitted files and configured providers, test a real PDF, a poor scan
   or photo, XLSX/CSV, another profile, supplier/buyer separation, missing fields,
   inconsistent totals, and provider failure. Mark unavailable access as
   NOT VERIFIED, never as a live pass based on a fake provider.
6. Test an actual eGrant write only on an authorized test application and with
   explicit human permission for the test write. Verify receipt/current values
   and absence of duplication. JSON export alone is not an eGrant integration
   test. Document unavailable interfaces rather than inventing endpoints.
7. Inspect application behavior on desktop and narrow screens: navigation,
   source context, editing, draft reload, loading/empty/error/retry, and a user
   completing the scenario without the author's guidance.
8. Inspect English naming, readable module structure, accurate comments and
   docstrings, and unnecessary abstraction/dead code. Fix safe problems with
   regression coverage; avoid unrelated rewrites or contract drift.
9. Verify request-to-job-to-document/extraction/submission log correlation,
   levels, safe error codes, and redaction. Logs must not expose document text,
   financial values, prompts, provider responses, personal filenames, or keys.
   Confirm review revisions, confirmations, and receipts are persisted as audit
   data, not reconstructed from operational logs.
10. Scan tracked/release files for credentials without printing secret values.
    Confirm .env is excluded, examples are permitted, fixture mode is visible,
    content routes are protected, and README describes the actual startup path.

## Fixes and release evidence

Make safe in-scope fixes in a separate branch with regression tests. Coordinate
shared contract changes with member 5. Re-run relevant checks and final-review.
After fixes are merged, update the verdict against the new actual release SHA.
Do not automatically merge, deploy, publish, or submit the project.

Write docs/release/FINAL-REVIEW.md with:
- reviewed SHA and clean-start procedure;
- PASS / FAIL / NOT VERIFIED for each acceptance scenario;
- exact commands and actual results;
- findings, fixes, and remaining blockers;
- provider matrix: live-verified / fixture-only / unavailable;
- README, demo, evaluation, and integration-documentation readiness;
- READY or NOT READY verdict supported by the recorded evidence.

Return a concise verdict, major remaining risks, and the report path. Do not
claim the whole product is ready when the central workflow has not passed.
