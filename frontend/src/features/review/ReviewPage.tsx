import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../../shared/api";
import { Button, Notice } from "../../shared/ui";
import { SourcePanel } from "./SourcePanel";
import { SubmissionActions } from "./SubmissionActions";
import { ReviewFields } from "./ReviewFields";
import {
  dataOf,
  displayValue,
  errorText,
  snapshotOf,
  warningIdentity,
  type Review,
  type Snapshot,
  type Source,
} from "./model";
import "./review.css";

// Keep unsaved edits in tab memory across SPA back/forward navigation, never browser storage.
const recoverableDrafts = new Map<string, { saved: Review; draft: Snapshot }>();

async function loadReview(extractionId: string) {
  const extraction = dataOf(
    await api.GET("/api/v1/extractions/{id}", {
      params: { path: { id: extractionId } },
    }),
  );
  const [profileResult, reviewResult] = await Promise.all([
    api.GET("/api/v1/profiles/{id}", {
      params: {
        path: { id: extraction.profileId },
        query: { version: extraction.profileVersion },
      },
    }),
    api.GET("/api/v1/reviews/{extraction_id}", {
      params: { path: { extraction_id: extractionId } },
    }),
  ]);
  const profile = dataOf(profileResult);
  const review = dataOf(reviewResult);
  const form = dataOf(
    await api.GET("/api/v1/forms/{id}", {
      params: { path: { id: profile.formId } },
    }),
  );
  const warningEntries = await Promise.all(
    extraction.warnings.map(async (warning) => ({
      warning,
      id: await warningIdentity(warning),
    })),
  );
  const warnings = [
    ...new Map(warningEntries.map((entry) => [entry.id, entry])).values(),
  ];
  return { extraction, profile, review, form, warnings };
}

export function ReviewPage() {
  const { extractionId } = useParams();
  if (
    !extractionId ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      extractionId,
    )
  )
    return (
      <section className="review-page">
        <h1>Skontrolovať údaje</h1>
        <Notice>Identifikátor spracovania nie je platný.</Notice>
      </section>
    );
  return <ReviewWorkspace key={extractionId} extractionId={extractionId} />;
}

