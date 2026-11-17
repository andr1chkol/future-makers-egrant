import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api } from "../../shared/api";
import { Button, Notice } from "../../shared/ui";
import { loadForms } from "./data";
import { Control, FieldEditor } from "./FieldEditor";
import { TrialRun } from "./TrialRun";
import { useUnsavedChanges } from "./useUnsavedChanges";
import {
  availableKey,
  createStarter,
  errorMessage,
  mappedField,
  mappedFields,
  sectionLabels,
  starterKinds,
  validateProfile,
  validationErrors,
  type FieldErrors,
  type Profile,
  type ProfileDefinition,
} from "./model";

export function ProfileEditorPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const version = params.get("version");
  return (
    <ProfileEditor
      key={`${id ?? "new"}:${version ?? "latest"}`}
      id={id}
      version={version}
      initialFormId={params.get("formId")}
    />
  );
}

function ProfileEditor({
  id,
  version,
  initialFormId,
}: {
  id?: string;
  version: string | null;
  initialFormId: string | null;
}) {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const forms = useQuery({ queryKey: ["forms"], queryFn: loadForms });
  const existing = useQuery({
    queryKey: ["profile", id, version],
    enabled: !!id,
    queryFn: async () => {
      const number = version === null ? undefined : Number(version);
      if (number !== undefined && (!Number.isInteger(number) || number < 1))
        throw new Error("Zadajte platné číslo verzie.");
      const { data, error } = await api.GET("/api/v1/profiles/{id}", {
        params: {
          path: { id: id! },
          query: number === undefined ? {} : { version: number },
        },
      });
      if (error) throw new Error(errorMessage(error.error.code));
      return data.data;
    },
  });
  const latest = useQuery({
    queryKey: ["profile-latest", id],
    enabled: !!id && version !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/profiles/{id}", {
        params: { path: { id: id! } },
      });
      if (error) throw new Error(errorMessage(error.error.code));
      return data.data;
    },
  });
  const [draft, setDraft] = useState<ProfileDefinition | null>(null);
  const [saved, setSaved] = useState<Profile | null>(null);
  const [baseline, setBaseline] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [starterKind, setStarterKind] =
    useState<keyof typeof starterKinds>("invoice");
  const dirty = draft !== null && JSON.stringify(draft) !== baseline;
  const historical = version !== null;
  useUnsavedChanges(dirty);

  useEffect(() => {
    if (draft || !forms.data) return;
    if (id) {
      if (!existing.data || existing.isFetching) return;
      const { id: _id, version: _version, ...definition } = existing.data;
      setSaved(existing.data);
      setDraft(definition);
      setBaseline(JSON.stringify(definition));
    } else {
      const form =
        forms.data.find((candidate) => candidate.id === initialFormId) ??
        forms.data[0];
      if (!form) return;
      const definition = createStarter("invoice", form);
      setDraft(definition);
      setBaseline(JSON.stringify(definition));
    }
  }, [
    draft,
    forms.data,
    existing.data,
    existing.isFetching,
    id,
    initialFormId,
  ]);

  const form = forms.data?.find((candidate) => candidate.id === draft?.formId);
  function update(next: ProfileDefinition) {
    setDraft(next);
    setErrors({});
    setSaveError("");
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!draft || !form || historical) return;
    const failures = validateProfile(draft, form);
    setErrors(failures);
    setSaveError("");
    if (Object.keys(failures).length) return;
    setSaving(true);
    try {
      // Every write creates a new snapshot; an existing version is never overwritten.
      const response = saved
        ? await api.POST("/api/v1/profiles/{id}/versions", {
            params: { path: { id: saved.id } },
            body: { ...draft, expectedVersion: saved.version },
          })
        : await api.POST("/api/v1/profiles", { body: draft });
      if (response.error) {
        setErrors(validationErrors(response.error.error.details));
        setSaveError(errorMessage(response.error.error.code));
        return;
      }
      const profile = response.data.data;
      const { id: _id, version: _version, ...definition } = profile;
      setSaved(profile);
      setDraft(definition);
      setBaseline(JSON.stringify(definition));
      await cache.invalidateQueries({ queryKey: ["profiles"] });
      if (!id) {
        cache.setQueryData(["profile", profile.id, null], profile);
        navigate(`/profiles/${profile.id}`, { replace: true });
      }
    } catch {
      setSaveError(errorMessage());
    } finally {
      setSaving(false);
    }
  }

  if (forms.isPending || (id && existing.isPending))
    return <Notice>Načítavame nastavenie profilu…</Notice>;
  if (forms.isError || existing.isError)
    return (
      <section className="profiles-workspace">
        <h1>Nastavenie profilu</h1>
        <p className="field-error" role="alert">
          {forms.error?.message ?? existing.error?.message}
        </p>
        <Link className="profiles-link" to="/profiles">
          Späť na profily
        </Link>
      </section>
    );
  if (!forms.data?.length)
    return (
      <section className="profiles-workspace">
        <h1>Nastavenie profilu</h1>
        <Notice>Najprv importujte definíciu formulára.</Notice>
        <Link className="profiles-link" to="/profiles">
          Importovať formulár
        </Link>
      </section>
    );
  if (!draft) return <Notice>Pripravujeme nastavenie…</Notice>;
  const sections = form ? sectionLabels(form.originalJson) : {};
  const maximumVersion = Math.max(
    saved?.version ?? 1,
    latest.data?.version ?? 1,
  );
  const visibleFields =
    form?.fields.filter((field) =>
      `${field.label} ${field.tag} ${sections[field.tag] ?? ""}`
        .toLocaleLowerCase("sk")
        .includes(search.toLocaleLowerCase("sk")),
    ) ?? [];

  return (
    <section className="profiles-workspace">
      <Link className="profiles-link" to="/profiles">
        ← Profily a formuláre
      </Link>
      <h1>Nastavenie profilu</h1>
      <p className="profiles-status" role="status">
        {dirty
          ? "Neuložené zmeny"
          : saved
            ? `Uložená verzia ${saved.version}`
            : "Nový profil"}
      </p>
      {saved && (
        <div className="profiles-toolbar">
          <label className="profiles-control">
            Zobrazená verzia
            <select
              value={historical ? String(saved.version) : "latest"}
              onChange={(event) => {
                if (
                  dirty &&
                  !window.confirm("Máte neuložené zmeny. Chcete ich zahodiť?")
                )
                  return;
                navigate(
                  event.target.value === "latest"
                    ? `/profiles/${saved.id}`
                    : `/profiles/${saved.id}?version=${event.target.value}`,
                );
              }}
            >
              <option value="latest">Najnovšia verzia</option>
              {Array.from({ length: maximumVersion }, (_, index) => (
                <option key={index + 1} value={String(index + 1)}>
                  Verzia {index + 1}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {historical && (
        <Notice>
          Historická verzia je nemenná. Na úpravy otvorte najnovšiu verziu
          profilu.
        </Notice>
      )}
      {latest.isError && (
        <p className="field-error" role="alert">
          Stav najnovšej verzie sa nepodarilo načítať.
        </p>
      )}
      <form onSubmit={save} noValidate>
        <fieldset disabled={historical || saving}>
          <div className="profiles-grid">
            <Control label="Názov profilu" path="name" errors={errors}>
              <input
                id="name"
                value={draft.name}
                maxLength={200}
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? "name-error" : undefined}
                onChange={(event) =>
                  update({ ...draft, name: event.target.value })
                }
              />
            </Control>
            <Control label="Druh dokumentu" path="documentKind" errors={errors}>
              <input
                id="documentKind"
                value={draft.documentKind}
                aria-invalid={!!errors.documentKind}
                onChange={(event) =>
                  update({ ...draft, documentKind: event.target.value })
                }
              />
            </Control>
            <label className="profiles-control">
              Cieľový formulár
              <select
                value={draft.formId}
                onChange={(event) => {
                  if (
                    dirty &&
                    !window.confirm(
                      "Zmena formulára vytvorí nové mapovanie. Zahodiť aktuálne zmeny?",
                    )
                  )
                    return;
                  const next = forms.data?.find(
                    (candidate) => candidate.id === event.target.value,
                  );
                  if (next) update(createStarter(starterKind, next));
                }}
              >
                {forms.data.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="profiles-toolbar">
            <label className="profiles-control">
              Vzorový profil
              <select
                value={starterKind}
                onChange={(event) =>
                  setStarterKind(
                    event.target.value as keyof typeof starterKinds,
                  )
                }
              >
                {Object.entries(starterKinds).map(([key, label]) => (
                  <option value={key} key={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <Button
              type="button"
              onClick={() => {
                if (
                  !form ||
                  (dirty &&
                    !window.confirm("Použiť vzor a zahodiť aktuálne zmeny?"))
                )
                  return;
                update(createStarter(starterKind, form));
              }}
            >
              Použiť vzor
            </Button>
          </div>
          <p className="profiles-muted">
            Vzory sú upraviteľné príklady konfigurácie. Presnosť extrakcie
            týchto kategórií zatiaľ nebola overená. Značky cieľov sa pri zmene
            názvov nemenia.
          </p>
          {!form ? (
            <p role="alert" className="field-error">
              Cieľový formulár nie je dostupný. Pred uložením vyberte dostupný
              formulár.
            </p>
          ) : (
            <>
              {form.isIllustrative && (
                <Notice>
                  Ilustračný formulár · kompatibilita s reálnym exportom eGrantu
                  nie je overená.
                </Notice>
              )}
              <label className="profiles-control">
                Hľadať pole alebo tabuľku
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </label>
              <h2>Polia formulára</h2>
              {visibleFields.map((destination) => {
                const index = draft.scalarFields.findIndex(
                  (field) => field.targetTag === destination.tag,
                );
                return (
                  <label className="profiles-check" key={destination.tag}>
                    <input
                      type="checkbox"
                      checked={index >= 0}
                      onChange={(event) =>
                        update({
                          ...draft,
                          scalarFields: event.target.checked
                            ? [
                                ...draft.scalarFields,
                                mappedField(destination, draft.scalarFields),
                              ]
                            : draft.scalarFields.filter(
                                (_, fieldIndex) => fieldIndex !== index,
                              ),
                        })
                      }
                    />
                    <span>
                      {sections[destination.tag] &&
                        `${sections[destination.tag]} / `}
                      {destination.label} · <code>{destination.tag}</code>
                      {destination.required ? " · povinné" : ""}
                    </span>
                  </label>
                );
              })}
              {errors.fields && (
                <p className="field-error" role="alert">
                  {errors.fields}
                </p>
              )}
              {draft.scalarFields.map((field, index) => (
                <fieldset key={index}>
                  <legend>{field.label || `Pole ${index + 1}`}</legend>
                  <FieldEditor
                    field={field}
                    index={index}
                    destinations={form.fields}
                    path={`scalarFields.${index}`}
                    errors={errors}
                    onChange={(next) =>
                      update({
                        ...draft,
                        scalarFields: draft.scalarFields.map(
                          (candidate, fieldIndex) =>
                            fieldIndex === index ? next : candidate,
                        ),
                      })
                    }
                  />
                </fieldset>
              ))}
              <h2>Tabuľky a stĺpce</h2>
              {form.tables
                .filter((table) =>
                  `${table.label} ${table.tag} ${sections[table.tag] ?? ""} ${table.columns.map((column) => `${column.label} ${column.tag}`).join(" ")}`
                    .toLocaleLowerCase("sk")
                    .includes(search.toLocaleLowerCase("sk")),
                )
                .map((destination) => (
                  <label key={destination.tag} className="profiles-check">
                    <input
                      type="checkbox"
                      checked={draft.tableFields.some(
                        (table) => table.targetTag === destination.tag,
                      )}
                      onChange={(event) =>
                        update({
                          ...draft,
                          tableFields: event.target.checked
                            ? [
                                ...draft.tableFields,
                                {
                                  key: availableKey(
                                    destination.tag,
                                    draft.tableFields.map(
                                      (candidate) => candidate.key,
                                    ),
                                  ),
                                  label: destination.label,
                                  targetTag: destination.tag,
                                  writeMode: "append",
                                  columns: mappedFields(destination.columns),
                                },
                              ]
                            : draft.tableFields.filter(
                                (table) => table.targetTag !== destination.tag,
                              ),
                        })
                      }
                    />
                    {destination.label} · <code>{destination.tag}</code>
                  </label>
                ))}
              {draft.tableFields.map((table, tableIndex) => {
                const path = `tableFields.${tableIndex}`;
                const destination = form.tables.find(
                  (candidate) => candidate.tag === table.targetTag,
                );
                const updateTable = (next: typeof table) =>
                  update({
                    ...draft,
                    tableFields: draft.tableFields.map((candidate, index) =>
                      index === tableIndex ? next : candidate,
                    ),
                  });
                return (
                  <fieldset key={tableIndex}>
                    <legend>
                      {table.label || `Tabuľka ${tableIndex + 1}`}
                    </legend>
                    <div className="profiles-grid">
                      <Control
                        label={`Kľúč tabuľky ${tableIndex + 1}`}
                        path={`${path}.key`}
                        errors={errors}
                      >
                        <input
                          id={`${path}.key`}
                          value={table.key}
                          aria-invalid={!!errors[`${path}.key`]}
                          onChange={(event) =>
                            updateTable({ ...table, key: event.target.value })
                          }
                        />
                      </Control>
                      <Control
                        label={`Názov tabuľky ${tableIndex + 1}`}
                        path={`${path}.label`}
                        errors={errors}
                      >
                        <input
                          id={`${path}.label`}
                          value={table.label}
                          onChange={(event) =>
                            updateTable({ ...table, label: event.target.value })
                          }
                        />
                      </Control>
                      <Control
                        label={`Cieľová značka tabuľky ${tableIndex + 1}`}
                        path={`${path}.targetTag`}
                        errors={errors}
                      >
                        <select
                          id={`${path}.targetTag`}
                          value={table.targetTag}
                          aria-invalid={!!errors[`${path}.targetTag`]}
                          onChange={(event) =>
                            updateTable({
                              ...table,
                              targetTag: event.target.value,
                            })
                          }
                        >
                          <option value="">Vyberte tabuľku</option>
                          {form.tables.map((candidate) => (
                            <option key={candidate.tag} value={candidate.tag}>
                              {candidate.label} · {candidate.tag}
                            </option>
                          ))}
                        </select>
                      </Control>
                      <label className="profiles-control">
                        {`Zápis tabuľky ${tableIndex + 1}`}
                        <select
                          value={table.writeMode}
                          onChange={(event) =>
                            updateTable({
                              ...table,
                              writeMode: event.target.value as
                                "append" | "replace",
                            })
                          }
                        >
                          <option value="append">Pridať riadky</option>
                          <option value="replace">Nahradiť riadky</option>
                        </select>
                      </label>
                    </div>
                    {table.writeMode === "replace" && (
                      <Notice>
                        Nahradenie môže odstrániť existujúce riadky. Pri
                        odoslaní do eGrantu bude potrebný náhľad a výslovné
                        potvrdenie.
                      </Notice>
                    )}
                    {destination?.columns.map((column) => (
                      <label className="profiles-check" key={column.tag}>
                        <input
                          type="checkbox"
                          checked={table.columns.some(
                            (candidate) => candidate.targetTag === column.tag,
                          )}
                          onChange={(event) =>
                            updateTable({
                              ...table,
                              columns: event.target.checked
                                ? [
                                    ...table.columns,
                                    mappedField(column, table.columns),
                                  ]
                                : table.columns.filter(
                                    (candidate) =>
                                      candidate.targetTag !== column.tag,
                                  ),
                            })
                          }
                        />
                        {column.label} · <code>{column.tag}</code>
                      </label>
                    ))}
                    {errors[`${path}.columns`] && (
                      <p className="field-error">{errors[`${path}.columns`]}</p>
                    )}
                    {table.columns.map((column, index) => (
                      <fieldset key={index}>
                        <legend>{column.label || `Stĺpec ${index + 1}`}</legend>
                        <FieldEditor
                          field={column}
                          index={index}
                          destinations={destination?.columns ?? []}
                          path={`${path}.columns.${index}`}
                          errors={errors}
                          onChange={(next) =>
                            updateTable({
                              ...table,
                              columns: table.columns.map(
                                (candidate, columnIndex) =>
                                  columnIndex === index ? next : candidate,
                              ),
                            })
                          }
                        />
                      </fieldset>
                    ))}
                  </fieldset>
                );
              })}
            </>
          )}
        </fieldset>
        {saveError && (
          <p role="alert" className="field-error">
            {saveError}
          </p>
        )}
        {Object.keys(errors).length > 0 && (
          <p role="alert" className="field-error">
            Opravte označené nastavenia pred uložením.
          </p>
        )}
        {!historical && (
          <Button type="submit" disabled={saving || !form}>
            {saving
              ? "Ukladáme…"
              : saved
                ? "Uložiť novú verziu"
                : "Uložiť profil"}
          </Button>
        )}
      </form>
      {form && (
        <details>
          <summary>Pôvodná definícia a nepodporované nastavenia</summary>
          <p className="profiles-muted">
            Pôvodný JSON ostáva uložený bez zmien vrátane neznámych nastavení.
            Editor upravuje iba mapovanie profilu; podmienky viditeľnosti a iné
            pravidlá formulára tu nemožno meniť.
          </p>
          <pre className="profiles-source">
            {JSON.stringify(form.originalJson, null, 2)}
          </pre>
        </details>
      )}
      {dirty && (
        <Button
          type="button"
          disabled={saving}
          onClick={() => {
            if (window.confirm("Zahodiť neuložené zmeny profilu?")) {
              setDraft(JSON.parse(baseline) as ProfileDefinition);
              setErrors({});
              setSaveError("");
            }
          }}
        >
          Zahodiť zmeny
        </Button>
      )}
      {saved && <TrialRun profile={saved} dirty={dirty} />}
    </section>
  );
}
