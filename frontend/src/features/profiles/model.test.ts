import { describe, expect, test } from "vitest";
import type { components } from "../../shared/api.generated";
import { createStarter, validateProfile, sectionLabels } from "./model";

const form: components["schemas"]["FormDefinition"] = {
  id: "00000000-0000-4000-8000-000000000002",
  name: "Grant",
  isIllustrative: true,
  originalJson: {
    sections: [{ label: "Project", fields: [{ tag: "code" }] }],
    unknownSetting: { script: "<script>alert(1)</script>" },
  },
  fields: [
    {
      tag: "code",
      label: "Kód",
      type: "string",
      required: true,
      options: [{ key: "primary", label: "Hlavný" }],
    },
  ],
  tables: [
    {
      tag: "budget",
      label: "Rozpočet",
      columns: [
        {
          tag: "sum",
          label: "Suma",
          type: "money",
          required: true,
          options: null,
        },
      ],
    },
  ],
};

describe("profile configuration", () => {
  test.each(["invoice", "receipt", "bank_statement", "contract"] as const)(
    "creates editable %s configuration against the selected form",
    (kind) => {
      const profile = createStarter(kind, form);
      expect(profile.documentKind).toBe(kind);
      expect(profile.scalarFields[0].targetTag).toBe("code");
      expect(profile.tableFields[0].columns[0].targetTag).toBe("sum");
      expect(profile.scalarFields[0].description).toContain("primary");
      expect(profile.scalarFields[0].description).not.toContain("Hlavný");
      expect(validateProfile(profile, form)).toEqual({});
      expect(form.originalJson).toHaveProperty("unknownSetting");
    },
  );

  test("label edits retain destination tags", () => {
    const profile = createStarter("invoice", form);
    profile.scalarFields[0].label = "Renamed";
    expect(profile.scalarFields[0].targetTag).toBe("code");
    expect(profile.scalarFields[0].key).toBe("code");
  });

  test("rejects duplicate keys, missing destinations and incompatible column types", () => {
    const profile = createStarter("invoice", form);
    profile.scalarFields.push({
      ...profile.scalarFields[0],
      targetTag: "absent",
    });
    profile.tableFields[0].columns[0].type = "string";
    const errors = validateProfile(profile, form);
    expect(errors["scalarFields.1.key"]).toBeTruthy();
    expect(errors["scalarFields.1.targetTag"]).toBeTruthy();
    expect(errors["tableFields.0.columns.0.type"]).toBeTruthy();
  });

  test("never treats an option display label as a destination tag", () => {
    const profile = createStarter("invoice", form);
    profile.scalarFields[0].targetTag = "Hlavný";
    expect(
      validateProfile(profile, form)["scalarFields.0.targetTag"],
    ).toBeTruthy();
  });

  test("finds section context without evaluating imported text", () => {
    expect(sectionLabels(form.originalJson)).toEqual({ code: "Project" });
  });

  test("creates valid unique extraction keys independently of destination addresses", () => {
    const definition = {
      ...form,
      fields: ["1.tag", "1 tag", "1_tag"].map((tag) => ({
        ...form.fields[0],
        tag,
      })),
    };
    const profile = createStarter("contract", definition);
    expect(new Set(profile.scalarFields.map((field) => field.key)).size).toBe(
      3,
    );
    expect(
      profile.scalarFields.every((field) =>
        /^[A-Za-z_][A-Za-z0-9_-]{0,127}$/.test(field.key),
      ),
    ).toBe(true);
    expect(profile.scalarFields.map((field) => field.targetTag)).toEqual([
      "1.tag",
      "1 tag",
      "1_tag",
    ]);
    profile.scalarFields[0].key = "invalid.key";
    expect(
      validateProfile(profile, definition)["scalarFields.0.key"],
    ).toBeTruthy();
  });

  test("starter instructions distinguish document categories", () => {
    const invoice = createStarter("invoice", form);
    const contract = createStarter("contract", form);
    expect(invoice.scalarFields[0].description).not.toBe(
      contract.scalarFields[0].description,
    );
    expect(invoice.tableFields[0].columns[0].description).not.toBe(
      contract.tableFields[0].columns[0].description,
    );
  });
});
