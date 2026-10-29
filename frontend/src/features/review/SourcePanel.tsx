import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../shared/api";
import { Button, Notice } from "../../shared/ui";
import { dataOf, errorText, type Source } from "./model";

export function SourcePanel({
  documentId,
  selected,
}: {
  documentId: string;
  selected: Source | null;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [previewAttempt, setPreviewAttempt] = useState(0);
  const document = useQuery({
    queryKey: ["review-document", documentId],
    retry: false,
    queryFn: async () =>
      dataOf(
        await api.GET("/api/v1/documents/{id}", {
          params: { path: { id: documentId } },
        }),
      ),
  });
  const normalized = useQuery({
    queryKey: ["review-normalized", documentId],
    retry: false,
    queryFn: async () =>
      dataOf(
        await api.GET("/api/v1/documents/{id}/normalized", {
          params: { path: { id: documentId } },
        }),
      ),
  });
  useEffect(() => {
    if (selected) heading.current?.focus();
  }, [selected]);
  const unit = normalized.data?.units.find(
    (item) => item.id === selected?.unitId,
  );
  const validSource =
    selected?.documentId === documentId &&
    normalized.data?.documentId === documentId &&
    unit !== undefined;
  const page =
    validSource &&
    unit.page &&
    unit.page >= 1 &&
    (!document.data?.pageCount || unit.page <= document.data.pageCount)
      ? unit.page
      : null;
  const content = `/api/v1/documents/${encodeURIComponent(documentId)}/content`;
  return (
    <aside className="review-source" aria-label="Zdrojový dokument">
      <p className="eyebrow">Zdrojové podklady</p>
      {previewFailed && (
        <div role="alert">
          Náhľad obrázka sa nepodarilo načítať. Skúste obnoviť dokument.
          <Button
            onClick={() => {
              setPreviewFailed(false);
              setPreviewAttempt((attempt) => attempt + 1);
            }}
          >
            Znova načítať obrázok
          </Button>
        </div>
      )}
      <h2 ref={heading} tabIndex={-1}>
        Dokument a dôkazy
      </h2>
      {document.isPending ? (
        <Notice>Načítavame dokument…</Notice>
      ) : document.isError ? (
        <>
          <p role="alert">{errorText(document.error)}</p>
          <Button onClick={() => void document.refetch()}>
            Znova načítať dokument
          </Button>
        </>
      ) : (
        <>
          <p>{document.data.filename}</p>
          {document.data.mediaType === "application/pdf" ? (
            <>
              <a
                href={`${content}${page ? `#page=${page}` : ""}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Otvoriť PDF{page ? ` — strana ${page}` : ""}
              </a>
              <iframe
                title="Náhľad PDF"
                sandbox=""
                src={`${content}${page ? `#page=${page}` : ""}`}
              />
            </>
          ) : ["image/png", "image/jpeg"].includes(document.data.mediaType) ? (
            <img
              key={previewAttempt}
              src={content}
              alt="Nahraný zdrojový dokument"
              onError={() => setPreviewFailed(true)}
              onLoad={() => setPreviewFailed(false)}
            />
          ) : (
            <p>
              Tabuľkové podklady sa zobrazujú ako bezpečný text; vzorce ani
              makrá sa nespúšťajú.
            </p>
          )}
        </>
      )}
      {normalized.isPending ? (
        <Notice>Načítavame text zdroja…</Notice>
      ) : normalized.isError ? (
        <>
          <p role="alert">{errorText(normalized.error)}</p>
          <Button onClick={() => void normalized.refetch()}>
            Znova načítať text
          </Button>
        </>
      ) : (
        <>
          {selected && !validSource && (
            <p role="alert">Odkaz na zdroj sa nepodarilo overiť.</p>
          )}
          {validSource && (
            <section className="review-evidence" aria-label="Vybraný zdroj">
              <h3>
                {unit.sheet
                  ? `${unit.sheet} · ${unit.cell ?? ""}`
                  : page
                    ? `Strana ${page}`
                    : "Textový úsek"}
              </h3>
              {selected?.quote && unit.text.includes(selected.quote) ? (
                <blockquote>{selected.quote}</blockquote>
              ) : (
                <p>Presný podporný citát nie je dostupný.</p>
              )}
              <pre>{unit.text}</pre>
            </section>
          )}
          <details open={!selected}>
            <summary>Text dokumentu</summary>
            {normalized.data.units.length === 0 ? (
              <p>Dokument neobsahuje dostupný text.</p>
            ) : (
              normalized.data.units.map((item) => (
                <section key={item.id}>
                  <h3>
                    {item.sheet
                      ? `${item.sheet} · ${item.cell ?? ""}`
                      : item.page
                        ? `Strana ${item.page}`
                        : "Textový úsek"}
                  </h3>
                  <pre>{item.text}</pre>
                </section>
              ))
            )}
          </details>
        </>
      )}
    </aside>
  );
}
