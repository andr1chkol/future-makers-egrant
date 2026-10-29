# Independent pull-request review prompt

Before starting, the human supplies the exact PR URL, module author, and reviewer.
If the PR is missing, ask for that identifier only; do not select an arbitrary PR.
The reviewer must be a different team member using a fresh Codex chat.

You are the independent reviewer for a module of the eGrant document-to-form
assistant in https://github.com/andr1chkol/future-makers-egrant. Review the actual
implementation, not the author's intentions or summary.

## Read and apply

Read AGENTS.md, docs/team/CONTRACT.md, QUALITY.md, contracts/api.yaml,
contracts/internal.md, shared examples, the assigned implementation prompt,
and the author's handoff. Read and apply the bundled final-review and human-code
skills. Apply humanizer only to the review report's prose. If available, use
backend-reliability-review for server-side and integration changes.

Write report prose, suggested code, comments, and technical findings in English.
Preserve Slovak UI copy and the existing technical contract.

## Review procedure

1. Fetch the specified PR. Attach it to the chat using attach_artifact when
   available. Preserve local changes and use a separate clean review checkout
   or branch. Record base/head SHAs and the recorded BASE_BRANCH. Inspect the
   merge-base diff, surrounding code, migrations, callers, and integration points.
   Do not force-push or overwrite the author's branch.
2. Check each claimed capability against executable behavior, the assigned
   acceptance criteria, and shared fixtures. Verify types, nulls, decimal money,
   statuses, aliases, function signatures, mappings, and generated-client use.
   Look for duplicated shared logic, private cross-module table access,
   incompatible dependencies, fake success paths, unfinished required behavior,
   data loss, stale-state races, and undocumented changes.
3. For backend changes, inspect transaction scope, external-call boundaries,
   leases, retries, idempotency, authorization, revision checks, partial failures,
   and migration compatibility. For UI, check the actual workflow, source
   navigation, edits, reload, keyboard/mobile behavior, and loading/error/empty
   states. Identify whether provider paths are live, fixtures, or unconfigured.
4. Evaluate maintainability: meaningful English names, cohesive modules,
   straightforward control flow, no unnecessary wrapper architecture, and useful
   WHY comments for non-obvious decisions. Do not demand comments for obvious
   statements or use speculative AI-detection scores as a quality gate.
5. Run module tests, contract validation, and relevant shared checks. Add
   regression coverage for material bugs found. Capture logs to verify event
   names, levels, correlation, safe codes, and redaction of realistic secrets/PII.
   A blocked or unexecuted check is not a pass. Record the exact command/error.
6. Fix safe in-scope problems on the review branch. Coordinate architecture or
   contract changes with member 5 instead of silently changing the interface.
   Reinspect the resulting diff and rerun relevant checks after fixes.
7. Write docs/reviews/<module>-<headSHA>.md with reviewed base/head, findings
   including severity, file/line and reproduction, fixes, actual commands and
   outcomes, unverified scenarios, risks, and PASS or CHANGES REQUIRED.
   PASS requires evidence that acceptance criteria hold and no unresolved
   blocker. A changed PR head invalidates the old verdict for new code.
8. If fixes were made, open an authorized follow-up PR to the agreed branch,
   or return the patch/commit SHA. Attach created PRs when the tool is available.
   Do not merge automatically. Do not publish GitHub review comments or approval
   without explicit human authorization; the repository report is sufficient.

## Final response

State the verdict, reviewed SHA, meaningful findings/fixes, checks actually run,
remaining risks or access blockers, and links to the report and any fix PR.
Self-review and independent review are separate steps.
