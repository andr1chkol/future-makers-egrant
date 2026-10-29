# Report from member 2: extraction is done; how the team builds on it

Author: member 2 (Kolya). Date: 2026-10-29.
Branch `codex/extraction` from `bootstrap-v1` (`88d1b95`). The PR into `main`
is not merged; member 1 (Danya) reviews it with `docs/team/06-PEER-REVIEW.md`.

The technical handoff is `docs/handoffs/02-extraction.md`, with interfaces, codes,
commands and limits. This report is the short version for the whole team: what
exists now, what each member has to do with it, and where the joins are.

## 1. Current state

| Area | State |
|---|---|
| Extraction routes (`POST/GET /extractions`, `GET /extractions/{id}`, `POST /extractions/{id}/retries`) | Implemented in `app.extraction.routes.router`, **not mounted yet** (member 5) |
| `extraction.process` worker handler | Implemented as `app.extraction.service.process_extraction`, **not registered yet** (member 5) |
| Migration `0201_extractions` | Done, branches from `0001_platform` |
| AI provider, live mode | OpenAI Responses API with strict JSON Schema. **No live call made: no key** |
| AI provider, fixture mode | Replays a recorded reply for the shared synthetic invoice and fails explicitly for anything else |
| Evidence and validation | Numbers, dates, currencies, quotes, unit IDs, option keys, arithmetic |
| Tests | `tests/extraction`: 110 passed, 1 skipped (the live test) on PostgreSQL 16 |
| Shared test failure | `tests/platform/test_jobs.py::test_migration_and_transactional_enqueue`, see 3.1 |
| Evaluation | Synthetic tuning (2) and held-out (4) cases plus an evaluator; no model accuracy figure yet |

Nothing outside my owned paths was changed: no shared files, no lockfiles, no
contracts, no frontend. Pushing the branch does not affect `main` or anyone else's branch.

## 2. How data flows through extraction

```
documents (member 1)            profiles (member 3)
get_normalized(session, id)     get_profile(session, id, version), get_form(session, id)
          \                        /
           POST /extractions  →  one Extraction + one job per document (status queued)
                                   │  worker: extraction.process
                                   ▼
                     provider (live: OpenAI, fixture: recorded reply)
                                   ▼
             parse → normalize → check evidence → domain rules → ready | failed
                                   ▼
             GET /extractions/{id} → review (member 4) → confirmed → export (member 5)
```

Extraction calls the other modules only through their public functions and
imports them at call time. Nothing breaks while their code is not merged; until
then my tests use stand-ins.

## 3. What each member needs to do

### 3.1 Member 5 (integration)

Wiring only; no logic of mine needs changing.

1. **Router.** Remove the four `/extractions` shells from `app/platform/routes.py`
   and include `app.extraction.routes.router` in `create_app` with
   `Depends(require_access)`, the same way as the shells. Under FastAPI 0.162 the
   included router is one `_IncludedRouter`, so shell routes cannot be filtered
   out afterwards; they have to be removed from the source.
2. **Worker.** In `app/worker.py`:
   ```python
   from app.extraction.service import process_extraction
   registry.register_handler("extraction.process", process_extraction)
   ```
   The handler raises `ExtractionRetryScheduled` for transient failures, so that
   your backoff applies, and handles every other outcome itself.
3. **Migrations.** Heads after the module merges: `010*` (documents),
   `0201_extractions`, `030*`, `040*`. A merge revision is needed. Fix
   `test_migration_and_transactional_enqueue` at the same time: it asserts that
   head is `0001_platform`, which is false as soon as any module migration exists.
4. **Capabilities.** `aiConfigured` can become
   `OpenAIProvider.from_settings(get_settings()) is not None`
   (`app.extraction.providers`). Mark it as unverified until the first live call.
5. **Leases.** The provider call is capped at 40 seconds inside your 60-second
   lease, so v1 does not need lease renewal for extraction. One gap is yours to
   decide: if the worker crashes during attempt 3, the job becomes
   `LEASE_EXHAUSTED` without calling the handler and the extraction stays `running`.
   A failure hook or a periodic sweep would close it.
