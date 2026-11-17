import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../shared/api";
import { Notice } from "../../shared/ui";
import { errorMessage } from "./errors";

export function DocumentPreview({
  id,
  search,
  onClose,
}: {
  id: string;
  search: URLSearchParams;
  onClose: () => void;
}) {
  const [blobUrl, setBlobUrl] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [id]);
  const [, setSearch] = useSearchParams();
  const [visibleUnits, setVisibleUnits] = useState(50);
  const sheet = search.get("sheet") ?? "";
  const cell = search.get("cell") ?? "";
  function selectLocation(key: "sheet" | "cell", value: string) {
    const next = new URLSearchParams(search);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("unit");
    setSearch(next, { replace: true });
    setVisibleUnits(50);
  }
  const document = useQuery({
    queryKey: ["document-preview", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/documents/{id}", {
        params: { path: { id } },
      });
      if (error) throw new Error(errorMessage(error.error.code));
      return data.data;
    },
    refetchInterval: (query) =>
      query.state.data?.status === "uploaded" ||
      query.state.data?.status === "processing"
        ? 1500
        : false,
    retry: false,
  });
  const content = useQuery({
    queryKey: ["document-content", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/documents/{id}/content", {
        params: { path: { id } },
        parseAs: "blob",
      });
      if (error) throw new Error(errorMessage(error.error.code));
      return data;
    },
    retry: false,
    gcTime: 0,
  });
  const normalized = useQuery({
    queryKey: ["document-sources", id],
    enabled: document.data?.status === "ready",
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/documents/{id}/normalized",
        { params: { path: { id } } },
      );
      if (error) throw new Error(errorMessage(error.error.code));
      return data.data;
    },
    retry: false,
    gcTime: 0,
  });
  useEffect(() => {
    if (!content.data) return;
    const url = URL.createObjectURL(content.data);
    setBlobUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [content.data]);
  const page = Math.max(
    1,
    Math.min(Number(search.get("page")) || 1, document.data?.pageCount ?? 1),
  );
  const sheets = [
    ...new Set(
      normalized.data?.units
        .map((unit) => unit.sheet)
        .filter((value): value is string => !!value),
    ),
  ];
  const units =
    normalized.data?.units.filter(
      (unit) =>
        (!search.get("page") || unit.page === page) &&
        (!search.get("unit") || unit.id === search.get("unit")) &&
        (!sheet || unit.sheet === sheet) &&
        (!cell || unit.cell?.toUpperCase() === cell.toUpperCase()),
    ) ?? [];
  return (
    <section className="upload-preview" aria-label="Náhľad dokumentu">
      <div className="upload-section-heading">
        <h2 ref={heading} tabIndex={-1}>
          Náhľad dokumentu
        </h2>
        <button className="upload-text-button" onClick={onClose}>
          <X size={16} aria-hidden="true" /> Zavrieť náhľad
        </button>
      </div>
      {document.isPending ? (
        <Notice>Načítavame náhľad…</Notice>
      ) : document.isError ? (
        <Notice>
          Náhľad nie je dostupný.{" "}
          <button
            className="upload-text-button"
            onClick={() => void document.refetch()}
          >
            Skúsiť znova
          </button>
        </Notice>
      ) : (
        <>
          <h3 className="upload-filename">{document.data.filename}</h3>
          {document.data.pageCount && document.data.pageCount > 1 && (
            <label className="upload-page-selector">
              Strana
              <select
                value={page}
                onChange={(event) => {
                  const next = new URLSearchParams(search);
                  next.set("page", event.target.value);
                  next.delete("unit");
                  setSearch(next);
                }}
              >
                {Array.from({ length: document.data.pageCount }, (_, index) => (
                  <option key={index + 1}>{index + 1}</option>
                ))}
              </select>
            </label>
          )}
          {content.isPending ? (
            <Notice>Načítavame originál…</Notice>
          ) : content.isError ? (
            <Notice>
              Originál sa nepodarilo načítať.{" "}
              <button
                className="upload-text-button"
                onClick={() => void content.refetch()}
              >
                Skúsiť znova
              </button>
            </Notice>
          ) : (
            blobUrl && (
              <>
                <a
                  className="upload-text-button"
                  href={blobUrl}
                  download={document.data.filename}
                >
                  Stiahnuť originál
                </a>
                {document.data.mediaType === "application/pdf" ? (
                  <iframe
                    title="Originálny dokument PDF"
                    src={`${blobUrl}#page=${page}`}
                  />
                ) : document.data.mediaType.startsWith("image/") ? (
                  <img
                    src={blobUrl}
                    alt={`Originál: ${document.data.filename}`}
                  />
                ) : null}
              </>
            )
          )}
          <h3>Zdrojové údaje</h3>
          {document.data.status !== "ready" ? (
            <Notice>
              {document.data.error
                ? errorMessage(document.data.error.code)
                : "Zdrojové údaje budú dostupné po spracovaní dokumentu."}
            </Notice>
          ) : normalized.isPending ? (
            <Notice>Načítavame zdrojové údaje…</Notice>
          ) : normalized.isError ? (
            <Notice>
              Zdrojové údaje sa nepodarilo načítať.{" "}
              <button
                className="upload-text-button"
                onClick={() => void normalized.refetch()}
              >
                Skúsiť znova
              </button>
            </Notice>
          ) : (
            <>
              {sheets.length > 0 && (
                <div className="upload-source-filters">
                  <label>
                    Hárok
                    <select
                      value={sheet}
                      onChange={(event) => {
                        selectLocation("sheet", event.target.value);
                      }}
                    >
                      <option value="">Všetky hárky</option>
                      {sheets.map((name) => (
                        <option key={name}>{name}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Bunka
                    <input
                      value={cell}
                      placeholder="A1"
                      onChange={(event) => {
                        selectLocation("cell", event.target.value);
                      }}
                    />
                  </label>
                </div>
              )}
              {units.length === 0 ? (
                <p>Pre túto polohu sa nenašli zdrojové údaje.</p>
              ) : (
                <ol className="upload-source-list">
                  {units.slice(0, visibleUnits).map((unit) => (
                    <li key={unit.id}>
                      <strong>
                        {unit.page
                          ? `Strana ${unit.page}`
                          : `${unit.sheet} · ${unit.cell}`}
                      </strong>
                      <pre>{unit.text}</pre>
                    </li>
                  ))}
                </ol>
              )}
              {units.length > visibleUnits && (
                <button
                  className="upload-text-button"
                  onClick={() => setVisibleUnits((value) => value + 50)}
                >
                  Zobraziť ďalších 50 zdrojov
                </button>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
