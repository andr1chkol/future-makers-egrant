import type { ReactNode } from "react";
import type { FieldErrors, FormField, ProfileField } from "./model";

export function Control({
  label,
  path,
  errors,
  children,
}: {
  label: string;
  path: string;
  errors: FieldErrors;
  children: ReactNode;
}) {
  return (
    <div className="profiles-control">
      <label htmlFor={path}>{label}</label>
      {children}
      {errors[path] && (
        <p id={`${path}-error`} className="field-error">
          {errors[path]}
        </p>
      )}
    </div>
  );
}

export function FieldEditor({
  field,
  destinations,
  path,
  index,
  errors,
  onChange,
}: {
  field: ProfileField;
  destinations: FormField[];
  path: string;
  index: number;
  errors: FieldErrors;
  onChange: (field: ProfileField) => void;
}) {
  const target = destinations.find(
    (destination) => destination.tag === field.targetTag,
  );
  const scopeLabel = path.startsWith("scalarFields")
    ? `poľa ${index + 1}`
    : `stĺpca ${index + 1} v tabuľke ${Number(path.split(".")[1]) + 1}`;
  const accessibleLabels = {
    key: `Kľúč extrahovaného ${scopeLabel}`,
    label: `Názov extrahovaného ${scopeLabel}`,
    type: `Typ extrahovaného ${scopeLabel}`,
    targetTag: `Cieľová značka ${scopeLabel}`,
    description: `Pokyny na extrakciu ${scopeLabel}`,
  };
  const attributes = (property: keyof typeof accessibleLabels) => ({
    "aria-label": accessibleLabels[property],
    id: `${path}.${property}`,
    "aria-invalid": !!errors[`${path}.${property}`],
    "aria-describedby": errors[`${path}.${property}`]
      ? `${path}.${property}-error`
      : undefined,
  });
  return (
    <div className="profiles-grid">
      <Control label="Kľúč" path={`${path}.key`} errors={errors}>
        <input
          {...attributes("key")}
          value={field.key}
          onChange={(event) => onChange({ ...field, key: event.target.value })}
        />
      </Control>
      <Control label="Názov" path={`${path}.label`} errors={errors}>
        <input
          {...attributes("label")}
          value={field.label}
          onChange={(event) =>
            onChange({ ...field, label: event.target.value })
          }
        />
      </Control>
      <Control label="Typ" path={`${path}.type`} errors={errors}>
        <select
          {...attributes("type")}
          value={field.type}
          onChange={(event) =>
            onChange({
              ...field,
              type: event.target.value as ProfileField["type"],
            })
          }
        >
          <option value="string">Text</option>
          <option value="decimal">Desatinné číslo</option>
          <option value="money">Peňažná suma</option>
          <option value="date">Dátum</option>
          <option value="boolean">Áno / nie</option>
        </select>
      </Control>
      <Control
        label="Cieľová značka"
        path={`${path}.targetTag`}
        errors={errors}
      >
        <select
          {...attributes("targetTag")}
          value={field.targetTag}
          onChange={(event) =>
            onChange({ ...field, targetTag: event.target.value })
          }
        >
          <option value="">Vyberte cieľ</option>
          {!target && field.targetTag && (
            <option value={field.targetTag}>
              {field.targetTag} · neexistuje
            </option>
          )}
          {destinations.map((destination) => (
            <option key={destination.tag} value={destination.tag}>
              {destination.label} · {destination.tag}
            </option>
          ))}
        </select>
      </Control>
      <Control
        label="Pokyny na extrakciu"
        path={`${path}.description`}
        errors={errors}
      >
        <textarea
          {...attributes("description")}
          rows={3}
          value={field.description}
          onChange={(event) =>
            onChange({ ...field, description: event.target.value })
          }
        />
      </Control>
      <div>
        <label className="profiles-check">
          <input
            type="checkbox"
            checked={field.required}
            onChange={(event) =>
              onChange({ ...field, required: event.target.checked })
            }
          />
          Povinný extrahovaný údaj
        </label>
        {target?.required && (
          <p className="field-help">Cieľové pole je vo formulári povinné.</p>
        )}
        {target?.options && (
          <p className="field-help">
            Povolené hodnoty (kľúč → označenie):{" "}
            {target.options
              .map(
                (option) => `${JSON.stringify(option.key)} → ${option.label}`,
              )
              .join("; ")}
            . Extrakcia musí vrátiť kľúč možnosti.
          </p>
        )}
      </div>
    </div>
  );
}