6. **Logging.** Retries log `job.retry_scheduled` with `extractionId` and the
   provider code. Add `extraction.retry_scheduled` to `EVENTS` if you want a separate event.

### 3.2 Member 1 (documents, and reviewer of my PR)

What extraction expects from `get_normalized(session, document_id)`:

- Raise `NotFoundError` for an unknown document and `ConflictError` while it is
  not `ready`. Extraction answers 404/409 at creation time and does not queue
  documents that are not ready. The UI should create extractions only after the
  document is ready.
- **Unit IDs must be stable**: the same document always yields the same IDs.
  Extraction stores them in `SourceRef.unitId`, and the review screen opens
  evidence by them.
- `page` starts at 1 for PDFs and images. For XLSX/CSV, set `sheet`/`cell` with
  `page = null`. Extraction copies these values into `SourceRef` and never invents them.
- Keep `text` close to the printed text: do not reformat numbers or dates. Quotes
  are checked as substrings (whitespace and line breaks are ignored).
- **Fixture demo:** the CSV `contracts/examples/synthetic-invoice.csv` must
  normalize to exactly the units in `contracts/examples/normalized-document.json`
  (`row-1` … `row-4` with the same texts). Otherwise fixture mode fails with
  `FIXTURE_NOT_AVAILABLE`, which is correct behavior but blocks the demo.

How to review my PR:

```sh
git fetch origin && git switch codex/extraction
uv sync --locked
docker run --name egrant-extraction-test -e POSTGRES_USER=egrant -e POSTGRES_DB=egrant_test \
  -e POSTGRES_PASSWORD=local-test-only -p 127.0.0.1:55432:5432 -d postgres:16
export TEST_DATABASE_URL=postgresql+psycopg://egrant:local-test-only@localhost:55432/egrant_test
uv run pytest tests/extraction
cd backend && uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/heldout
```

Expected: 110 passed, 1 skipped. Full `uv run pytest`: 1 known failure (3.1, item 3).
Areas that deserve a close look: `service.process_extraction` (phases, run token,
retries), `validation/values.py` (number and date parsing), and `validation/rules.py`
(tolerances).

### 3.3 Member 3 (profiles)

- Extraction calls `get_profile(session, id, version)` with an explicit version
  and checks that the returned `version` matches. Raise `NotFoundError` for an
  unknown version. Extraction stores a snapshot of the profile, so new versions do
  not affect existing runs.
- `get_form(session, form_id)` is used only to read **option keys**: for `string`
  fields, by `targetTag`, scalar or table column. The model is told to answer only
  with these keys, and any other value is rejected (`OPTION_NOT_PERMITTED`).
- **Field descriptions go to the model.** `description` in `ProfileField` is the
  main hint to the AI. Write it precisely, e.g. "Name of the supplier (seller,
  Dodávateľ) without address", not just "Dodávateľ". Good examples are in
  `tests/extraction/evaluation/profiles/*.json`.
- **Arithmetic checks rely on key names.** The constructor's default keys should
  follow these names so that the checks work:
  `quantity`, `unit_price`, `line_total` (row); `net_total`, `vat_total`, `total`
  (document); `opening_balance`, `closing_balance` and the `amount` column (bank
  statement). Other keys work too, but the checks are skipped for them.

### 3.4 Member 4 (review)

What the review screen receives in `Extraction` (`status = ready`):

- Each field and cell has `value`, `status` and `sources[]`.
  - `missing`: `value = null`. **Sources may still be present**: something was
    printed but could not be read (ambiguous date or number). Show the link to the
    source anyway.
  - `needs_review`: a value exists but a check failed; a warning explains which.
  - `found`: value and evidence verified.
- `rowId` is persistent across reads. Human-added rows get their own UUIDs (your module).
- Warnings carry `fieldKey`/`tableKey`/`rowId`, so they can be shown next to
  the field or row. Acknowledgement uses `warning_identity` from `contracts.py`.
- Retry is available only for `failed` extractions (`POST /extractions/{id}/retries`);
  for any other status it returns 409.
