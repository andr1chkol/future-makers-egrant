import type { components } from "../../shared/api.generated";

export type FormDefinition = components["schemas"]["FormDefinition"];
export type FormField = components["schemas"]["FormField"];
export type Profile = components["schemas"]["Profile"];
export type ProfileDefinition = components["schemas"]["ProfileDefinition"];
export type ProfileField = components["schemas"]["ProfileField"];
export type ProfileTable = components["schemas"]["ProfileTable"];
export type FieldErrors = Record<string, string>;

export const starterKinds = {
  invoice: "Faktúra",
  receipt: "Pokladničný doklad",
  bank_statement: "Bankový výpis",
  contract: "Zmluva",
} as const;

export function availableKey(tag: string, existing: string[]): string {
  // Extraction keys are identifiers; destination tags remain untouched addresses.
  const cleaned = tag.replace(/[^A-Za-z0-9_-]/g, "_");
  const base = (
    /^[A-Za-z_]/.test(cleaned) ? cleaned : `field_${cleaned}`
  ).slice(0, 120);
  let key = base;
  for (let suffix = 2; existing.includes(key); suffix += 1)
    key = `${base}_${suffix}`;
  return key;
}

export function mappedField(
  field: FormField,
  existing: ProfileField[] = [],
): ProfileField {
  return {
    key: availableKey(
      field.tag,
      existing.map((candidate) => candidate.key),
    ),
    label: field.label,
    type: field.type,
    description: field.options?.length
      ? // Option labels can change; extraction must return the stable option keys.
        `Použite iba kľúče možností: ${field.options.map((option) => JSON.stringify(option.key)).join(", ")}.`
      : `Získajte údaj: ${field.label}. Ak údaj chýba, vráťte null.`,
    required: field.required,
    targetTag: field.tag,
  };
}

export function mappedFields(fields: FormField[]): ProfileField[] {
  const mapped: ProfileField[] = [];
  for (const field of fields) mapped.push(mappedField(field, mapped));
  return mapped;
}

export function createStarter(
  kind: keyof typeof starterKinds,
  form: FormDefinition,
): ProfileDefinition {
  const instructions = {
    invoice: {
      scalar: "Čítajte hlavičku faktúry a súhrn účtovaných súm.",
      column:
        "Jeden riadok predstavuje jednu fakturovanú položku; súhrny a DPH nevytvárajú samostatné položky.",
    },
    receipt: {
      scalar:
        "Čítajte identifikáciu predajcu, dátum a celkovú platbu z pokladničného dokladu.",
      column:
        "Jeden riadok predstavuje jednu zakúpenú položku; medzisúčty a platobné údaje vynechajte.",
    },
    bank_statement: {
      scalar:
        "Čítajte identifikáciu účtu a obdobie výpisu; nevymýšľajte chýbajúce údaje.",
      column:
        "Jeden riadok predstavuje jednu bankovú transakciu; zachovajte znamienko sumy a vynechajte zostatkové súhrny.",
    },
    contract: {
      scalar:
        "Čítajte zmluvné strany, číslo zmluvy a dohodnuté dátumy zo zmluvy.",
      column:
        "Jeden riadok predstavuje jednu zmluvnú položku alebo míľnik; návrhy a nepodpísané zmeny neprezentujte ako potvrdené podmienky.",
    },
  }[kind];
  const tables: ProfileTable[] = [];
  for (const table of form.tables)
    tables.push({
      key: availableKey(
        table.tag,
        tables.map((candidate) => candidate.key),
      ),
      label: table.label,
      targetTag: table.tag,
      writeMode: "append",
      columns: mappedFields(table.columns).map((column) => ({
        ...column,
        description: `${instructions.column} ${column.description}`,
      })),
    });
  return {
    name: `${starterKinds[kind]} · ${form.name}`,
    documentKind: kind,
    formId: form.id,
    scalarFields: mappedFields(form.fields).map((field) => ({
      ...field,
      description: `${instructions.scalar} ${field.description}`,
    })),
    tableFields: tables,
  };
}

