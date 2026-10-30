# Final assembly fixture demo

This is a failing acceptance procedure on the current continuation, not a product
PASS. Member 3 owns `codex/final-assembly`. Do not merge unreviewed modules merely
to make the demonstration continue.

## Prerequisites

Follow the README's locked install and install Chromium. Use PostgreSQL 16 with
two disposable databases: `egrant_test_full_product` and
`egrant_test_full_product_e2e`. Supply their URLs through `TEST_DATABASE_URL` and
`FULL_PRODUCT_E2E_DATABASE_URL`. Keep credentials in the environment, outside Git.
Ports 8017 and 5179 must be free for the browser launcher. The backend acceptance
test launches a real worker; the browser launcher starts its own API and worker.

```sh
scripts/final-assembly-demo.sh
# To inspect the browser failure separately:
make e2e-full-product
```

The script exits nonzero on a failure. It does not start a fake neighboring
service, rewrite the source CSV, substitute source IDs or enable an eGrant write.
The backend database fixture resets its guarded test database. The browser
launcher refuses any database other than `egrant_test_full_product_e2e`.

## Intended observable sequence

1. Import the illustrative shared form and preserve its complete `originalJson`.
   Configure scalar and table mappings, then save immutable profile version 1.
2. Upload the unchanged `contracts/examples/synthetic-invoice.csv`. A second
   upload has a different document ID, the same hash and `duplicateOf` pointing
   to the first. The worker produces 23 authentic cell units per document.
3. Launch the saved profile version. Every returned source must reference the
   uploaded document, an existing unit, exact quote and matching coordinates.
4. Inspect source context, correct scalar values and both table rows, save the
   draft and reload it. Missing required values must block confirmation; a stale
   revision must return 409. A later manager edit must leave version 1 intact.
5. Explicitly confirm, export JSON and compare every mapped corrected scalar
   and row. Repeat confirmation and submission using current revision and the
   same idempotency key without creating another operation.
6. Repeat the backend scenario with another form and distinct destination tags.

Current observed stopping point: step 3 returns `503 FEATURE_UNAVAILABLE` from
the real extraction shell. Steps 4–6 are prepared assertions, not verified
assembled behavior. Provider failure/retry/recovery, live AI/OCR and the broader
release input set still need execution after the module review gates pass.

## Gates before a successful demo

Member 4 must publish corrections for human-review UTC serialization and invalid
currency acceptance, followed by member 3's exact-head recheck. Member 2 must
publish the actual-source extraction fixture correction and resolve the reported
option/recovery/provider-lifetime findings; member 1 then reviews that exact head.
Only then can member 3 assemble their routers, worker recovery, metadata and new
migration merge revision. The new assembly needs member 4's independent review
and member 1's release verification. See `FINAL-ASSEMBLY-STATUS.md`.
