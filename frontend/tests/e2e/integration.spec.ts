import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const reviewId = "00000000-0000-4000-8000-000000000004";
const origin = "http://localhost:5176";
const requestBody = {
  reviewId,
  reviewRevision: 2,
  mode: "export",
  targetContext: { applicationId: null },
  acknowledgeOverwrite: false,
};

test("real submission endpoint preserves corrections, idempotency and JSON download", async ({
  page,
  request,
}) => {
  const key = crypto.randomUUID();
  const headers = { Origin: origin, "Idempotency-Key": key };
  const response = await request.post("/api/v1/submissions", {
    headers,
    data: requestBody,
  });
  expect(response.status()).toBe(201);
  const submission = (await response.json()).data;
  const repeat = await request.post("/api/v1/submissions", {
    headers,
    data: requestBody,
  });
  expect((await repeat.json()).data.id).toBe(submission.id);
  const conflict = await request.post("/api/v1/submissions", {
    headers,
    data: { ...requestBody, reviewRevision: 3 },
  });
  expect(conflict.status()).toBe(409);
  await page.goto(`/submissions/${submission.id}`);
  await expect(
    page.getByText("Pripravené na export", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Potvrdený obsah JSON")).toContainText(
    "HUMAN-PO-001",
  );
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Stiahnuť JSON" }).click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe(`submission-${submission.id}.json`);
  const file = await download.path();
  expect(file).not.toBeNull();
  const payload = JSON.parse(await readFile(file!, "utf8"));
  const expected = JSON.parse(
    await readFile(resolve("../contracts/examples/submission.json"), "utf8"),
  ).payload;
  expect(payload).toEqual(expected);
  await expect(
    page.getByText("Exportované do JSON", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Exportované do JSON", { exact: true }),
  ).toBeVisible();
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Stiahnuť JSON" }),
    ).toBeVisible();
  }
  await page.screenshot({
    path: "../docs/release/integration-export.png",
    fullPage: true,
  });
});

test("stale review and eGrant requests fail without a successful operation", async ({
  request,
}) => {
  for (const data of [
    { ...requestBody, reviewRevision: 1 },
    { ...requestBody, mode: "egrant", acknowledgeOverwrite: true },
  ]) {
    const result = await request.post("/api/v1/submissions", {
      headers: { Origin: origin, "Idempotency-Key": crypto.randomUUID() },
      data,
    });
    expect(result.status()).toBe(data.mode === "egrant" ? 503 : 409);
  }
  const capability = await request.get("/api/v1/capabilities");
  expect((await capability.json()).data.egrantConfigured).toBe(false);
});

test("history distinguishes unavailable, empty, failure and real returned records", async ({
  page,
}) => {
  await page.goto("/history");
  await expect(page.getByRole("alert")).toContainText(
    "po pripojení modulu extrakcie",
  );
  // History owner is absent. These are explicit UI-only responses, not a live-flow claim.
  let state = "empty";
  await page.route("**/api/v1/extractions?*", async (route) => {
    if (state === "failure")
      return route.fulfill({
        status: 502,
        json: {
          error: {
            code: "UPSTREAM_FAILED",
            message: "Unavailable",
            details: null,
          },
        },
      });
    const extraction = JSON.parse(
      await readFile(resolve("../contracts/examples/extraction.json"), "utf8"),
    );
    return route.fulfill({
      json: {
        data: state === "empty" ? [] : [extraction],
        pagination: { limit: 20, offset: 0, total: state === "empty" ? 0 : 1 },
      },
    });
  });
  await page.getByRole("button", { name: "Skúsiť znova" }).click();
  await expect(
    page.getByText("Zatiaľ tu nie sú žiadne spracovania."),
  ).toBeVisible();
  state = "failure";
  await page.reload();
  await expect(page.getByRole("alert")).toHaveText(
    "Históriu sa nepodarilo načítať.",
  );
  state = "record";
  await page.getByRole("button", { name: "Skúsiť znova" }).click();
  await expect(
    page.getByRole("link", { name: "Skontrolovať údaje" }),
  ).toHaveAttribute("href", `/review/${reviewId}`);
  await expect(page.getByRole("listitem")).toContainText("Ukážkové údaje");
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("status and download failures offer retry without an external write", async ({
  page,
  request,
}) => {
  const result = await request.post("/api/v1/submissions", {
    headers: { Origin: origin, "Idempotency-Key": crypto.randomUUID() },
    data: requestBody,
  });
  const id = (await result.json()).data.id;
  let fail = true;
  await page.route(`**/api/v1/submissions/${id}`, (route) =>
    fail
      ? route.fulfill({
          status: 502,
          json: {
            error: {
              code: "UPSTREAM_FAILED",
              message: "Unavailable",
              details: null,
            },
          },
        })
      : route.continue(),
  );
  await page.goto(`/submissions/${id}`);
  await expect(page.getByRole("alert")).toContainText("nepodarilo načítať");
  fail = false;
  await page.getByRole("button", { name: "Skúsiť znova" }).click();
  await expect(
    page.getByRole("button", { name: "Stiahnuť JSON" }),
  ).toBeVisible();
  await page.route(`**/api/v1/submissions/${id}/export`, (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "FEATURE_UNAVAILABLE",
          message: "Unavailable",
          details: null,
        },
      },
    }),
  );
  await page.getByRole("button", { name: "Stiahnuť JSON" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Súbor sa nepodarilo stiahnuť",
  );
});
