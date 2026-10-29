import { Button } from "../../shared/ui";
import { ValueInput } from "./ValueInput";
import {
  displayValue,
  sameValue,
  type Extraction,
  type Profile,
  type FormDefinition,
  type Snapshot,
  type Source,
  type Value,
} from "./model";

export function ReviewFields({
  extraction,
  profile,
  form,
  draft,
  setDraft,
  issuesOnly,
  onSource,
  warnings,
  readOnly,
}: {
  extraction: Extraction;
  profile: Profile;
  form: FormDefinition;
  draft: Snapshot;
  setDraft: (snapshot: Snapshot) => void;
  issuesOnly: boolean;
  onSource: (source: Source) => void;
  warnings: { id: string; warning: Extraction["warnings"][number] }[];
  readOnly: boolean;
}) {
  const setField = (key: string, value: Value) =>
    setDraft({
      ...draft,
      fields: draft.fields.map((field) =>
        field.key === key ? { ...field, value } : field,
      ),
    });
  const setCell = (
    tableKey: string,
    rowId: string,
    key: string,
    value: Value,
  ) =>
    setDraft({
      ...draft,
      tables: draft.tables.map((table) =>
        table.key !== tableKey
          ? table
          : {
              ...table,
              rows: table.rows.map((row) =>
                row.rowId !== rowId
                  ? row
                  : {
                      ...row,
                      cells: row.cells.map((cell) =>
                        cell.key === key ? { ...cell, value } : cell,
                      ),
                    },
              ),
            },
      ),
    });
  function sources(items: Source[]) {
    return items.length ? (
      <div className="review-source-links">
        {items.map((item, index) => (
          <button type="button" key={index} onClick={() => onSource(item)}>
            Zdroj {index + 1}
            {item.page
              ? ` · str. ${item.page}`
              : item.cell
                ? ` · ${item.cell}`
                : ""}
          </button>
        ))}
      </div>
    ) : (
      <small>Bez zdrojového odkazu</small>
    );
  }
  return (
    <>
      <h2>Údaje formulára</h2>
      {profile.scalarFields.length === 0 && (
        <p>Profil nemá samostatné polia.</p>
      )}
      {profile.scalarFields.map((definition) => {
        const field = draft.fields.find((item) => item.key === definition.key);
        const original = extraction.fields.find(
          (item) => item.key === definition.key,
        );
        if (!field) return null;
        const edited = !sameValue(field.value, original?.value ?? null);
        const missing = field.value === null || field.value === "";
        if (
          issuesOnly &&
          !missing &&
          !edited &&
          original?.status !== "needs_review" &&
          !warnings.some(({ warning }) => warning.fieldKey === field.key)
        )
          return null;
        return (
          <div className="review-field" key={field.key}>
            <label htmlFor={`field-${field.key}`}>
              {definition.label}
              {definition.required ? " *" : ""}
            </label>
            <p className="review-indicator">
              {edited
                ? "Upravené človekom"
                : missing
                  ? "Nenájdené"
                  : original?.status === "needs_review"
                    ? "Vyžaduje kontrolu"
                    : "Nájdené"}
            </p>
            <ValueInput
              disabled={readOnly}
              id={`field-${field.key}`}
              definition={definition}
              value={field.value}
              onChange={(value) => setField(field.key, value)}
              options={
                form.fields.find(
                  (target) => target.tag === definition.targetTag,
                )?.options
              }
            />
            <small>AI návrh: {displayValue(original?.value ?? null)}</small>
            {definition.type === "decimal" || definition.type === "money" ? (
              <small>Použite desatinnú bodku (napr. 2.00).</small>
            ) : null}
            {sources(original?.sources ?? [])}
          </div>
        );
      })}
      {profile.tableFields.map((definition) => {
        const table = draft.tables.find((item) => item.key === definition.key);
        const original = extraction.tables.find(
          (item) => item.key === definition.key,
        );
        if (!table) return null;
        return (
          <section className="review-table" key={table.key}>
            <h2>{definition.label}</h2>
            {table.rows.length === 0 && (
              <p>Tabuľka je prázdna. Môžete pridať riadok.</p>
            )}
            <div
              className="review-table-scroll"
              role="region"
              aria-label={definition.label}
              tabIndex={0}
            >
              <table>
                <thead>
                  <tr>
                    <th scope="col">Riadok</th>
                    {definition.columns.map((column) => (
                      <th scope="col" key={column.key}>
                        {column.label}
                        {column.required ? " *" : ""}
                      </th>
                    ))}
                    <th scope="col">Úpravy</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((row, rowIndex) => {
                    const originalRow = original?.rows.find(
                      (item) => item.rowId === row.rowId,
                    );
                    const issue =
                      !originalRow ||
                      row.cells.some(
                        (cell) =>
                          cell.value === null ||
                          !sameValue(
                            cell.value,
                            originalRow.cells.find(
                              (item) => item.key === cell.key,
                            )?.value ?? null,
                          ),
                      ) ||
                      originalRow.cells.some(
                        (cell) => cell.status === "needs_review",
                      ) ||
                      warnings.some(
                        ({ warning }) =>
                          warning.tableKey === table.key &&
                          (!warning.rowId || warning.rowId === row.rowId),
                      );
                    if (issuesOnly && !issue) return null;
                    return (
                      <tr key={row.rowId}>
                        <th scope="row">
                          {rowIndex + 1}
                          {!originalRow && <small>Pridaný človekom</small>}
                        </th>
                        {definition.columns.map((column) => {
                          const cell = row.cells.find(
                            (item) => item.key === column.key,
                          );
                          const proposed = originalRow?.cells.find(
                            (item) => item.key === column.key,
                          );
                          if (!cell)
                            return <td key={column.key}>Neplatná štruktúra</td>;
                          const id = `cell-${row.rowId}-${column.key}`;
                          return (
                            <td key={column.key}>
                              <label className="review-sr-only" htmlFor={id}>
                                {column.label}, riadok {rowIndex + 1}
                              </label>
                              <ValueInput
                                disabled={readOnly}
                                id={id}
                                definition={column}
                                value={cell.value}
                                onChange={(value) =>
                                  setCell(table.key, row.rowId, cell.key, value)
                                }
                                options={
                                  form.tables
                                    .find(
                                      (target) =>
                                        target.tag === definition.targetTag,
                                    )
                                    ?.columns.find(
                                      (target) =>
                                        target.tag === column.targetTag,
                                    )?.options
                                }
                              />
                              <small>
                                {!sameValue(cell.value, proposed?.value ?? null)
                                  ? "Upravené človekom · "
                                  : ""}
                                AI: {displayValue(proposed?.value ?? null)}
                              </small>
                              {sources(proposed?.sources ?? [])}
                            </td>
                          );
                        })}
                        <td>
                          <Button
                            disabled={readOnly}
                            type="button"
                            className="button review-secondary"
                            aria-label={`Odstrániť riadok ${rowIndex + 1} z ${definition.label}`}
                            onClick={() =>
                              setDraft({
                                ...draft,
                                tables: draft.tables.map((item) =>
                                  item.key === table.key
                                    ? {
                                        ...item,
                                        rows: item.rows.filter(
                                          (item) => item.rowId !== row.rowId,
                                        ),
                                      }
                                    : item,
                                ),
                              })
                            }
                          >
                            Odstrániť
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Button
              disabled={readOnly}
              type="button"
              onClick={() =>
                setDraft({
                  ...draft,
                  tables: draft.tables.map((item) =>
                    item.key === table.key
                      ? {
                          ...item,
                          rows: [
                            ...item.rows,
                            {
                              rowId: crypto.randomUUID(),
                              cells: definition.columns.map((column) => ({
                                key: column.key,
                                value: null,
                              })),
                            },
                          ],
                        }
                      : item,
                  ),
                })
              }
            >
              Pridať riadok do {definition.label}
            </Button>
          </section>
        );
      })}
      <section className="review-warnings">
        <h2>Upozornenia</h2>
        {warnings.length === 0 ? (
          <p>Bez upozornení zo spracovania.</p>
        ) : (
          warnings.map(({ warning, id }) => (
            <label className="review-check" key={id}>
              <input
                disabled={readOnly}
                type="checkbox"
                checked={draft.acknowledgedWarnings.includes(id)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    acknowledgedWarnings: event.target.checked
                      ? [...draft.acknowledgedWarnings, id]
                      : draft.acknowledgedWarnings.filter(
                          (item) => item !== id,
                        ),
                  })
                }
              />
              <span>Rozumiem upozorneniu: {warning.message}</span>
            </label>
          ))
        )}
      </section>
    </>
  );
}