export function validateProfile(
  profile: ProfileDefinition,
  form: FormDefinition,
): FieldErrors {
  const errors: FieldErrors = {};
  if (!profile.name.trim()) errors.name = "Zadajte názov profilu.";
  if (!profile.documentKind.trim())
    errors.documentKind = "Zadajte druh dokumentu.";
  if (!profile.scalarFields.length && !profile.tableFields.length) {
    errors.fields = "Vyberte aspoň jedno pole alebo tabuľku.";
  }
  function validateScope(
    fields: ProfileField[],
    destinations: FormField[],
    path: string,
  ) {
    fields.forEach((field, index) => {
      const prefix = `${path}.${index}`;
      if (!/^[A-Za-z_][A-Za-z0-9_-]{0,127}$/.test(field.key))
        errors[`${prefix}.key`] =
          "Kľúč môže mať najviac 128 znakov: písmená bez diakritiky, číslice, _ a -. Musí začínať písmenom alebo _.";
      if (
        fields.some(
          (other, otherIndex) =>
            otherIndex !== index && other.key === field.key,
        )
      ) {
        errors[`${prefix}.key`] = "Kľúč musí byť v tejto skupine jedinečný.";
      }
      if (!field.label.trim())
        errors[`${prefix}.label`] = "Zadajte názov poľa.";
      const target = destinations.find(
        (destination) => destination.tag === field.targetTag,
      );
      if (!target) errors[`${prefix}.targetTag`] = "Cieľové pole neexistuje.";
      else if (target.type !== field.type)
        errors[`${prefix}.type`] = "Typ sa nezhoduje s cieľovým poľom.";
      if (
        fields.some(
          (other, otherIndex) =>
            otherIndex !== index && other.targetTag === field.targetTag,
        )
      ) {
        errors[`${prefix}.targetTag`] =
          "Cieľové pole už používa iné mapovanie.";
      }
    });
  }
  validateScope(profile.scalarFields, form.fields, "scalarFields");
  profile.tableFields.forEach((table, index) => {
    const path = `tableFields.${index}`;
    if (!/^[A-Za-z_][A-Za-z0-9_-]{0,127}$/.test(table.key))
      errors[`${path}.key`] =
        "Zadajte platný kľúč tabuľky: najviac 128 znakov, písmená bez diakritiky, číslice, _ a -.";
    if (!table.label.trim()) errors[`${path}.label`] = "Zadajte názov tabuľky.";
    if (
      profile.tableFields.some(
        (other, otherIndex) => otherIndex !== index && other.key === table.key,
      )
    ) {
      errors[`${path}.key`] = "Kľúč tabuľky musí byť jedinečný.";
    }
    if (
      profile.tableFields.some(
        (other, otherIndex) =>
          otherIndex !== index && other.targetTag === table.targetTag,
      )
    ) {
      errors[`${path}.targetTag`] = "Cieľovú tabuľku už používa iné mapovanie.";
    }
    const destination = form.tables.find(
      (candidate) => candidate.tag === table.targetTag,
    );
    if (!destination)
      errors[`${path}.targetTag`] = "Cieľová tabuľka neexistuje.";
    if (!table.columns.length)
      errors[`${path}.columns`] = "Vyberte aspoň jeden stĺpec.";
    validateScope(table.columns, destination?.columns ?? [], `${path}.columns`);
  });
  return errors;
}

export function sectionLabels(
  original: Record<string, unknown>,
): Record<string, string> {
  const labels: Record<string, string> = Object.create(null);
  function visit(value: unknown, section: string, depth: number) {
    if (depth > 30 || value === null || typeof value !== "object") return;
    if (Array.isArray(value)) {
      value.forEach((entry) => visit(entry, section, depth + 1));
      return;
    }
    const node = value as Record<string, unknown>;
    if (typeof node.tag === "string" && section) labels[node.tag] = section;
    for (const key of ["fields", "tables", "sections", "children"]) {
      const nextSection = key === "sections" ? "" : section;
      if (key === "sections" && Array.isArray(node[key])) {
        node[key].forEach((entry) => {
          if (entry && typeof entry === "object") {
            const label =
              "label" in entry && typeof entry.label === "string"
                ? entry.label
                : "";
            visit(
              entry,
              [section, label].filter(Boolean).join(" / "),
              depth + 1,
            );
          }
        });
      } else visit(node[key], nextSection, depth + 1);
    }
  }
  visit(original, "", 0);
  return labels;
}

