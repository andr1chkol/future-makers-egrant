import type { Definition, Option, Value } from "./model";

export function ValueInput({
  definition,
  value,
  onChange,
  id,
  options,
  disabled = false,
}: {
  definition: Definition;
  value: Value;
  onChange: (value: Value) => void;
  id: string;
  options?: Option[] | null;
  disabled?: boolean;
}) {
  if (options)
    return (
      <select
        disabled={disabled}
        id={id}
        value={value === null ? "" : `v:${String(value)}`}
        onChange={(event) =>
          onChange(
            event.target.value === "" ? null : event.target.value.slice(2),
          )
        }
      >
        <option value="">Nevyplnené</option>
        {options.map((option) => (
          <option key={option.key} value={`v:${option.key}`}>
            {option.label}
          </option>
        ))}
      </select>
    );
  if (definition.type === "boolean")
    return (
      <select
        disabled={disabled}
        id={id}
        value={value === null ? "" : String(value)}
        onChange={(event) =>
          onChange(
            event.target.value === "" ? null : event.target.value === "true",
          )
        }
      >
        <option value="">Nevyplnené</option>
        <option value="true">Áno</option>
        <option value="false">Nie</option>
      </select>
    );
  if (definition.type === "money") {
    const money =
      value !== null && typeof value === "object"
        ? value
        : { amount: "", currency: "" };
    return (
      <div className="review-money">
        <input
          disabled={disabled}
          id={id}
          aria-label={`${definition.label} — suma`}
          inputMode="decimal"
          value={money.amount}
          pattern="-?(0|[1-9][0-9]*)\.[0-9]+"
          placeholder="0.00"
          onChange={(event) =>
            onChange(
              event.target.value === ""
                ? null
                : { ...money, amount: event.target.value },
            )
          }
        />
        <input
          disabled={disabled}
          aria-label={`${definition.label} — mena`}
          value={money.currency}
          pattern="[A-Z]{3}"
          maxLength={3}
          placeholder="Mena"
          required={value !== null}
          onChange={(event) =>
            onChange({ ...money, currency: event.target.value })
          }
        />
      </div>
    );
  }
  return (
    <input
      disabled={disabled}
      id={id}
      value={typeof value === "string" ? value : ""}
      type={definition.type === "date" ? "date" : "text"}
      inputMode={definition.type === "decimal" ? "decimal" : undefined}
      pattern={
        definition.type === "decimal" ? "-?(0|[1-9][0-9]*)\.[0-9]+" : undefined
      }
      onChange={(event) =>
        onChange(event.target.value === "" ? null : event.target.value)
      }
    />
  );
}
