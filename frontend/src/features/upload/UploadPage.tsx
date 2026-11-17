import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { FileText, Upload } from "lucide-react";
import { api } from "../../shared/api";
import type { components } from "../../shared/api.generated";
import { Button, Notice } from "../../shared/ui";
import { DocumentPreview } from "./DocumentPreview";
import { errorMessage, UploadRequestError } from "./errors";
import "./upload.css";

type Document = components["schemas"]["Document"];
type LocalUpload = {
  id: number;
  file: File;
  state: "uploading" | "failed";
  error?: string;
};
const statusLabels: Record<Document["status"], string> = {
  uploaded: "Čaká na spracovanie",
  processing: "Spracúva sa",
  ready: "Pripravený",
  failed: "Spracovanie zlyhalo",
};

export function UploadPage() {
  const cache = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const previewTrigger = useRef<HTMLButtonElement>(null);
  const nextUpload = useRef(0);
  const [search, setSearch] = useSearchParams();
  const [offset, setOffset] = useState(0);
  const [uploads, setUploads] = useState<LocalUpload[]>([]);
  const [dragging, setDragging] = useState(false);
  const [profileKey, setProfileKey] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [launching, setLaunching] = useState(false);
  const [actionError, setActionError] = useState("");
  const [retrying, setRetrying] = useState<string[]>([]);
  const [createdLinks, setCreatedLinks] = useState<
    components["schemas"]["QueuedExtraction"][]
  >([]);
  const previewId = search.get("document");
  const documents = useQuery({
    queryKey: ["documents", offset],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/documents", {
        params: { query: { limit: 50, offset } },
      });
      if (error) throw new UploadRequestError(error.error.code);
      return data;
    },
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.data.some(
        (document) =>
          document.status === "uploaded" || document.status === "processing",
      )
        ? 1500
        : false,
  });
  const profiles = useQuery({
    queryKey: ["upload-profiles"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/profiles", {
        params: { query: { limit: 200 } },
      });
      if (error) throw new UploadRequestError(error.error.code);
      return data;
    },
    retry: false,
  });
  const capabilities = useQuery({
    queryKey: ["capabilities"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/capabilities");
      if (error) throw new UploadRequestError(error.error.code);
      return data.data;
    },
    retry: false,
  });
  const extractions = useQuery({
    queryKey: ["upload-extractions"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/extractions", {
        params: { query: { limit: 200 } },
      });
      if (error) throw new UploadRequestError(error.error.code);
      return data;
    },
    retry: false,
  });

  async function uploadFile(local: LocalUpload) {
    setUploads((current) =>
      current.map((entry) =>
        entry.id === local.id
          ? { ...entry, state: "uploading", error: undefined }
          : entry,
      ),
    );
    const form = new FormData();
    form.append("files", local.file);
    try {
      // Separate requests preserve accepted files when another file is rejected.
      const { error } = await api.POST("/api/v1/documents", {
        body: { files: [] },
        bodySerializer: () => form,
      });
      if (error) throw new UploadRequestError(error.error.code);
      setUploads((current) => current.filter((entry) => entry.id !== local.id));
      setOffset(0);
      await cache.invalidateQueries({ queryKey: ["documents"] });
    } catch (error) {
      setUploads((current) =>
        current.map((entry) =>
          entry.id === local.id
            ? {
                ...entry,
                state: "failed",
                error:
                  error instanceof UploadRequestError
                    ? error.message
                    : errorMessage(),
              }
            : entry,
        ),
      );
    }
  }
  async function addFiles(files: File[]) {
    const incoming = files.map((file) => ({
      id: ++nextUpload.current,
      file,
      state: "uploading" as const,
    }));
    setUploads((current) => [...current, ...incoming]);
    for (const local of incoming) await uploadFile(local);
  }
  async function retryDocument(id: string) {
    setActionError("");
    setRetrying((current) => [...current, id]);
    try {
      const { error } = await api.POST("/api/v1/documents/{id}/retries", {
        params: { path: { id } },
      });
      if (error) throw new UploadRequestError(error.error.code);
    } catch (error) {
      setActionError(
        error instanceof UploadRequestError ? error.message : errorMessage(),
      );
    } finally {
      setRetrying((current) => current.filter((value) => value !== id));
      await cache.invalidateQueries({ queryKey: ["documents"] });
      await cache.invalidateQueries({ queryKey: ["document-preview", id] });
    }
  }
  async function launchExtraction() {
    const profile = profiles.data?.data.find(
      (candidate) => `${candidate.id}:${candidate.version}` === profileKey,
    );
    if (!profile || !selected.length) return;
    setLaunching(true);
    setActionError("");
    try {
      const { data, error } = await api.POST("/api/v1/extractions", {
        body: {
          documentIds: selected,
          profileId: profile.id,
          profileVersion: profile.version,
        },
      });
      if (error) throw new UploadRequestError(error.error.code);
      setSelected([]);
      setCreatedLinks((current) => [...data.data.extractions, ...current]);
      await cache.invalidateQueries({ queryKey: ["upload-extractions"] });
    } catch (error) {
      setActionError(
        error instanceof UploadRequestError ? error.message : errorMessage(),
      );
    } finally {
      setLaunching(false);
    }
  }
  const readyIds =
    documents.data?.data
      .filter((document) => document.status === "ready")
      .map((document) => document.id) ?? [];
  const canExtract =
    !!capabilities.data &&
    (capabilities.data.aiConfigured || capabilities.data.mode === "fixture");
  return (
    <section className="upload-workspace" aria-labelledby="upload-title">
      <p className="eyebrow">Dokumenty a zdroje</p>
      <h1 id="upload-title">Nahrať dokumenty</h1>
      <p className="upload-intro">
        Pridajte podklady, vyberte profil a pripravte údaje na kontrolu.
      </p>
      <div
        className={`upload-dropzone ${dragging ? "is-dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void addFiles(Array.from(event.dataTransfer.files));
        }}
      >
        <Upload size={28} aria-hidden="true" />
        <div>
          <strong>Presuňte súbory sem</strong>
          <p>PDF, JPEG, PNG, XLSX alebo CSV · najviac 20 MiB na súbor</p>
        </div>
        <Button type="button" onClick={() => input.current?.click()}>
          Vybrať súbory
        </Button>
        <input
          ref={input}
          className="upload-file-input"
          type="file"
          multiple
          aria-label="Vybrať dokumenty"
          accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv"
          onChange={(event) => {
            void addFiles(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </div>
      {capabilities.isError ? (
        <Notice>
          Stav integrácií sa nepodarilo načítať.{" "}
          <button
            className="upload-text-button"
            onClick={() => void capabilities.refetch()}
          >
            Skúsiť znova
          </button>
        </Notice>
      ) : (
        capabilities.data &&
        !capabilities.data.ocrConfigured && (
          <Notice>
            OCR nie je dostupné. Textové PDF a tabuľky možno spracovať;
            fotografie a skeny vyžadujú nastavenie OCR správcom.
          </Notice>
        )
      )}
      {uploads.length > 0 && (
        <ul className="upload-local-list" aria-label="Nahrávanie súborov">
          {uploads.map((local) => (
            <li key={local.id}>
              <span className="upload-filename">{local.file.name}</span>
              {local.state === "uploading" ? (
                <span role="status">Nahráva sa…</span>
              ) : (
                <>
                  <p className="field-error" role="alert">
                    {local.error}
                  </p>
                  <button
                    className="upload-text-button"
                    onClick={() => void uploadFile(local)}
                  >
                    Zopakovať nahrávanie
                  </button>
                  <button
                    className="upload-text-button"
                    onClick={() =>
                      setUploads((current) =>
                        current.filter((entry) => entry.id !== local.id),
                      )
                    }
                  >
                    Odstrániť zo zoznamu
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="upload-section-heading">
        <h2>Vaše dokumenty</h2>
        <button
          className="upload-text-button"
          disabled={documents.isFetching}
          onClick={() => void documents.refetch()}
        >
          Obnoviť zoznam
        </button>
      </div>
      {documents.isPending ? (
        <Notice>Načítavame dokumenty…</Notice>
      ) : documents.isError ? (
        <Notice>Zoznam sa nepodarilo načítať. Skúste ho obnoviť.</Notice>
      ) : documents.data.data.length === 0 ? (
        <p className="upload-empty">
          Zatiaľ tu nie sú žiadne dokumenty. Začnite výberom súborov.
        </p>
      ) : (
        <ul className="upload-document-list" aria-label="Prijaté dokumenty">
          {documents.data.data.map((document) => {
            const links = [
              ...createdLinks,
              ...(extractions.data?.data ?? []),
            ].filter(
              (extraction, index, all) =>
                extraction.documentId === document.id &&
                all.findIndex((candidate) => candidate.id === extraction.id) ===
                  index,
            );
            return (
              <li key={document.id}>
                <div className="upload-document-main">
                  <label className="upload-select-control">
                    <input
                      type="checkbox"
                      aria-label={`Vybrať ${document.filename}`}
                      disabled={document.status !== "ready" || launching}
                      checked={selected.includes(document.id)}
                      onChange={(event) =>
                        setSelected((current) =>
                          event.target.checked
                            ? [...current, document.id]
                            : current.filter((id) => id !== document.id),
                        )
                      }
                    />
                  </label>
                  <FileText size={22} aria-hidden="true" />
                  <div className="upload-document-label">
                    <strong>{document.filename}</strong>
                    <span>
                      {statusLabels[document.status]}
                      {document.pageCount
                        ? ` · ${document.pageCount} str.`
                        : ""}
                    </span>
                  </div>
                  <button
                    className="upload-text-button"
                    onClick={(event) => {
                      previewTrigger.current = event.currentTarget;
                      setSearch({ document: document.id });
                    }}
                  >
                    Náhľad
                  </button>
                </div>
                {document.duplicateOf && (
                  <p className="upload-warning">
                    Rovnaký súbor už bol nahraný. Táto kópia sa spracuje
                    samostatne.
                  </p>
                )}
                {document.warnings.some(
                  (warning) => warning.code === "FORMULA_VALUE_UNAVAILABLE",
                ) && (
                  <p className="upload-warning">
                    Niektoré vzorce nemajú uložený výsledok. Pred nahratím
                    uložte prepočítanú tabuľku.
                  </p>
                )}
                {document.error && (
                  <div className="upload-document-error">
                    <p className="field-error">
                      {errorMessage(document.error.code)}
                    </p>
                    {document.status === "failed" && (
                      <button
                        className="upload-text-button"
                        disabled={retrying.includes(document.id)}
                        onClick={() => void retryDocument(document.id)}
                      >
                        {retrying.includes(document.id)
                          ? "Opakujeme…"
                          : "Zopakovať spracovanie"}
                      </button>
                    )}
                  </div>
                )}
                {links.length > 0 && (
                  <ul className="upload-review-links">
                    {links.map((extraction) => (
                      <li key={extraction.id}>
                        <Link to={`/review/${extraction.id}`}>
                          Skontrolovať údaje{" "}
                          <span className="upload-run-id">
                            {extraction.id.slice(0, 8)}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {!!documents.data?.pagination.total &&
        documents.data.pagination.total > 50 && (
          <div className="upload-pagination">
            <button
              className="upload-text-button"
              disabled={offset === 0}
              onClick={() => {
                setOffset(Math.max(0, offset - 50));
                setSelected([]);
              }}
            >
              Predchádzajúce
            </button>
            <span>
              {offset + 1}–
              {Math.min(offset + 50, documents.data.pagination.total)} z{" "}
              {documents.data.pagination.total}
            </span>
            <button
              className="upload-text-button"
              disabled={offset + 50 >= documents.data.pagination.total}
              onClick={() => {
                setOffset(offset + 50);
                setSelected([]);
              }}
            >
              Ďalšie
            </button>
          </div>
        )}
      <section className="upload-extraction" aria-labelledby="extraction-title">
        <h2 id="extraction-title">Pripraviť údaje</h2>
        <p>
          Každý dokument vytvorí samostatný návrh. Údaje potom skontrolujete a
          výslovne potvrdíte.
        </p>
        {profiles.isPending ? (
          <Notice>Načítavame profily…</Notice>
        ) : profiles.isError ? (
          <Notice>
            Profily nie sú dostupné.{" "}
            <button
              className="upload-text-button"
              onClick={() => void profiles.refetch()}
            >
              Skúsiť znova
            </button>
          </Notice>
        ) : profiles.data.data.length === 0 ? (
          <Notice>
            Najprv vytvorte <Link to="/profiles/new">extrakčný profil</Link>.
          </Notice>
        ) : (
          <>
            <label htmlFor="upload-profile">Extrakčný profil</label>
            <select
              id="upload-profile"
              value={profileKey}
              disabled={launching}
              onChange={(event) => setProfileKey(event.target.value)}
            >
              <option value="">Vyberte profil</option>
              {profiles.data.data.map((profile) => (
                <option
                  key={profile.id}
                  value={`${profile.id}:${profile.version}`}
                >
                  {profile.name} · v{profile.version}
                </option>
              ))}
            </select>
            {profiles.data.pagination.total > 200 && (
              <p className="field-help">Zobrazených je prvých 200 profilov.</p>
            )}
          </>
        )}
        {capabilities.data?.mode === "live" &&
          !capabilities.data.aiConfigured && (
            <p className="field-error">
              AI extrakcia nie je nakonfigurovaná. Kontaktujte správcu.
            </p>
          )}
        <div className="upload-actions">
          <button
            className="upload-text-button"
            disabled={launching || !readyIds.length}
            onClick={() => setSelected(readyIds)}
          >
            Vybrať pripravené
          </button>
          <Button
            disabled={
              !selected.length || !profileKey || !canExtract || launching
            }
            onClick={() => void launchExtraction()}
          >
            {launching
              ? "Pripravujeme…"
              : `Spustiť ${capabilities.data?.mode === "fixture" ? "ukážkovú extrakciu" : "extrakciu"} (${selected.length})`}
          </Button>
        </div>
        {actionError && (
          <p className="field-error" role="alert">
            {actionError}
          </p>
        )}
        {extractions.isError && (
          <p className="field-help">
            Odkazy na staršie návrhy sa nepodarilo načítať.{" "}
            <button
              className="upload-text-button"
              onClick={() => void extractions.refetch()}
            >
              Skúsiť znova
            </button>
          </p>
        )}
        {(extractions.data?.pagination.total ?? 0) > 200 && (
          <p className="field-help">Zobrazených je prvých 200 návrhov.</p>
        )}
      </section>
      {previewId && (
        <DocumentPreview
          key={previewId}
          id={previewId}
          search={search}
          onClose={() => {
            setSearch({});
            previewTrigger.current?.focus();
          }}
        />
      )}
    </section>
  );
}
