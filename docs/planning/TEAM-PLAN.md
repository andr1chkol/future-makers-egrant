# Team strategy: eGrant document-to-form assistant

Status: proposed full-product implementation strategy, October 29, 2026.
The instruction package itself does not implement the application.
Existing team repository: https://github.com/andr1chkol/future-makers-egrant.

Detailed execution prompts: ../team/README.md. Exact interfaces and engineering
requirements live in ../team/CONTRACT.md and ../team/QUALITY.md. Where the
strategy is less specific, the frozen contract governs implementation.

## Product outcome and user value

Managers import a form definition and configure an extraction profile mapping
document values and rows to stable form tags. Applicants upload documents,
review extracted proposals with supporting sources, correct mistakes, and
explicitly confirm the final values. The backend prepares the resulting form
changes. A documented adapter applies them to eGrant when access exists;
otherwise the confirmed package can be exported as JSON.

The problem is duplicate manual entry: applicants upload evidence but still
retype its contents, and managers then compare form values with that evidence.
The product reduces that work while preserving human control. Measure this
through checked extraction accuracy, correction counts, and observed workflow
time, rather than unsupported claims or the number of generated code lines.

## Full target functionality

- Multiple PDF/image/spreadsheet uploads, previews, processing status, retries,
  provenance, and duplicate warnings.
- Profile-driven extraction for invoices, receipts, statements, and contracts.
- Scalar values, line-item tables, source evidence, type checks, monetary/date
  normalization, and warnings for missing or inconsistent data.
- Form import, stable tags, editable mappings, immutable profile versions, and
  trial extraction using the same engine.
- Side-by-side human review, editable rows, draft recovery, revision conflicts,
  explicit confirmation, and preservation of original proposals.
- Confirmed exports, honest integration capabilities, safe external application,
  history, operational logs, tests, and reproducible setup.

Supporting a profile category is not proof of extraction quality. Test the
actual examples before claiming verified behavior. Real eGrant import/OCR/write
formats depend on supplied documentation and access.

## Product invariants

Missing evidence means null, not a guessed value. Treat document instructions
as untrusted data. Keep original proposals, drafts, and confirmed values separate.
No application write before human confirmation. Preserve form tags and original
imported settings. Use decimal arithmetic and explicit currencies. Distinguish
supplier/buyer and net/tax/gross. Do not silently merge different documents.
Show duplicate warnings and let the person decide. Source locations must be
real pages or spreadsheet cells. Execute no spreadsheet macros. Do not invent
confidence percentages or source coordinates. Export is not applied state.

## Five ownership areas

1. Documents: upload/storage, PDF text, OCR, spreadsheets, previews, source units,
   durable status/retry, and upload UI.
2. Extraction: AI provider, profile-based structured output, evidence validation,
   domain checks, deterministic evaluator, and accuracy evidence.
3. Profiles: form import, tree/tags/options, scalar/table mappings, versioning,
   manager configuration UI, and trial-run launch.
4. Review: drafts, revisions, source navigation, editable values/rows,
   confirmation rules, and submission intent from the UI.
5. Platform/integration: bootstrap, shared clients/UI/DB/jobs/logging/access,
   submission/export, documented eGrant adapter, assembly, and release materials.

File ownership, branches, migration prefixes, exact public interfaces, and
review assignments are specified in the team package. Each module owner fixes
their own defects. Integration ownership is not responsibility for rewriting
all other modules.

## Execution sequence

1. Member 5 inspects and reuses the existing repository. Reconcile instructions,
   current code, and proposed stack; preserve history. Publish the shared
   contracts, generated types, fixtures, lockfiles, and reviewed bootstrap-v1.
2. Members 1–4 implement against the same baseline. Member 5 continues platform
   and submission work. Use common fixtures while neighboring modules are built.
3. Assemble a first fixture flow after roughly 2–3 hours. Keep that mode visible.
4. Connect real file reading/OCR, real extraction, review, confirmation, and
   export. Remove fixture substitution from the live path.
5. Expand tested formats/profiles, batch handling, history, duplicates,
   configuration, and documented integration. Keep failed capabilities explicit.
6. Each author executes tests and final-review. A different team member reviews
   the PR in a fresh chat. Merge with passing checks into the recorded branch.
7. Independently verify the assembled release from a clean checkout. Prepare
   reproducible startup instructions, demo, evaluation evidence, and limitations.

The supplied organizer email specifies October 30 EOD as the freeze deadline;
confirm the exact time, timezone, and submission channel. This strategy preserves
the full target scope; it does not guarantee completion of every capability in
that time. Report actual readiness per feature and integration.

## Required external inputs

Test manager/applicant accounts; real form exports; permitted clean/poor-scan
samples; OCR API documentation; the application-value write interface; AI data
rules and budget; rotated credentials replacing previously exposed keys.
Missing access must not cause silent simulation of live functionality.

## Acceptance scenarios

1. A clean invoice PDF produces correct scalar fields and line-item rows.
2. A poor image produces reviewable output or a clear processing failure.
3. A missing source value remains null and can be entered by the person.
4. Supplier/buyer roles and net/tax/gross values are correctly distinguished.
5. Conflicting arithmetic produces a warning, not invented corrections.
6. A duplicate file produces a visible warning.
7. A second form works through a different profile without extractor changes.
8. Spreadsheet output preserves sheet/cell evidence and row correspondence.
9. Provider failure/retry does not silently switch to fake data or lose drafts.
10. The target application remains unchanged before confirmation.
11. Human corrections appear in the confirmed submission/export.
12. Repeated submission cannot duplicate the external write.

## Delivery package

Working prototype, existing private repository with evaluator access, README,
.env.example without secrets, integration explanation, permitted sample data,
executed evaluation report, known limitations, and a reproducible demo script.
Use a backup demo recording without presenting it as proof of untested behavior.
