import { test, expect } from "@playwright/test";

test("fixture banner persists across feature routes and narrow layouts", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(
    page.getByRole("heading", { name: "Nahrať dokumenty" }),
  ).toBeVisible();
  await expect(
    page.getByText("Ukážkový režim", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Vybrať súbory" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Profily", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Profily extrakcie" }),
  ).toBeVisible();
  await expect(
    page.getByText("Ukážkový režim", { exact: false }),
  ).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await expect(
    page.getByRole("link", { name: "Dokumenty", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../docs/release/foundation-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({
    path: "../docs/release/foundation-desktop.png",
    fullPage: true,
  });
});

test("keyboard skip link reaches content and scaled text stays readable", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(
    page.getByRole("heading", { name: "Nahrať dokumenty" }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Preskočiť na obsah" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [375, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    await expect(
      page.getByRole("heading", { name: "Nahrať dokumenty" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});

test("failed login links the inline error to the field and preserves focus", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/session", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "UNAUTHENTICATED",
          message: "Authentication required",
          details: null,
        },
      }),
    }),
  );
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "UNAUTHENTICATED",
          message: "Invalid access code",
          details: null,
        },
      }),
    }),
  );
  await page.goto("/documents");
  const field = page.getByLabel("Prístupový kód", { exact: true });
  await field.fill("test-only-invalid-code");
  await page.getByRole("button", { name: "Prihlásiť sa", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Prístupový kód nie je správny. Skúste ho zadať znova.",
  );
  await expect(field).toHaveAttribute("aria-invalid", "true");
  await expect(field).toHaveAttribute(
    "aria-describedby",
    "access-help access-error",
  );
  await expect(field).toBeFocused();
});
