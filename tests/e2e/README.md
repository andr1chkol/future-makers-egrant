# Browser tests

Browser tests live in `frontend/tests/e2e` so Node resolves the same locked
Playwright dependency as the frontend. Run them from the repository root with
`make e2e`. Full domain workflow coverage is pending module integration.

`make e2e-integration` runs the submission HTTP API against a separate PostgreSQL
database named with the `egrant_test_e2e` prefix. Set
`INTEGRATION_E2E_DATABASE_URL` before running it. The test server resets that
database and migrates it; never supply a database with data you need. It starts
API/frontend on 8013/5176. Neighboring public reads use explicit reference-example
test doubles. Browser tests verify the real persisted operation, exact corrected
JSON download, repeat/conflicting requests, responsive status page and error
recovery. History UI responses are mocked explicitly while extraction is absent.
These tests do not claim the assembled document-to-confirmation workflow.
