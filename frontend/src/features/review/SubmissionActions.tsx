import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../shared/api";
import { Button } from "../../shared/ui";
import {
  dataOf,
  errorText,
  RequestError,
  type Profile,
  type Review,
  type Submission,
} from "./model";

type ApplyIntent = { key: string; applicationId: string };

function readIntent(storageKey: string): ApplyIntent | null {
  try {
    const stored: unknown = JSON.parse(
      sessionStorage.getItem(storageKey) ?? "null",
    );
    if (
      stored &&
      typeof stored === "object" &&
      "key" in stored &&
      "applicationId" in stored &&
      typeof stored.key === "string" &&
      typeof stored.applicationId === "string"
    )
      return { key: stored.key, applicationId: stored.applicationId };
  } catch {
    /* Unavailable storage is handled before any write request. */
  }
  return null;
}

export function SubmissionActions({
  review,
  profile,
}: {
  review: Review;
  profile: Profile;
}) {
  const pendingKey = `egrant:pending-apply:${review.extractionId}:${review.revision}`;
  const [intent, setIntent] = useState(() => readIntent(pendingKey));
  const [applicationId, setApplicationId] = useState(
    intent?.applicationId ?? "",
  );
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exported, setExported] = useState<Submission | null>(null);
  const [applied, setApplied] = useState<Submission | null>(null);
  const capabilities = useQuery({
    queryKey: ["capabilities"],
    retry: false,
    queryFn: async () => dataOf(await api.GET("/api/v1/capabilities")),
  });
  const replaces = profile.tableFields.some(
    (table) => table.writeMode === "replace",
  );
  async function submit(mode: "export" | "egrant") {
    if (review.status !== "confirmed" || busy) return;
    if (
      mode === "egrant" &&
      (replaces ||
        !capabilities.data?.egrantConfigured ||
        (!intent && (!consent || !applicationId.trim())))
    )
      return;
    setBusy(true);
    setError(null);
    try {
      let key: string;
      let target: string | null = null;
      if (mode === "egrant") {
        // An unresolved intent survives reload and locks the target. Retrying reuses its key.
        const pending = intent ?? {
          key: crypto.randomUUID(),
          applicationId: applicationId.trim(),
        };
        sessionStorage.setItem(pendingKey, JSON.stringify(pending));
        setIntent(pending);
        key = pending.key;
        target = pending.applicationId;
      } else {
        const storageKey = `egrant:export:${review.extractionId}:${review.revision}`;
        key = sessionStorage.getItem(storageKey) ?? crypto.randomUUID();
        sessionStorage.setItem(storageKey, key);
      }
      const result = dataOf(
        await api.POST("/api/v1/submissions", {
          params: { header: { "idempotency-key": key } },
          body: {
            reviewId: review.extractionId,
            reviewRevision: review.revision,
            mode,
            targetContext: { applicationId: target },
            acknowledgeOverwrite: false,
          },
        }),
      );
      if (mode === "export") setExported(result);
      else setApplied(result);
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    if (!applied) return;
    setBusy(true);
    setError(null);
    try {
      setApplied(
        dataOf(
          await api.GET("/api/v1/submissions/{id}", {
            params: { path: { id: applied.id } },
          }),
        ),
      );
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    if (!exported) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.GET("/api/v1/submissions/{id}/export", {
        params: { path: { id: exported.id } },
      });
      if (!result.data || !result.response.ok)
        throw new RequestError(result.response.status);
      // Only the server constructs destination tags and payload values.
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(result.data, null, 2)], {
          type: "application/json",
        }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `submission-${exported.id}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
      setExported({ ...exported, status: "exported" });
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setBusy(false);
    }
  }
  const labels: Record<Submission["status"], string> = {
    prepared: "Pripravené",
    exported: "Exportované — bez zápisu do eGrantu",
    applying: "Prebieha zápis",
    applied: "Zapísané",
    failed: "Operácia zlyhala — najprv overte výsledok",
    unknown: "Výsledok zápisu je neznámy — vyžaduje overenie správcom",
  };
  if (review.status !== "confirmed") return null;
  return (
    <section className="review-submission" aria-label="Export a zápis">
      <h2>Čo chcete urobiť s potvrdenými údajmi?</h2>
      <p>JSON export nezapisuje do eGrantu. Zápis je samostatná operácia.</p>
      {error && <p role="alert">{error}</p>}
      <Button disabled={busy} onClick={() => void submit("export")}>
        Exportovať JSON
      </Button>
      {exported && (
        <>
          <p role="status">{labels[exported.status]}</p>
          <Button disabled={busy} onClick={() => void download()}>
            Stiahnuť JSON
          </Button>
        </>
      )}
      {applied && (
        <>
          <p role="status">{labels[applied.status]}</p>
          <Button disabled={busy} onClick={() => void refresh()}>
            Overiť stav operácie
          </Button>
        </>
      )}
      {capabilities.isError && (
        <p role="alert">
          Stav eGrantu nie je dostupný.{" "}
          <button type="button" onClick={() => void capabilities.refetch()}>
            Znova overiť dostupnosť
          </button>
        </p>
      )}
      {!capabilities.data?.egrantConfigured && (
        <p>Zápis do eGrantu nie je dostupný.</p>
      )}
      {replaces && (
        <p>
          Profil požaduje nahradenie tabuľky. Zápis je nedostupný, kým nie je
          možné bezpečne zobraziť a potvrdiť dôsledky prepísania aktuálnych
          údajov.
        </p>
      )}
      {capabilities.data?.egrantConfigured && !replaces && (
        <fieldset disabled={busy || !!intent}>
          <legend>Výslovné povolenie zápisu do eGrantu</legend>
          <label htmlFor="review-application">
            Identifikátor cieľovej žiadosti
          </label>
          <input
            id="review-application"
            value={applicationId}
            onChange={(event) => setApplicationId(event.target.value)}
          />
          <label className="review-check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            Potvrdzujem zápis potvrdených údajov do uvedenej žiadosti.
          </label>
          <Button
            disabled={!consent || !applicationId.trim()}
            onClick={() => void submit("egrant")}
          >
            Zapísať do eGrantu
          </Button>
        </fieldset>
      )}
      {intent && !applied && (
        <>
          <p role="alert">
            Pôvodná požiadavka vyžaduje overenie. Nevytvárajte nový zápis.
            Overenie používa rovnaký kľúč a cieľovú žiadosť.
          </p>
          <Button
            disabled={busy || !capabilities.data?.egrantConfigured}
            onClick={() => void submit("egrant")}
          >
            Overiť pôvodnú požiadavku
          </Button>
        </>
      )}
    </section>
  );
}