- `error.code` on a failed run is a stable code (`AI_TIMEOUT`, `FIXTURE_NOT_AVAILABLE`, ...).
  Map it to Slovak copy, not `message`.

Proposed Slovak copy for the warning codes. This is a proposal; the final UI
wording is yours.

| Code | Proposed UI text |
|---|---|
| `REQUIRED_VALUE_MISSING` | Povinný údaj sa v dokumente nenašiel |
| `MISSING_OPTIONAL_VALUE` | Nepovinný údaj sa v dokumente nenašiel |
| `VALUE_UNREADABLE` | Hodnotu sa nepodarilo prečítať |
| `NUMBER_AMBIGUOUS` | Číslo možno čítať viacerými spôsobmi – zadajte ho ručne |
| `DATE_AMBIGUOUS` | Dátum možno čítať viacerými spôsobmi – zadajte ho ručne |
| `OPTION_NOT_PERMITTED` | Navrhnutá hodnota nie je medzi povolenými možnosťami |
| `CURRENCY_MISSING` | Pri sume chýba mena |
| `CURRENCY_INVALID` | Neplatný kód meny |
| `CURRENCY_NOT_IN_DOCUMENT` | Mena sa v dokumente nespomína |
| `CURRENCY_INCONSISTENT` | Sumy v dokumente sú v rôznych menách |
| `SOURCE_UNIT_UNKNOWN` | Odkaz na zdroj neexistuje |
| `QUOTE_NOT_IN_SOURCE` | Citát sa v zdroji nenachádza |
| `EVIDENCE_MISSING` | Hodnota nemá oporu v dokumente |
| `VALUE_NOT_IN_EVIDENCE` | Hodnota sa v citovanom zdroji nenachádza |
| `EMPTY_ROW_DROPPED` | Prázdny riadok tabuľky bol vynechaný |
| `DUPLICATE_ROW` | Riadok sa opakuje s rovnakým zdrojom – skontrolujte, či nejde o duplicitu |
| `LINE_TOTAL_MISMATCH` | Suma riadku nezodpovedá množstvu × cene |
| `DOCUMENT_TOTAL_MISMATCH` | Súčet riadkov nezodpovedá celkovej sume |
| `TAX_TOTAL_MISMATCH` | Základ + DPH nezodpovedá celkovej sume |
| `BALANCE_MISMATCH` | Počiatočný zostatok + pohyby nezodpovedá konečnému zostatku |

## 4. Running the module without the rest of the app

- Unit and behavior tests need no other modules; they replace documents and
  profiles with stand-ins.
- The evaluator runs the whole parse-and-validate pipeline on prepared cases:
  `cd backend && uv run python -m app.extraction.evaluation ../tests/extraction/evaluation/tuning`.
- A live run needs `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env` (never in Git),
  `APP_MODE=live`, and an explicit start:
  `EXTRACTION_LIVE_TEST=1 uv run pytest tests/extraction/test_live_provider.py`, or the
  evaluator with `--live`. Both are paid calls; run them only with the team's permitted key.

## 5. Order of assembly

1. Member 5 mounts the extraction router and registers the handler on
   `codex/integration`, and fixes the migration test. This needs only my branch.
2. When documents (member 1) arrive: check that the shared CSV produces
   `row-1` … `row-4`, then run upload → extraction in fixture mode end to end.
3. When profiles (member 3) arrive: create the example profile through the API and
   start an extraction with its `id`/`version`.
4. When review (member 4) arrives: open `/review/:extractionId` on a ready
   extraction and check source navigation and warnings.
5. With a key: one live run on a synthetic document, then the held-out evaluation
   with `--live`, so that the team has a real accuracy figure.

## 6. Open questions for the team

- Which OpenAI model and key are permitted, and the budget. Nothing has been sent without them.
- Whether real eGrant form JSON exists. Option keys and descriptions depend on it.
- Who owns the gap where an extraction stays `running` after a crash on the last
  attempt (member 5, see 3.1, item 5).
- Whether `role` should be added to `ProfileField` in contract v2, so that
  arithmetic does not depend on key names (members 3 and 5).
