import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

test("production fixture flow: configure, upload, inspect, correct, confirm and download", async ({
  page,
}) => {
  const expectedScalarValues = {
    invoice_number: "DEMO-2026-001",
    supplier: "Human-reviewed supplier",
    issue_date: "2026-10-20",
    buyer: "Demo Grant Association",
    purchase_order: "HUMAN-PO-002",
    total: { amount: "60.00", currency: "EUR" },
  };
  const expectedRows = [
    {
      description: "Human-reviewed row 1",
      quantity: "3.00",
      unit_price: { amount: "10.00", currency: "EUR" },
      line_total: { amount: "30.00", currency: "EUR" },
    },
    {
      description: "Human-reviewed row 2",
      quantity: "3.00",
      unit_price: { amount: "10.00", currency: "EUR" },
      line_total: { amount: "30.00", currency: "EUR" },
    },
  ];
  const source = await readFile(
    resolve("../contracts/examples/form.json"),
    "utf8",
  );
  await page.goto("/profiles");
  await expect(
    page.getByText(/Ukážkový režim · Syntetické údaje/),
  ).toBeVisible();
  await page
    .getByLabel("Názov formulára", { exact: true })
    .fill("Full product fixture form");
  await page.getByLabel("Súbor JSON", { exact: true }).setInputFiles({
    name: "illustrative-form.json",
    mimeType: "application/json",
    buffer: Buffer.from(source),
  });
  await page
    .getByRole("button", { name: "Importovať formulár", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Nastavenie profilu", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Názov profilu", { exact: true })
    .fill("Full product invoice fixture");
  await page
    .getByRole("button", { name: "Uložiť profil", exact: true })
    .click();
  await expect(
    page.getByText("Uložená verzia 1", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/profiles\/[a-f0-9-]{36}$/);
  const profilePath = new URL(page.url()).pathname;
  const profileId = profilePath.split("/").at(-1)!;
  const profile = (
    await (await page.request.get(`/api/v1/profiles/${profileId}`)).json()
  ).data;
  const form = (
    await (await page.request.get(`/api/v1/forms/${profile.formId}`)).json()
  ).data;
  expect(form.originalJson).toEqual(JSON.parse(source));
  expect(form.isIllustrative).toBe(true);

  await page.goto("/documents");
  const uploaded = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/documents") &&
      response.request().method() === "POST",
  );
  await page
    .getByLabel("Vybrať dokumenty", { exact: true })
    .setInputFiles(resolve("../contracts/examples/synthetic-invoice.csv"));
  const upload = await uploaded;
  expect(upload.status()).toBe(201);
  const documentId = (await upload.json()).data[0].id;
  await expect(
    page.getByRole("list", { name: "Prijaté dokumenty" }),
  ).toContainText("Pripravený");
  const normalized = (
    await (
      await page.request.get(`/api/v1/documents/${documentId}/normalized`)
    ).json()
  ).data;
  expect(normalized.units).toHaveLength(23);
  expect(
    (await page.request.get(`/api/v1/documents/${documentId}/content`)).ok(),
  ).toBe(true);

  await page.goto(profilePath);
  await page
    .getByRole("combobox", { name: /Dokument na skúšku/ })
    .selectOption(documentId);
  const started = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/extractions") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Spustiť skúšku", exact: true })
    .click();
  const start = await started;
  expect(start.status(), await start.text()).toBe(202);
  const extractionId = (await start.json()).data.extractions[0].id;
  await expect(page).toHaveURL(new RegExp(`/review/${extractionId}$`));
  await expect(page.getByLabel("Dodávateľ *", { exact: true })).toHaveValue(
    "Demo Paper s.r.o.",
  );
  await page
    .getByRole("button", { name: /Zdroj 1/ })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Vybraný zdroj" }),
  ).toContainText("DEMO-2026-001");
  const extraction = (
    await (await page.request.get(`/api/v1/extractions/${extractionId}`)).json()
  ).data;
  expect(extraction.mode).toBe("fixture");
  expect(
    extraction.fields.find(
      (field: { key: string }) => field.key === "purchase_order",
    ).value,
  ).toBeNull();
  await expect(
    page.getByRole("button", { name: "Exportovať JSON", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Dodávateľ *", { exact: true })
    .fill("Human-reviewed supplier");
  await page.getByLabel("Objednávka", { exact: true }).fill("HUMAN-PO-002");
  await page.getByLabel("Celková suma — suma", { exact: true }).fill("60.00");
  for (const index of [1, 2]) {
    await page
      .getByLabel(`Popis, riadok ${index}`, { exact: true })
      .fill(`Human-reviewed row ${index}`);
    await page
      .getByLabel(`Množstvo, riadok ${index}`, { exact: true })
      .fill("3.00");
    const row = page.getByRole("row").filter({
      has: page.getByLabel(`Popis, riadok ${index}`, { exact: true }),
    });
    await row
      .getByLabel("Jednotková cena — suma", { exact: true })
      .fill("10.00");
    await row.getByLabel("Suma — suma", { exact: true }).fill("30.00");
  }
  for (const warning of await page
    .getByRole("checkbox", { name: /Rozumiem upozorneniu/ })
    .all()) {
    await warning.check();
  }
  await page
    .getByRole("button", { name: "Uložiť koncept", exact: true })
    .click();
  await expect(
    page.getByText("Koncept bol uložený.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Dodávateľ *", { exact: true })).toHaveValue(
    expectedScalarValues.supplier,
  );
  await expect(page.getByLabel("Objednávka", { exact: true })).toHaveValue(
    expectedScalarValues.purchase_order,
  );
  await expect(
    page.getByLabel("Celková suma — suma", { exact: true }),
  ).toHaveValue(expectedScalarValues.total.amount);
  await expect(
    page.getByLabel("Celková suma — mena", { exact: true }),
  ).toHaveValue(expectedScalarValues.total.currency);
  for (const [index, expected] of expectedRows.entries()) {
    await expect(
      page.getByLabel(`Popis, riadok ${index + 1}`, { exact: true }),
    ).toHaveValue(expected.description);
    await expect(
      page.getByLabel(`Množstvo, riadok ${index + 1}`, { exact: true }),
    ).toHaveValue(expected.quantity);
    const row = page.getByRole("row").filter({
      has: page.getByLabel(`Popis, riadok ${index + 1}`, { exact: true }),
    });
    await expect(
      row.getByLabel("Jednotková cena — suma", { exact: true }),
    ).toHaveValue(expected.unit_price.amount);
    await expect(
      row.getByLabel("Jednotková cena — mena", { exact: true }),
    ).toHaveValue(expected.unit_price.currency);
    await expect(row.getByLabel("Suma — suma", { exact: true })).toHaveValue(
      expected.line_total.amount,
    );
    await expect(row.getByLabel("Suma — mena", { exact: true })).toHaveValue(
      expected.line_total.currency,
    );
  }
  const draft = (
    await (await page.request.get(`/api/v1/reviews/${extractionId}`)).json()
  ).data;
  expect(draft.status).toBe("draft");
  expect(
    Object.fromEntries(
      draft.fields.map((field: { key: string; value: unknown }) => [
        field.key,
        field.value,
      ]),
    ),
  ).toEqual(expectedScalarValues);
  expect(draft.tables).toHaveLength(1);
  expect(
    draft.tables[0].rows.map(
      (row: { cells: { key: string; value: unknown }[] }) =>
        Object.fromEntries(row.cells.map((cell) => [cell.key, cell.value])),
    ),
  ).toEqual(expectedRows);
  await page
    .getByRole("button", { name: "Skontrolovať súhrn", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Záverečný súhrn" }),
  ).toContainText("Human-reviewed row 2");
  await page
    .getByRole("button", { name: "Potvrdiť údaje", exact: true })
    .click();
  await expect(page.getByLabel("Dodávateľ *", { exact: true })).toBeDisabled();
  await page
    .getByRole("button", { name: "Exportovať JSON", exact: true })
    .click();
  const downloaded = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Stiahnuť JSON", exact: true })
    .click();
  const download = await downloaded;
  const file = await download.path();
  expect(file).not.toBeNull();
  const payload = JSON.parse(await readFile(file!, "utf8"));
  expect(payload.formId).toBe(profile.formId);
  expect(payload.profileId).toBe(profileId);
  expect(payload.profileVersion).toBe(1);
  expect(payload.fields).toEqual(
    Object.entries(expectedScalarValues).map(([targetTag, value]) => ({
      targetTag,
      value,
    })),
  );
  expect(payload.tables).toEqual([
    {
      targetTag: "items",
      writeMode: "append",
      rows: expectedRows.map((values, index) => ({
        rowId: draft.tables[0].rows[index].rowId,
        values,
      })),
    },
  ]);
  await expect(
    page.getByText("Exportované — bez zápisu do eGrantu", { exact: true }),
  ).toBeVisible();
});
