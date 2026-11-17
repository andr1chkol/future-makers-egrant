import type { components } from "../../shared/api.generated";

export type Extraction = components["schemas"]["Extraction"];
export type Profile = components["schemas"]["Profile"];
export type FormDefinition = components["schemas"]["FormDefinition"];
export type Review = components["schemas"]["Review"];
export type Snapshot = Pick<
  Review,
  "fields" | "tables" | "acknowledgedWarnings"
>;
export type Value = Review["fields"][number]["value"];
export type Source = components["schemas"]["SourceRef"];
export type Definition = Profile["scalarFields"][number];
export type Option = components["schemas"]["Option"];
export type Submission = components["schemas"]["Submission"];

export class RequestError extends Error {
  constructor(public status: number) {
    super("Review request failed");
  }
}

export function dataOf<T>(result: {
  data?: { data: T };
  response: Response;
}): T {
  if (!result.data || !result.response.ok)
    throw new RequestError(result.response.status);
  return result.data.data;
}

export function errorText(error: unknown): string {
  if (error instanceof RequestError) {
    if (error.status === 409)
      return "Údaje sa medzičasom zmenili. Vaše úpravy zostali zachované. Načítajte a porovnajte uloženú verziu.";
    if (error.status === 422)
      return "Údaje nie sú platné. Skontrolujte typy, povinné hodnoty, možnosti výberu a upozornenia.";
    if (error.status === 503)
      return "Potrebná služba ešte nie je dostupná. Skúste to neskôr.";
    if (error.status === 401 || error.status === 403)
      return "Prístup vypršal alebo bol zamietnutý. Prihláste sa znova; predtým si uchovajte neuložené úpravy.";
    if (error.status === 404) return "Požadované spracovanie sa nenašlo.";
  }
  return "Server nie je dostupný. Úpravy zostali zachované. Skúste to znova.";
}

export function snapshotOf(review: Review): Snapshot {
  return JSON.parse(
    JSON.stringify({
      fields: review.fields,
      tables: review.tables,
      acknowledgedWarnings: review.acknowledgedWarnings,
    }),
  );
}

export function displayValue(value: Value): string {
  if (value === null) return "Nevyplnené";
  if (typeof value === "boolean") return value ? "Áno" : "Nie";
  if (typeof value === "object") return `${value.amount} ${value.currency}`;
  return value;
}

export function sameValue(a: Value, b: Value): boolean {
  return displayValue(a) === displayValue(b) && typeof a === typeof b;
}

export async function warningIdentity(
  warning: components["schemas"]["Warning"],
): Promise<string> {
  // Match Python's sorted, compact UTF-8 JSON including optional null locations.
  const canonical = JSON.stringify({
    code: warning.code,
    fieldKey: warning.fieldKey ?? null,
    message: warning.message,
    rowId: warning.rowId ?? null,
    tableKey: warning.tableKey ?? null,
  });
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(canonical),
  );
  return Array.from(new Uint8Array(hash), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}
