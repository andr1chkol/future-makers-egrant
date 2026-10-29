import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { FileJson, Plus } from "lucide-react";
import { api } from "../../shared/api";
import { Button, Notice } from "../../shared/ui";
import { errorMessage, validationErrors } from "./model";
import { loadForms, loadProfiles } from "./data";
import "./profiles.css";

export { ProfileEditorPage } from "./ProfileEditorPage";

export function ProfilesPage() {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const forms = useQuery({ queryKey: ["forms"], queryFn: loadForms });
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: loadProfiles });
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [json, setJson] = useState("");
  const [importError, setImportError] = useState("");
  const [importing, setImporting] = useState(false);
  const query = search.toLocaleLowerCase("sk");

  async function importForm(event: FormEvent) {
    event.preventDefault();
    setImportError("");
    let definition: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(json);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
        throw new Error();
      definition = parsed as Record<string, unknown>;
    } catch {
      setImportError("Zadajte platný JSON objekt formulára.");
      return;
    }
    if (!name.trim()) {
      setImportError("Zadajte názov formulára.");
      return;
    }
    setImporting(true);
    try {
      const { data, error } = await api.POST("/api/v1/forms", {
        body: { name: name.trim(), definition },
      });
      if (error) {
        setImportError(
          Object.values(validationErrors(error.error.details))[0] ??
            errorMessage(error.error.code),
        );
        return;
      }
      await cache.invalidateQueries({ queryKey: ["forms"] });
      navigate(`/profiles/new?formId=${encodeURIComponent(data.data.id)}`);
    } catch {
      setImportError(errorMessage());
    } finally {
      setImporting(false);
    }
  }

  return (
    <section className="profiles-workspace">
      <p className="eyebrow">Nastavenie extrakcie</p>
      <h1>Profily extrakcie</h1>
      <p className="profiles-muted">
        Priraďte údaje z dokumentov k stabilným značkám formulára. Každé
        uloženie vytvorí samostatnú verziu profilu.
      </p>
      <Link className="button profiles-link" to="/profiles/new">
        <Plus size={18} aria-hidden="true" />
        Nový profil
      </Link>
      <div className="profiles-toolbar">
        <label className="profiles-control">
          Hľadať formulár alebo profil
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            type="search"
          />
        </label>
      </div>
      <h2>Formuláre</h2>
      {forms.isPending ? (
        <Notice>Načítavame formuláre…</Notice>
      ) : forms.isError ? (
        <p role="alert" className="field-error">
          {forms.error.message}
        </p>
      ) : (
        <ul>
          {forms.data
            .filter((form) =>
              `${form.name} ${form.fields.map((field) => `${field.label} ${field.tag}`).join(" ")} ${form.tables.map((table) => `${table.label} ${table.tag} ${table.columns.map((column) => `${column.label} ${column.tag}`).join(" ")}`).join(" ")}`
                .toLocaleLowerCase("sk")
                .includes(query),
            )
            .map((form) => (
              <li key={form.id} className="profiles-row">
                <div>
                  <strong>{form.name}</strong>
                  <p className="field-help">
                    {form.fields.length} polí · {form.tables.length} tabuliek
                    {form.isIllustrative ? " · Ilustračný formulár" : ""}
                  </p>
                </div>
                <Link
                  className="profiles-link"
                  to={`/profiles/new?formId=${encodeURIComponent(form.id)}`}
                >
                  Nastaviť profil
                </Link>
              </li>
            ))}
        </ul>
      )}
      {forms.data?.length === 0 && (
        <p>Zatiaľ nemáte formulár. Importujte jeho definíciu nižšie.</p>
      )}
      <h2>Uložené profily</h2>
      {profiles.isPending ? (
        <Notice>Načítavame profily…</Notice>
      ) : profiles.isError ? (
        <p role="alert" className="field-error">
          {profiles.error.message}
        </p>
      ) : (
        <ul>
          {profiles.data
            .filter((profile) =>
              `${profile.name} ${profile.documentKind}`
                .toLocaleLowerCase("sk")
                .includes(query),
            )
            .map((profile) => (
              <li key={profile.id} className="profiles-row">
                <Link className="profiles-link" to={`/profiles/${profile.id}`}>
                  {profile.name}
                </Link>
                <span>Verzia {profile.version}</span>
              </li>
            ))}
        </ul>
      )}
      {profiles.data?.length === 0 && (
        <p>Vytvorte prvý profil z importovaného formulára.</p>
      )}
      <details open>
        <summary>
          <FileJson size={18} aria-hidden="true" /> Import formulára
        </summary>
        <Notice>
          Podporovaný je ilustračný formát. Kompatibilita so skutočnými exportmi
          eGrantu zatiaľ nie je overená.
        </Notice>
        <p className="profiles-muted">
          Neznáme nastavenia a pôvodný JSON ostanú zachované. Text ani HTML z
          importu sa nespúšťajú.
        </p>
        <form onSubmit={importForm} noValidate>
          <label className="profiles-control">
            Názov formulára
            <input
              value={name}
              maxLength={200}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="profiles-control">
            Súbor JSON
            <input
              type="file"
              accept="application/json,.json"
              onChange={async (event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                if (file.size > 2_000_000) {
                  setImportError("Súbor JSON môže mať najviac 2 MB.");
                  return;
                }
                try {
                  setJson(await file.text());
                  setImportError("");
                  if (!name) setName(file.name.replace(/\.json$/i, ""));
                } catch {
                  setImportError("Súbor sa nepodarilo prečítať.");
                }
              }}
            />
          </label>
          <label className="profiles-control">
            Definícia JSON
            <textarea
              rows={9}
              value={json}
              onChange={(event) => setJson(event.target.value)}
              aria-invalid={!!importError}
              aria-describedby={importError ? "form-import-error" : undefined}
              spellCheck={false}
            />
          </label>
          {importError && (
            <p className="field-error" role="alert" id="form-import-error">
              {importError}
            </p>
          )}
          <Button type="submit" disabled={importing}>
            {importing ? "Importujeme…" : "Importovať formulár"}
          </Button>
        </form>
      </details>
    </section>
  );
}
