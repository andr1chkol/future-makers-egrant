import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test("persists two distinct manager configurations through the real API and PostgreSQL", async ({
  page,
}, testInfo) => {
  // The test harness assembles the real profiles router with shared access and errors.
  // No forms/profile HTTP response is mocked; the extractor remains a visible 503 shell.
  const profiles: string[] = [];
  for (const [index, filename] of [
    "invoice-form.json",
    "travel-form.json",
  ].entries()) {
    const json = readFileSync(
      new URL(
        `../../../../../tests/profiles/examples/${filename}`,
        import.meta.url,
      ),
      "utf8",
    );
    const definition = JSON.parse(json);
    const firstTag = definition.sections[0].fields[0].tag;
    await page.goto("/profiles");
    await page
      .getByLabel("Názov formulára", { exact: true })
      .fill(`Browser integration ${index + 1}`);
    await page.getByLabel("Súbor JSON", { exact: true }).setInputFiles({
      name: filename,
      mimeType: "application/json",
      buffer: Buffer.from(json),
    });
    await expect(page.getByLabel("Definícia JSON")).toHaveValue(json);
    await page
      .getByRole("button", { name: "Importovať formulár", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Nastavenie profilu", exact: true }),
    ).toBeVisible();
    await page
      .getByLabel("Názov profilu", { exact: true })
      .fill(`Configured example ${index + 1}`);
    if (index === 1) {
      await page
        .getByRole("combobox", { name: "Zápis tabuľky 1", exact: true })
        .selectOption("replace");
      await expect(page.getByText(/Nahradenie môže odstrániť/)).toBeVisible();
    }
    await page
      .getByRole("button", { name: "Uložiť profil", exact: true })
      .click();
    await expect(
      page.getByText("Uložená verzia 1", { exact: true }),
    ).toBeVisible();
    const id = new URL(page.url()).pathname.split("/").at(-1)!;
    profiles.push(id);
    const v1 = await (
      await page.request.get(`/api/v1/profiles/${id}?version=1`)
    ).json();
    expect(v1.data.scalarFields[0].targetTag).toBe(firstTag);
    expect(
      v1.data.scalarFields.every((field: { key: string }) =>
        /^[A-Za-z_][A-Za-z0-9_-]{0,127}$/.test(field.key),
      ),
    ).toBe(true);
    const storedForm = await (
      await page.request.get(`/api/v1/forms/${v1.data.formId}`)
    ).json();
    expect(storedForm.data.originalJson).toEqual(definition);
    if (index === 1) {
      expect(v1.data.scalarFields[1].description).toContain('"rail"');
      expect(storedForm.data.fields[1].options).toEqual([
        { key: "rail", label: "Vlak" },
        { key: "air", label: "Lietadlo" },
      ]);
    }
    await page
      .getByLabel("Názov extrahovaného poľa 1", { exact: true })
      .fill("Upravené označenie");
    await page
      .getByRole("button", { name: "Uložiť novú verziu", exact: true })
      .click();
    await expect(
      page.getByText("Uložená verzia 2", { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByLabel("Názov extrahovaného poľa 1", { exact: true }),
    ).toHaveValue("Upravené označenie");
    await expect(
      page.getByLabel("Cieľová značka poľa 1", { exact: true }),
    ).toHaveValue(firstTag);
    await page.getByLabel("Zobrazená verzia").selectOption("1");
    await expect(
      page.getByLabel("Názov extrahovaného poľa 1", { exact: true }),
    ).toHaveValue(v1.data.scalarFields[0].label);
    await expect(
      page.getByLabel("Názov profilu", { exact: true }),
    ).toBeDisabled();
    const pinned = await (
      await page.request.get(`/api/v1/profiles/${id}?version=1`)
    ).json();
    expect(pinned).toEqual(v1);
    await page.getByLabel("Zobrazená verzia").selectOption("latest");
    await expect(
      page.getByLabel("Názov extrahovaného poľa 1", { exact: true }),
    ).toHaveValue("Upravené označenie");
    await expect(
      page.getByRole("button", { name: "Spustiť skúšku", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByText(/Nie je dostupný žiadny spracovaný dokument/),
    ).toBeVisible();
    if (index === 0) {
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.screenshot({
        path: testInfo.outputPath("egrant-profiles-desktop.png"),
        fullPage: true,
      });
      await page.setViewportSize({ width: 375, height: 900 });
      await page
        .getByLabel("Názov extrahovaného poľa 1", { exact: true })
        .scrollIntoViewIfNeeded();
      await page.screenshot({
        path: testInfo.outputPath("egrant-profiles-mobile.png"),
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.setViewportSize({ width: 1440, height: 1000 });
    }
  }
  const first = await (
    await page.request.get(`/api/v1/profiles/${profiles[0]}`)
  ).json();
  const second = await (
    await page.request.get(`/api/v1/profiles/${profiles[1]}`)
  ).json();
  expect(first.data.formId).not.toBe(second.data.formId);
  expect(first.data.tableFields[0].targetTag).toBe("invoice.items");
  expect(second.data.tableFields[0].targetTag).toBe("journeys");
  expect(second.data.tableFields[0].writeMode).toBe("replace");
});