function ReviewWorkspace({ extractionId }: { extractionId: string }) {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["review", extractionId],
    retry: false,
    queryFn: () => loadReview(extractionId),
  });
  const [saved, setSaved] = useState<Review | null>(
    () => recoverableDrafts.get(extractionId)?.saved ?? null,
  );
  const [draft, setDraft] = useState<Snapshot | null>(
    () => recoverableDrafts.get(extractionId)?.draft ?? null,
  );
  const [source, setSource] = useState<Source | null>(null);
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const dirty =
    !!saved &&
    !!draft &&
    JSON.stringify(snapshotOf(saved)) !== JSON.stringify(draft);
  useEffect(() => {
    if (saved && draft && dirty)
      recoverableDrafts.set(extractionId, { saved, draft });
    else recoverableDrafts.delete(extractionId);
  }, [extractionId, saved, draft, dirty]);
  useEffect(() => {
    // Refetch can discover newer server data, but must never overwrite local edits.
    if (!saved && query.data && !query.isFetching && !query.isError) {
      setSaved(query.data.review);
      setDraft(snapshotOf(query.data.review));
    }
  }, [query.data, query.isFetching, query.isError, saved]);
  useEffect(() => {
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const navigate = (event: MouseEvent) => {
      const anchor = (event.target as Element).closest?.("a");
      if (
        anchor &&
        anchor.target !== "_blank" &&
        !anchor.hasAttribute("download") &&
        !anchor.getAttribute("href")?.startsWith("#") &&
        !window.confirm(
          "Máte neuložené úpravy. Chcete opustiť stránku? Koncept ešte nie je uložený na serveri.",
        )
      ) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", navigate, true);
    return () => {
      window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", navigate, true);
    };
  }, [dirty]);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!saved || !draft || busy) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const result = dataOf(
        await api.PUT("/api/v1/reviews/{extraction_id}", {
          params: { path: { extraction_id: extractionId } },
          body: { expectedRevision: saved.revision, ...draft },
        }),
      );
      setSaved(result);
      setDraft(snapshotOf(result));
      cache.setQueryData(["review", extractionId], {
        ...query.data,
        review: result,
      });
      setSummary(false);
      setNotice("Koncept bol uložený.");
    } catch (failure) {
      setError(errorText(failure));
      await query.refetch();
    } finally {
      setBusy(false);
    }
  }
  async function confirm() {
    if (!saved || dirty || busy || saved.status !== "draft") return;
    setBusy(true);
    setError(null);
    try {
      const result = dataOf(
        await api.POST("/api/v1/reviews/{extraction_id}/confirm", {
          params: { path: { extraction_id: extractionId } },
          body: { expectedRevision: saved.revision },
        }),
      );
      setSaved(result);
      setDraft(snapshotOf(result));
      cache.setQueryData(["review", extractionId], {
        ...query.data,
        review: result,
      });
      setSummary(false);
      setNotice("Údaje boli výslovne potvrdené.");
    } catch (failure) {
      setError(errorText(failure));
      await query.refetch();
    } finally {
      setBusy(false);
    }
  }
  async function reload() {
    if (
      dirty &&
      !window.confirm(
        "Načítaním uloženého konceptu zahodíte neuložené úpravy. Pokračovať?",
      )
    )
      return;
    setBusy(true);
    const result = await query.refetch();
    if (result.data && !result.error) {
      setSaved(result.data.review);
      setDraft(snapshotOf(result.data.review));
      setSummary(false);
      setError(null);
    } else setError(errorText(result.error));
    setBusy(false);
  }
  if (query.isPending || (!saved && query.isFetching))
    return (
      <section className="review-page">
        <h1>Skontrolovať údaje</h1>
        <Notice>Načítavame uložený koncept…</Notice>
      </section>
    );
  if (!query.data || !saved || !draft)
    return (
      <section className="review-page">
        <h1>Skontrolovať údaje</h1>
        <p role="alert">{errorText(query.error)}</p>
        <Button onClick={() => void query.refetch()}>Skúsiť znova</Button>
      </section>
    );
  const { extraction, profile, form, warnings } = query.data;
  const confirmed = saved.status === "confirmed";
  const latest = query.data.review;
  return (
    <section className="review-page">
      <header className="review-heading">
        <p className="eyebrow">
          Ľudská kontrola ·{" "}
          {extraction.mode === "fixture"
            ? "Ukážkové údaje"
            : "Živé spracovanie"}
        </p>
        <h1>Skontrolovať údaje</h1>
        <p>
          {profile.name} · verzia profilu {profile.version} · revízia{" "}
          {saved.revision}
        </p>
        {form.isIllustrative && (
          <Notice>
            Formulár je ilustračný; nejde o overený import eGrantu.
          </Notice>
        )}
        <p>AI návrh zostáva zachovaný. Vaše opravy sa ukladajú oddelene.</p>
      </header>
      {error && (
        <p className="review-error" role="alert">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {latest.revision > saved.revision && (
        <section className="review-conflict" aria-label="Novšia uložená verzia">
          <h2>Na serveri je novšia revízia {latest.revision}</h2>
          <p>
            Vaše úpravy zostávajú v editore. Pred načítaním novej verzie si ich
            porovnajte alebo skopírujte.
          </p>
          <details>
            <summary>Zobraziť údaje uloženej verzie</summary>
            <SnapshotSummary snapshot={latest} profile={profile} />
          </details>
        </section>
      )}
      <div className="review-toolbar">
        <label className="review-check">
          <input
            type="checkbox"
            checked={issuesOnly}
            onChange={(event) => setIssuesOnly(event.target.checked)}
          />
          Iba položky vyžadujúce pozornosť
        </label>
        <Button
          className="button review-secondary"
          disabled={busy}
          onClick={() => void reload()}
        >
          Načítať uloženú verziu
        </Button>
      </div>
      {confirmed && (
        <Notice>
          Táto revízia je potvrdená a nemenná. Pre ďalšie úpravy spustite nové
          spracovanie dokumentu.
        </Notice>
      )}
      <div className="review-layout">
        <SourcePanel documentId={extraction.documentId} selected={source} />
        <div className="review-editor">
          <form onSubmit={(event) => void save(event)}>
            <fieldset disabled={busy}>
              <legend>Hodnoty a položky</legend>
              <ReviewFields
                extraction={extraction}
                profile={profile}
                form={form}
                draft={draft}
                setDraft={setDraft}
                warnings={warnings}
                issuesOnly={issuesOnly}
                onSource={setSource}
                readOnly={confirmed}
              />
              <p>
                * Povinné hodnoty sa kontrolujú pri potvrdení. Neúplný koncept
                možno uložiť.
              </p>
              <Button type="submit" disabled={!dirty || confirmed}>
                {busy ? "Ukladáme…" : "Uložiť koncept"}
              </Button>
            </fieldset>
          </form>
          {!confirmed && (
            <section className="review-confirm">
              <h2>Potvrdenie</h2>
              <p>
                {dirty
                  ? "Máte neuložené úpravy. Pred potvrdením uložte koncept."
                  : "Potvrdí sa presne uložená revízia."}
              </p>
              <Button disabled={dirty || busy} onClick={() => setSummary(true)}>
                Skontrolovať súhrn
              </Button>
              {summary && (
                <section aria-label="Záverečný súhrn">
                  <h3>Potvrdiť revíziu {saved.revision}?</h3>
                  <p>
                    Potvrdené upozornenia: {draft.acknowledgedWarnings.length}/
                    {warnings.length}.
                  </p>
                  <SnapshotSummary snapshot={draft} profile={profile} />
                  <p>
                    Potvrdené údaje už nebude možné meniť. Toto potvrdenie samo
                    nezapisuje do eGrantu.
                  </p>
                  <Button
                    disabled={busy || dirty}
                    onClick={() => void confirm()}
                  >
                    Potvrdiť údaje
                  </Button>
                  <Button
                    className="button review-secondary"
                    onClick={() => setSummary(false)}
                  >
                    Späť k úpravám
                  </Button>
                </section>
              )}
            </section>
          )}
          {confirmed && <SubmissionActions review={saved} profile={profile} />}
        </div>
      </div>
    </section>
  );
}

function SnapshotSummary({
  snapshot,
  profile,
}: {
  snapshot: Snapshot;
  profile: Awaited<ReturnType<typeof loadReview>>["profile"];
}) {
  return (
    <>
      <dl>
        {snapshot.fields.map((field) => (
          <div key={field.key}>
            <dt>
              {profile.scalarFields.find((item) => item.key === field.key)
                ?.label ?? field.key}
            </dt>
            <dd>{displayValue(field.value)}</dd>
          </div>
        ))}
      </dl>
      {snapshot.tables.map((table) => (
        <section key={table.key}>
          <h3>
            {profile.tableFields.find((item) => item.key === table.key)
              ?.label ?? table.key}
          </h3>
          {table.rows.length === 0 && <p>Bez riadkov</p>}
          {table.rows.map((row, index) => (
            <div key={row.rowId}>
              <p>Riadok {index + 1}</p>
              <dl>
                {row.cells.map((cell) => (
                  <div key={cell.key}>
                    <dt>
                      {profile.tableFields
                        .find((item) => item.key === table.key)
                        ?.columns.find((item) => item.key === cell.key)
                        ?.label ?? cell.key}
                    </dt>
                    <dd>{displayValue(cell.value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
