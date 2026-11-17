import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../../shared/api";
import { Button, Notice } from "../../shared/ui";
import { errorMessage, type Profile } from "./model";

export function TrialRun({
  profile,
  dirty,
}: {
  profile: Profile;
  dirty: boolean;
}) {
  const navigate = useNavigate();
  const [documentId, setDocumentId] = useState("");
  const [running, setRunning] = useState(false);
  const [failure, setFailure] = useState("");
  const capabilities = useQuery({
    queryKey: ["capabilities"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/capabilities");
      if (error) throw new Error(errorMessage(error.error.code));
      return data.data;
    },
  });
  const documents = useQuery({
    queryKey: ["trial-documents"],
    queryFn: async () => {
      const items: import("../../shared/api.generated").components["schemas"]["Document"][] =
        [];
      let total = 1;
      while (items.length < total) {
        const { data, error } = await api.GET("/api/v1/documents", {
          params: { query: { limit: 200, offset: items.length } },
        });
        if (error) throw new Error(errorMessage(error.error.code));
        items.push(...data.data);
        total = data.pagination.total;
        if (!data.data.length) break;
      }
      return items.filter((document) => document.status === "ready");
    },
  });
  const available =
    !capabilities.isError &&
    !capabilities.isPending &&
    !capabilities.isFetching &&
    capabilities.data &&
    (capabilities.data.mode === "fixture" || capabilities.data.aiConfigured);
  async function run() {
    setRunning(true);
    setFailure("");
    try {
      const { data, error } = await api.POST("/api/v1/extractions", {
        body: {
          documentIds: [documentId],
          profileId: profile.id,
          profileVersion: profile.version,
        },
      });
      if (error) {
        setFailure(
          error.error.code === "CONFLICT"
            ? "Dokument alebo profil nie je pripravený na skúšku. Obnovte údaje a skúste znova."
            : errorMessage(error.error.code),
        );
        return;
      }
      const extraction = data.data.extractions[0];
      if (!extraction || extraction.documentId !== documentId) {
        setFailure("Server nevrátil očakávanú skúšku dokumentu.");
        return;
      }
      navigate(`/review/${encodeURIComponent(extraction.id)}`);
    } catch {
      setFailure(errorMessage());
    } finally {
      setRunning(false);
    }
  }
  return (
    <section aria-label="Skúška profilu">
      <h2>Skúška uloženej verzie {profile.version}</h2>
      <p className="profiles-muted">
        Skúška použije uloženú verziu a otvorí spoločnú kontrolu údajov. Žiadne
        údaje sa automaticky neodosielajú do eGrantu.
      </p>
      {!capabilities.isError && capabilities.data?.mode === "fixture" && (
        <Notice>
          Ukážková extrakcia používa syntetické údaje. Presnosť živého
          poskytovateľa nie je overená.
        </Notice>
      )}
      {capabilities.data?.mode === "live" &&
        !capabilities.data.aiConfigured && (
          <p className="field-error">Živá extrakcia nie je nakonfigurovaná.</p>
        )}
      {dirty && (
        <Notice>
          Pred skúškou uložte zmeny alebo ich zahoďte. Skúška používa iba
          uloženú verziu.
        </Notice>
      )}
      {(documents.isPending || capabilities.isPending) && (
        <Notice>Načítavame dokumenty a dostupnosť extrakcie…</Notice>
      )}
      {capabilities.isError && (
        <p role="alert" className="field-error">
          Dostupnosť extrakcie sa nepodarilo overiť. Skúšku nemožno spustiť.
        </p>
      )}
      {documents.isError && (
        <p role="alert" className="field-error">
          {documents.error.message}
        </p>
      )}
      <label className="profiles-control">
        Dokument na skúšku
        <select
          value={documentId}
          onChange={(event) => setDocumentId(event.target.value)}
          disabled={documents.isPending || documents.isError}
        >
          <option value="">Vyberte spracovaný dokument</option>
          {documents.data?.map((document) => (
            <option key={document.id} value={document.id}>
              {document.filename}
            </option>
          ))}
        </select>
      </label>
      {documents.data?.length === 0 && (
        <p>
          Nie je dostupný žiadny spracovaný dokument. Najprv ho nahrajte v časti
          Dokumenty.
        </p>
      )}
      {failure && (
        <p role="alert" className="field-error">
          {failure}
        </p>
      )}
      <div className="profiles-toolbar">
        <Button
          type="button"
          disabled={
            !available || !documentId || dirty || running || documents.isError
          }
          onClick={run}
        >
          {running ? "Spúšťame…" : "Spustiť skúšku"}
        </Button>
      </div>
    </section>
  );
}
