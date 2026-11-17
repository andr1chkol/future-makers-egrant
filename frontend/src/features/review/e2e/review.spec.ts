import { test, expect } from "@playwright/test";
import extraction from "../../../../../contracts/examples/extraction.json" with { type: "json" };

const route = `/review/${extraction.id}`;
const headers = { Origin: "http://localhost:5174" };

test.beforeEach(async ({ request }) => {
  const result = await request.post("/api/v1/__test/reset", { headers });
  expect(result.ok()).toBe(true);
});

test("real review API: edit sources/rows, persist, confirm and export human values", async ({
  page,
}) => {
  await page.goto(route);
  await expect(page.getByLabel("Dodávateľ *")).toHaveValue("Demo Paper s.r.o.");
  await expect(
    page.getByRole("button", { name: "Exportovať JSON" }),
  ).toHaveCount(0);
  await page.getByLabel("Dodávateľ *").fill("Human-reviewed supplier");
  await page.getByLabel("Celková suma — suma").fill("77.50");
  await page.getByRole("button", { name: "Pridať riadok do Položky" }).click();
  await page.getByLabel("Popis, riadok 3").fill("Human-added row");
  await page.getByLabel("Množstvo, riadok 3").fill("1.00");
  const row = page
    .getByRole("row")
    .filter({ has: page.getByLabel("Popis, riadok 3") });
  await row.getByLabel("Jednotková cena — suma").fill("22.50");
  await row.getByLabel("Jednotková cena — mena").fill("EUR");
  await row.getByLabel("Suma — suma", { exact: true }).fill("22.50");
  await row.getByLabel("Suma — mena", { exact: true }).fill("EUR");
  await page
    .getByRole("button", { name: /Zdroj 1/ })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Vybraný zdroj" }),
  ).toContainText("DEMO-2026-001");
  await page.getByRole("checkbox", { name: /Rozumiem upozorneniu/ }).check();
  await page.getByRole("button", { name: "Uložiť koncept" }).click();
  await expect(page.getByText("Koncept bol uložený.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Dodávateľ *")).toHaveValue(
    "Human-reviewed supplier",
  );
  await expect(page.getByLabel("Popis, riadok 3")).toHaveValue(
    "Human-added row",
  );
  await page.getByRole("button", { name: "Skontrolovať súhrn" }).click();
  await expect(
    page.getByRole("region", { name: "Záverečný súhrn" }),
  ).toContainText("Human-added row");
  await page
    .getByRole("button", { name: "Potvrdiť údaje", exact: true })
    .click();
  await expect(page.getByLabel("Dodávateľ *")).toBeDisabled();
  await expect(
    page.getByRole("button", { name: /Zdroj 1/ }).first(),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Exportovať JSON" }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Stiahnuť JSON" }).click();
  const file = await download;
  const stream = await file.createReadStream();
  let content = "";
  for await (const chunk of stream!) content += chunk.toString();
  const payload = JSON.parse(content);
  expect(
    payload.fields.find(
      (field: { targetTag: string }) => field.targetTag === "supplier",
    ).value,
  ).toBe("Human-reviewed supplier");
  expect(payload.tables[0].rows[2].values.description).toBe("Human-added row");
  await expect(
    page.getByText("Exportované — bez zápisu do eGrantu"),
  ).toBeVisible();
});

test("stale server revision preserves local corrections", async ({
  page,
  request,
}) => {
  await page.goto(route);
  await page.getByLabel("Dodávateľ *").fill("Unsaved local correction");
  const existing = await request.get(`/api/v1/reviews/${extraction.id}`);
  const review = (await existing.json()).data;
  const response = await request.put(`/api/v1/reviews/${extraction.id}`, {
    headers,
    data: {
      expectedRevision: review.revision,
      fields: review.fields,
      tables: review.tables,
      acknowledgedWarnings: review.acknowledgedWarnings,
    },
  });
  expect(response.ok()).toBe(true);
  await page.getByRole("button", { name: "Uložiť koncept" }).click();
  await expect(
    page.getByRole("heading", { name: "Na serveri je novšia revízia 1" }),
  ).toBeVisible();
  await expect(page.getByLabel("Dodávateľ *")).toHaveValue(
    "Unsaved local correction",
  );
  page.on("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Načítať uloženú verziu" }).click();
  await expect(page.getByLabel("Dodávateľ *")).toHaveValue(
    "Unsaved local correction",
  );
});

test("keyboard, issue filter and 375px layout stay usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(route);
  await expect(page.getByLabel("Dodávateľ *")).toBeVisible();
  await page
    .getByRole("checkbox", { name: "Iba položky vyžadujúce pozornosť" })
    .check();
  await expect(page.getByLabel("Objednávka")).toBeVisible();
  await expect(page.getByLabel("Dodávateľ *")).toHaveCount(0);
  await page.keyboard.press("Tab");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.screenshot({
    path: "../docs/release/review-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("checkbox", { name: "Iba položky vyžadujúce pozornosť" })
    .uncheck();
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "200%";
  });
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "";
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../docs/release/review-desktop.png",
    fullPage: true,
  });
});
