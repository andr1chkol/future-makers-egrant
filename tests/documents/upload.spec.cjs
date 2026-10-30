const {
  test,
  expect,
} = require("../../frontend/node_modules/@playwright/test");
const path = require("node:path");

test("real upload, partial rejection, source preview, retry, refresh and separate extraction links", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(page.getByText(/Zatiaľ tu nie sú/)).toBeVisible();
  await page.getByLabel("Vybrať dokumenty").setInputFiles([
    {
      name: "supporting-data.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("name,amount\nOriginal source,12.50\n"),
    },
    {
      name: "broken.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("not a pdf"),
    },
    {
      name: "other-data.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("title,value\nSeparate document,42\n"),
    },
  ]);
  await expect(page.getByRole("alert")).toContainText(
    "Obsah súboru nezodpovedá",
  );
  await expect(page.getByText("Pripravený", { exact: true })).toHaveCount(2, {
    timeout: 20000,
  });
  const accepted = page.getByRole("list", { name: "Prijaté dokumenty" });
  await accepted
    .getByRole("listitem")
    .filter({ hasText: "supporting-data.csv" })
    .getByRole("button", { name: "Náhľad", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Zdrojové údaje" }),
  ).toBeVisible();
  await expect(
    page.getByText("Original source,12.50", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Bunka", { exact: true }).fill("B2");
  await expect(
    page.getByText("Original source,12.50", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Zavrieť náhľad" }).click();
  await page.reload();
  await expect(page.getByText("Pripravený", { exact: true })).toHaveCount(2);
  await page
    .getByLabel("Extrakčný profil")
    .selectOption({ label: "Ukážková faktúra · v1" });
  await page.getByRole("button", { name: "Vybrať pripravené" }).click();
  await page
    .getByRole("button", { name: "Spustiť ukážkovú extrakciu (2)" })
    .click();
  const reviews = page.getByRole("link", { name: /Skontrolovať údaje/ });
  await expect(reviews).toHaveCount(2);
  const firstHref = await reviews.first().getAttribute("href");
  expect(await reviews.last().getAttribute("href")).not.toBe(firstHref);
  await page.reload();
  await expect(reviews).toHaveCount(2);
  await page.screenshot({
    path: path.resolve(__dirname, "../../.private/upload-desktop.png"),
    fullPage: true,
  });
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Vybrať súbory" }),
    ).toBeVisible();
  }
  await page.setViewportSize({ width: 375, height: 900 });
  await page.screenshot({
    path: path.resolve(__dirname, "../../.private/upload-mobile.png"),
    fullPage: true,
  });
  await reviews.first().click();
  await expect(page).toHaveURL(new RegExp(firstHref));
});

test("image OCR configuration failure remains visible across reload and retry", async ({
  page,
}) => {
  await page.goto("/documents");
  await page
    .getByLabel("Vybrať dokumenty")
    .setInputFiles(
      path.resolve(__dirname, "../../.private/browser-sample.png"),
    );
  const row = page
    .getByRole("list", { name: "Prijaté dokumenty" })
    .getByRole("listitem")
    .filter({ hasText: "browser-sample.png" });
  await expect(row.getByText(/OCR nie je nakonfigurované/)).toBeVisible({
    timeout: 20000,
  });
  await row.getByRole("button", { name: "Zopakovať spracovanie" }).click();
  await expect(row.getByText(/OCR nie je nakonfigurované/)).toBeVisible({
    timeout: 20000,
  });
  await page.reload();
  await expect(row.getByText(/OCR nie je nakonfigurované/)).toBeVisible();
});
