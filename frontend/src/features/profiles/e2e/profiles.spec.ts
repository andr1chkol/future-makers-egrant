import { expect, test } from "@playwright/test";

test("manager configures two illustrative forms and launches the saved version", async ({
  page,
}) => {
  // This browser scenario mocks domain HTTP responses; PostgreSQL is covered separately.
  const forms: Record<string, unknown>[] = [];
  const profiles: Record<string, unknown>[] = [];
  let submittedVersion: unknown;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    const body = request.method() === "POST" ? request.postDataJSON() : null;
    if (path === "/auth/session")
      return route.fulfill({
        json: { data: { authenticated: true, mode: "fixture" } },
      });
    if (path === "/capabilities")
      return route.fulfill({
        json: {
          data: {
            mode: "fixture",
            aiConfigured: false,
            ocrConfigured: false,
            egrantConfigured: false,
          },
        },
      });
    if (path === "/forms" && body) {
      const form = {
        ...body.definition,
        id: `00000000-0000-4000-8000-00000000000${forms.length + 1}`,
        name: body.name,
        isIllustrative: true,
        originalJson: body.definition,
      };
      forms.push(form);
      return route.fulfill({ status: 201, json: { data: form } });
    }
    if (path === "/forms")
      return route.fulfill({
        json: {
          data: forms,
          pagination: { limit: 200, offset: 0, total: forms.length },
        },
      });
    if (path === "/profiles" && body) {
      const profile = {
        ...body,
        id: `00000000-0000-4000-8000-00000000001${profiles.length + 1}`,
        version: 1,
      };
      profiles.push(profile);
      return route.fulfill({ status: 201, json: { data: profile } });
    }
    if (path === "/profiles")
      return route.fulfill({
        json: {
          data: profiles,
          pagination: { limit: 200, offset: 0, total: profiles.length },
        },
      });
    if (path.startsWith("/profiles/"))
      return route.fulfill({
        json: {
          data: profiles.find((profile) => path === `/profiles/${profile.id}`),
        },
      });
    if (path === "/documents")
      return route.fulfill({
        json: {
          data: [
            {
              id: "00000000-0000-4000-8000-000000000099",
              filename: "synthetic.csv",
              status: "ready",
              mediaType: "text/csv",
            },
          ],
          pagination: { limit: 200, offset: 0, total: 1 },
        },
      });
    if (path === "/extractions") {
      submittedVersion = body;
      return route.fulfill({
        status: 202,
        json: {
          data: {
            extractions: [
              {
                id: "00000000-0000-4000-8000-000000000098",
                documentId: body.documentIds[0],
                status: "queued",
              },
            ],
          },
        },
      });
    }
    return route.fulfill({
      status: 503,
      json: {
        error: {
          code: "FEATURE_UNAVAILABLE",
          message: "Unavailable",
          details: null,
        },
      },
    });
  });

  for (const [index, tags] of [
    ["project_reference", "costs", "gross"],
    ["contract_reference", "milestones", "payment"],
  ].entries()) {
    await page.goto("/profiles");
    await page
      .getByLabel("Názov formulára", { exact: true })
      .fill(`Grant ${index + 1}`);
    const definition = JSON.stringify({
      illustrative: true,
      unknownSetting: { html: "<script>window.hostileImport=true</script>" },
      fields: [
        {
          tag: tags[0],
          label: "Referencia",
          type: "string",
          required: true,
          options: null,
        },
      ],
      tables: [
        {
          tag: tags[1],
          label: "Rozpočet",
          columns: [
            {
              tag: tags[2],
              label: "Suma",
              type: "money",
              required: true,
              options: null,
            },
          ],
        },
      ],
    });
    if (index === 0) {
      await page.getByLabel("Súbor JSON", { exact: true }).setInputFiles({
        name: "illustrative-form.json",
        mimeType: "application/json",
        buffer: Buffer.from(definition),
      });
      await expect(page.getByLabel("Definícia JSON")).toHaveValue(definition);
    } else await page.getByLabel("Definícia JSON").fill(definition);
    await page
      .getByRole("button", { name: "Importovať formulár", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Nastavenie profilu" }),
    ).toBeVisible();
    await page
      .getByLabel("Názov extrahovaného poľa 1", { exact: true })
      .fill(`Referencia ${index + 1}`);
    await expect(
      page.getByText("Neuložené zmeny", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Uložiť profil", exact: true })
      .click();
    await expect(
      page.getByText("Uložená verzia 1", { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByLabel("Názov extrahovaného poľa 1", { exact: true }),
    ).toHaveValue(`Referencia ${index + 1}`);
    await expect(
      page.getByLabel("Cieľová značka poľa 1", { exact: true }),
    ).toHaveValue(tags[0]);
    await page
      .getByLabel("Názov profilu", { exact: true })
      .fill("Neuložený koncept");
    const historyDialog = page.waitForEvent("dialog");
    await page.evaluate(() => window.history.back());
    await (await historyDialog).dismiss();
    await expect(page.getByLabel("Názov profilu", { exact: true })).toHaveValue(
      "Neuložený koncept",
    );
    page.once("dialog", (dialog) => dialog.accept());
    await page
      .getByRole("button", { name: "Zahodiť zmeny", exact: true })
      .click();
    await page
      .getByLabel("Dokument na skúšku")
      .selectOption("00000000-0000-4000-8000-000000000099");
    await page
      .getByRole("button", { name: "Spustiť skúšku", exact: true })
      .click();
    await expect(page).toHaveURL(
      /\/review\/00000000-0000-4000-8000-000000000098$/,
    );
    expect(submittedVersion).toMatchObject({
      profileId: profiles[index].id,
      profileVersion: 1,
    });
  }
  expect(profiles[0].formId).not.toBe(profiles[1].formId);
  expect(profiles[0].scalarFields).toMatchObject([
    { targetTag: "project_reference" },
  ]);
  expect(profiles[1].tableFields).toMatchObject([
    { targetTag: "milestones", columns: [{ targetTag: "payment" }] },
  ]);
  expect(await page.evaluate(() => "hostileImport" in window)).toBe(false);
});

test("editor retains the document-desk layout at mobile and enlarged text", async ({
  page,
}) => {
  const form = {
    id: "00000000-0000-4000-8000-000000000002",
    name: "Ilustračný grant",
    isIllustrative: true,
    originalJson: {},
    fields: [
      {
        tag: "project_reference",
        label: "Referencia projektu",
        type: "string",
        required: true,
        options: null,
      },
    ],
    tables: [],
  };
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/session"))
      return route.fulfill({
        json: { data: { authenticated: true, mode: "fixture" } },
      });
    if (path.endsWith("/capabilities"))
      return route.fulfill({
        json: {
          data: {
            mode: "fixture",
            aiConfigured: false,
            ocrConfigured: false,
            egrantConfigured: false,
          },
        },
      });
    return route.fulfill({
      json: { data: [form], pagination: { limit: 200, offset: 0, total: 1 } },
    });
  });
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/profiles/new");
    await expect(
      page.getByLabel("Názov profilu", { exact: true }),
    ).toBeVisible();
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/profiles-editor-${width}.png`,
      fullPage: true,
    });
    await expect(
      page.getByText(
        "Ukážkový režim · Syntetické údaje · Zápis do eGrantu je vypnutý",
      ),
    ).toBeVisible();
  }
});