const validationMessages: Record<string, string> = {
  IMPORT_FORMAT_UNVERIFIED:
    "Tento formát importu nie je overený. Použite označený ilustračný formát.",
  INVALID_FORM_SHAPE: "JSON nemá podporovanú štruktúru formulára.",
  INVALID_JSON: "Definícia nie je platný JSON objekt.",
  IMPORT_TOO_DEEP: "Definícia obsahuje príliš veľa vnorených úrovní.",
  IMPORT_TOO_LARGE: "Definícia formulára je príliš veľká.",
  DUPLICATE_TAG:
    "Cieľová značka sa opakuje. Značky musia byť v príslušnej skupine jedinečné.",
  INVALID_TAG: "Cieľová značka nemá podporovaný formát.",
  INVALID_REQUIRED: "Povinnosť poľa musí byť hodnota true alebo false.",
  INVALID_OPTION: "Možnosť musí obsahovať platný kľúč a označenie.",
  DUPLICATE_OPTION_KEY:
    "Kľúč možnosti sa opakuje. Označenia možností nenahrádzajú ich kľúče.",
  UNSUPPORTED_FIELD_TYPE:
    "Tento typ poľa nepodporujeme. Pôvodný import nebol zmenený.",
  EMPTY_FORM: "Formulár musí obsahovať aspoň jedno pole alebo tabuľku.",
  EMPTY_TABLE: "Tabuľka musí obsahovať aspoň jeden stĺpec.",
  DESTINATION_NOT_FOUND:
    "Cieľová značka neexistuje v zvolenom formulári alebo tabuľke.",
  INCOMPATIBLE_TYPE: "Typ sa nezhoduje s cieľovým poľom.",
  INVALID_KEY:
    "Zadajte platný kľúč: písmeno alebo _, potom písmená bez diakritiky, číslice, _ alebo -, najviac 128 znakov.",
  INVALID_LABEL: "Zadajte platný názov poľa alebo tabuľky.",
  DUPLICATE_KEY: "Kľúč musí byť v tejto skupine jedinečný.",
  DUPLICATE_DESTINATION: "Cieľová značka už má priradené mapovanie.",
  DESCRIPTION_TOO_LONG: "Pokyny na extrakciu sú príliš dlhé. Skráťte ich.",
  EMPTY_PROFILE: "Vyberte aspoň jedno pole alebo tabuľku.",
  INVALID_DOCUMENT_KIND: "Zadajte platný druh dokumentu.",
};

export function errorMessage(code?: string) {
  if (code && Object.hasOwn(validationMessages, code))
    return validationMessages[code];
  switch (code) {
    case "CONFLICT":
      return "Niekto uložil novšiu verziu. Váš koncept ostal zachovaný. Otvorte aktuálnu verziu a porovnajte zmeny.";
    case "NOT_FOUND":
      return "Formulár, profil alebo požadovaná verzia neexistuje.";
    case "VALIDATION_ERROR":
      return "Skontrolujte nastavenia polí a cieľové značky.";
    case "FEATURE_UNAVAILABLE":
      return "Táto funkcia na serveri ešte nie je pripojená. Skúste to po dokončení integrácie.";
    case "UNAUTHENTICATED":
      return "Prístup vypršal. Prihláste sa znova.";
    default:
      return "Operácia sa nepodarila. Skontrolujte pripojenie a skúste znova.";
  }
}

export function validationErrors(
  details: Record<string, unknown> | null | undefined,
): FieldErrors {
  const errors: FieldErrors = {};
  if (!Array.isArray(details?.fields)) return errors;
  for (const issue of details.fields) {
    if (!issue || typeof issue !== "object" || typeof issue.path !== "string")
      continue;
    // The backend supplies paths and codes, never imported values or provider text.
    errors[issue.path] =
      typeof issue.code === "string" &&
      Object.hasOwn(validationMessages, issue.code)
        ? validationMessages[issue.code]
        : "Neplatné nastavenie. Skontrolujte kľúč, typ a cieľovú značku.";
  }
  return errors;
}
