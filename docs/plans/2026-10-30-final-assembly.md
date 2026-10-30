# Final assembly continuation plan

Active integration owner: member 3, transferred by the user and member 5's
handover. Branch: codex/final-assembly. Initial parent:
6d3843d43f00424601bd94dd0bba263bd9f6a728 from draft PR 11; its verified code
ancestor is a5b283f129cf9caed7097d75d71ed0fbd365618a. Existing document,
profile, export, recovery, parser and storage work stays intact. PR 4 is already
an ancestor and must not be reapplied. No reset, force push or tag movement.

## Ownership and review gates

- Available local worktrees were clean with no intended unpublished commits.
  Member 5's handover explains the historical tree-equivalent local commits.
  Ownership receipt and the active continuation branch were published on PR 11.
- PR 3 at 133e6ced9cbce21fb255fa77b45d3d335c47ec75 was reviewed independently
  in a fresh isolated context. Its report is on review/human-review-133e6ce.
  Verdict: CHANGES REQUIRED. Member 4 must resolve UTC response consistency and
  human currency validation. The safe timestamp correction is separately
  published as 35b04707861657a9b79c92f758291bcd6a03c600, not silently merged.
- PR 6 at f21eb8434a63dd65a9d509c76de9031fad67faaa still needs member 1's
  independent review and member 2's actual normalized-source fixture correction.
  Options, recovery fairness and provider-request lifetime findings were sent
  to the owner. Do not substitute earlier self-audits or green CI for a verdict.
- Re-fetch and record the actual corrected heads before assembly. Root's later
  assembly is author work; member 4 reviews it separately. Member 1 performs
  release verification with separate independent coverage of their document code.

## Implementation sequence

1. Verify the inherited candidate in a fresh worktree with locked installs,
   make check, PostgreSQL backend tests and applicable frontend/browser suites.
   Use dedicated egrant_test databases, never the demo database.
2. Prepare acceptance tests under tests/e2e and frontend/tests without replacing
   neighboring services. Actual files must pass through production upload,
   normalization, registered worker handlers, extraction, review and export.
   The incomplete candidate should expose missing modules, not fake success.
3. After review gates pass, merge the reviewed owner histories normally. Resolve
   shared conflicts using the existing assembled behavior and union of migration
   assertions. Do not replace the documents directory with PR 9 wholesale.
4. In backend/app/main.py and backend/app/platform/routes.py, replace extraction
   and review shells with real access-protected routers. Register models in
   backend/migrations/env.py and migration locations in backend/alembic.ini and
   the owned auxiliary configs. Add a new 0504_final_assembly merge revision
   joining 0503_documents_assembly, 0201_extractions and 0401_reviews. Published
   migrations remain immutable; prove one head and a clean database upgrade.
5. In backend/app/worker.py, register extraction.process and invoke public
   recover_terminal_extractions with its own fresh session alongside existing
   document/submission recovery. Derive capabilities from configured adapters.
   Preserve access, queue fencing, private storage and failed-provider behavior.
6. Wire existing owner browser suites and the complete product suite into shared
   Makefile/CI. Keep OpenAPI, examples and generated client checks compatible.
7. Execute exact corrected scalar/table export, second mapping/profile, nulls,
   duplicates, stale revisions, provider failure/retry, recovery and repeated
   submission scenarios. Fixture mode remains visibly labeled and deterministic.
8. Update README, INTEGRATION-HANDOFF, provider matrix, limitations and a clean
   reproducible demo script. Record actual commands/results and reviewed SHAs.
9. Apply final-review, fix safe shared findings with regressions, rerun affected
   checks, publish one draft final-assembly PR identifying incorporated PRs, and
   request member 4's exact-head integration review and member 1's release pass.

## Verification boundaries

No process AI/OCR configuration is present on this host. Docker CLI exists but
its daemon is unavailable, and no host Tesseract executable was found. These
facts block live/container checks, not fixture implementation or isolated
PostgreSQL verification. The user was asked for an existing local configuration
path and agreed model without sending secret values. No .env or secret value
is copied into Git. No external eGrant application write is authorized.

No acceptance PASS, owner review PASS or final release readiness is asserted by
this plan. Record each completed check against its actual source head.
