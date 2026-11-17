import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../shared/api";
import { Button, Notice } from "../shared/ui";
import type { components } from "../shared/api.generated";

type Submission = components["schemas"]["Submission"];
const statuses: Record<Submission["status"], string> = {
  prepared: "Pripravené na export",
  exported: "Exportované do JSON",
  applying: "Prebieha zápis",
  applied: "Zapísané do eGrantu",
  failed: "Operácia zlyhala",
  unknown: "Výsledok zápisu nie je známy",
};

function failureMessage(code?: string) {
  if (code === "CONFLICT")
    return "Údaje sa zmenili alebo ešte nie sú potvrdené. Obnovte kontrolu údajov.";
  if (code === "FEATURE_UNAVAILABLE")
    return "Táto operácia zatiaľ nie je dostupná.";
  if (code === "VALIDATION_ERROR")
    return "Údaje alebo mapovanie nie sú platné. Skontrolujte profil a potvrdené hodnoty.";
  return "Operáciu sa nepodarilo dokončiť. Skúste znova.";
}

export function SubmissionPage() {
  const { id = "" } = useParams();
  const cache = useQueryClient();
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const submission = useQuery({
    queryKey: ["submission", id],
    retry: false,
    queryFn: async () => {
      const result = await api.GET("/api/v1/submissions/{id}", {
        params: { path: { id } },
      });
      if (result.error)
        throw new Error(failureMessage(result.error.error.code));
      return result.data.data;
    },
    refetchInterval: (query) =>
      query.state.data?.status === "applying" ? 3000 : false,
  });
  async function download() {
    setDownloading(true);
    setDownloadError(null);
    try {
      const result = await api.GET("/api/v1/submissions/{id}/export", {
        params: { path: { id } },
        parseAs: "blob",
      });
      if (result.error) throw new Error();
      const url = URL.createObjectURL(result.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `submission-${id}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      await cache.invalidateQueries({ queryKey: ["submission", id] });
    } catch {
      setDownloadError("Súbor sa nepodarilo stiahnuť. Skúste znova.");
    } finally {
      setDownloading(false);
    }
  }
  const data = submission.data;
  return (
    <section className="workspace submission-status">
      <p className="eyebrow">Výsledok kontroly</p>
      <h1>Export a odoslanie</h1>
      {submission.isPending ? (
        <Notice>Načítavame operáciu…</Notice>
      ) : submission.isError ? (
        <>
          <p role="alert" className="field-error">
            Operáciu sa nepodarilo načítať.
          </p>
          <Button onClick={() => void submission.refetch()}>
            Skúsiť znova
          </Button>
        </>
      ) : (
        data && (
          <>
            <Notice>{statuses[data.status]}</Notice>
            <dl className="operation-details">
              <dt>Operácia</dt>
              <dd>{data.id}</dd>
              <dt>Potvrdená revízia</dt>
              <dd>{data.reviewRevision}</dd>
              <dt>Verzia profilu</dt>
              <dd>{data.payload.profileVersion}</dd>
              <dt>Vytvorené</dt>
              <dd>{new Date(data.createdAt).toLocaleString("sk-SK")}</dd>
            </dl>
            <Link className="text-link" to={`/review/${data.reviewId}`}>
              Otvoriť kontrolu údajov
            </Link>
            <p>
              {data.mode === "export"
                ? "Export JSON nie je zápis do eGrantu."
                : "Režim zápisu do eGrantu"}
            </p>
            {data.status === "unknown" && (
              <p role="alert">
                Zápis neopakujte. Správca musí overiť výsledok v eGrante.
              </p>
            )}
            {data.error && (
              <p className="field-error" role="alert">
                {failureMessage(data.error.code)}
              </p>
            )}
            {data.mode === "export" &&
              ["prepared", "exported"].includes(data.status) && (
                <Button onClick={() => void download()} disabled={downloading}>
                  {downloading ? "Sťahujeme…" : "Stiahnuť JSON"}
                </Button>
              )}
            {downloadError && (
              <p className="field-error" role="alert">
                {downloadError}
              </p>
            )}
            <h2>Obsah potvrdeného exportu</h2>
            <pre
              className="payload-preview"
              tabIndex={0}
              aria-label="Potvrdený obsah JSON"
            >
              {JSON.stringify(data.payload, null, 2)}
            </pre>
          </>
        )
      )}
    </section>
  );
}
