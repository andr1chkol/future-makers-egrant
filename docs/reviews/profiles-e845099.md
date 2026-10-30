# Independent review recheck: profiles (member 3) at e845099

Reviewer: member 2. Author: member 3. Guide: `docs/team/06-PEER-REVIEW.md`.
Previous report: `docs/reviews/profiles-7fe7659.md` (CHANGES REQUIRED for `7fe7659`).

- Reviewed head: `origin/codex/profiles` at `e845099` (two commits after `7fe7659`)
- Base: `main` / `bootstrap-v1` at `88d1b959c524cfd559d01ee8ff6ac3f183f7c9e8`

## Verdict

**PASS** for `e845099`. A later commit invalidates this verdict for the new code.

## What changed since 7fe7659

- `44cc3b8` cherry-picks the reviewer fix `fc49db8`; its content is identical
  (`git diff fc49db8 44cc3b8` is empty). Integration screenshots now go to
  `testInfo.outputPath(...)`. Finding 1 of the previous report is resolved.
- `e845099` updates `docs/handoffs/03-profiles.md` only. It records the fix, the
  author's fresh macOS checks and the open low-severity findings. Its statements
  match the code.

No runtime code changed between `7fe7659` and `e845099`, so the rest of the
previous review still applies.

## Remaining findings (non-blocking)

- Low: `list_profiles` orders by random profile UUID rather than by name.
- Low: imported option keys keep surrounding whitespace (`" rail "`).
- Owner member 5: profile/form IDs and version are dropped from JSON logs until
  `ID_KEYS`/`NUMBER_KEYS` are extended.
- Owner member 2: extraction's arithmetic checks rely on conventional keys, which
  profiles derive from form tags.

The author acknowledges the two low findings in the handoff.

## Verification

Linux (Fedora 44), Python 3.12.16, Node 22, PostgreSQL 16 under podman, clean
checkout of `e845099`,
`TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test`.

| Command | Result |
|---|---|
| `make check` | exit 0 |
| `uv run pytest` | 82 passed |
| `cd frontend && npm test` | 26 passed |
| `npm run e2e` | 3 passed |
| `npx playwright test -c src/features/profiles/playwright.config.ts` | 2 passed |
| `npx playwright test -c src/features/profiles/playwright.integration.config.ts` | 1 passed |

Still not verified: a real eGrant form export, a trial run with real documents and
a live AI provider, and the assembled document-to-export flow.
