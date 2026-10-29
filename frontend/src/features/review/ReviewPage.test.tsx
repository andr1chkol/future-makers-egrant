import { afterEach, beforeEach, expect, test, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { webcrypto } from "node:crypto";
import { api } from "../../shared/api";
import { ReviewPage } from "./ReviewPage";
import { SubmissionActions } from "./SubmissionActions";
import { warningIdentity, type Review, type Profile } from "./model";
import extractionExample from "../../../../contracts/examples/extraction.json";
import profileExample from "../../../../contracts/examples/profile.json";
import formExample from "../../../../contracts/examples/form.json";
import reviewExample from "../../../../contracts/examples/review.json";
import documentExample from "../../../../contracts/examples/document.json";
import normalizedExample from "../../../../contracts/examples/normalized-document.json";
import submissionExample from "../../../../contracts/examples/submission.json";

let server: Review;
let unavailable: boolean;
let client: QueryClient;
let configured: boolean;
let overrides: Record<string, unknown>;
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value));
const ok = (data: unknown) => ({
  data: { data: copy(data) },
  response: new Response(null, { status: 200 }),
});

beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  sessionStorage.clear();
  unavailable = false;
  configured = false;
  overrides = {};
  server = {
    ...copy(reviewExample),
    status: "draft",
    confirmedAt: null,
    revision: 0,
  } as Review;
  client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (unavailable)
      return {
        error: {},
        response: new Response(null, { status: 503 }),
      } as never;
    const values: Record<string, unknown> = {
      "/api/v1/extractions/{id}": extractionExample,
      "/api/v1/profiles/{id}": profileExample,
      "/api/v1/forms/{id}": formExample,
      "/api/v1/reviews/{extraction_id}": server,
      "/api/v1/documents/{id}": documentExample,
      "/api/v1/documents/{id}/normalized": normalizedExample,
      "/api/v1/capabilities": {
        ocrConfigured: false,
        aiConfigured: false,
        egrantConfigured: configured,
        mode: "fixture",
      },
    };
    return ok(overrides[path] ?? values[path]) as never;
  });
});
afterEach(() => {
  cleanup();
  client.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function page() {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/review/${extractionExample.id}`]}>
        <Routes>
          <Route path="/review/:extractionId" element={<ReviewPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("warning identity matches the frozen Python fixture", async () => {
  expect(await warningIdentity(extractionExample.warnings[0])).toBe(
    reviewExample.acknowledgedWarnings[0],
  );
});

test("edit, add/delete rows, navigate source, save, remount and explicitly confirm", async () => {
  const put = vi
    .spyOn(api, "PUT")
    .mockImplementation(async (_path, options) => {
      const body = options?.body;
      server = {
        ...server,
        fields: copy(body!.fields),
        tables: copy(body!.tables),
        acknowledgedWarnings: copy(body!.acknowledgedWarnings),
        revision: server.revision + 1,
      };
      return ok(server) as never;
    });
  const post = vi.spyOn(api, "POST").mockImplementation(async (path) => {
    expect(path).toBe("/api/v1/reviews/{extraction_id}/confirm");
    server = {
      ...server,
      status: "confirmed",
      revision: server.revision + 1,
      confirmedAt: "2026-10-29T20:00:00Z",
    };
    return ok(server) as never;
  });
  const view = page();
  await screen.findByLabelText("Dodávateľ *");
  expect(
    screen.queryByRole("button", { name: "Exportovať JSON" }),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Dodávateľ *"), {
    target: { value: "Human supplier" },
  });
  expect(
    screen.getByRole("button", { name: "Skontrolovať súhrn" }),
  ).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Pridať riadok do Položky" }),
  );
  expect(screen.getByText("Pridaný človekom")).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Odstrániť riadok 3 z Položky" }),
  );
  fireEvent.click(screen.getAllByRole("button", { name: /Zdroj 1/ })[0]);
  expect(
    await screen.findByRole("region", { name: "Vybraný zdroj" }),
  ).toHaveTextContent("DEMO-2026-001");
  fireEvent.click(screen.getByRole("button", { name: "Uložiť koncept" }));
  await screen.findByText("Koncept bol uložený.");
  expect(put).toHaveBeenCalledOnce();
  view.unmount();
  page();
  expect(await screen.findByLabelText("Dodávateľ *")).toHaveValue(
    "Human supplier",
  );
  expect(post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Skontrolovať súhrn" }));
  expect(
    screen.getByRole("region", { name: "Záverečný súhrn" }),
  ).toHaveTextContent("Human supplier");
  fireEvent.click(screen.getByRole("button", { name: "Potvrdiť údaje" }));
  expect(
    await screen.findByRole("button", { name: "Exportovať JSON" }),
  ).toBeEnabled();
  expect(screen.getByLabelText("Dodávateľ *")).toBeDisabled();
  expect(post).toHaveBeenCalledOnce();
});

test("stale PUT and background refetch preserve local edits; reload requires explicit discard", async () => {
  vi.spyOn(api, "PUT").mockImplementation(async () => {
    server.revision = 1;
    server.fields[1].value = "Other editor";
    return {
      error: {},
      response: new Response(null, { status: 409 }),
    } as never;
  });
  page();
  await screen.findByLabelText("Dodávateľ *");
  fireEvent.change(screen.getByLabelText("Dodávateľ *"), {
    target: { value: "Unsaved local" },
  });
  await client.refetchQueries({ queryKey: ["review", extractionExample.id] });
  expect(screen.getByLabelText("Dodávateľ *")).toHaveValue("Unsaved local");
  fireEvent.click(screen.getByRole("button", { name: "Uložiť koncept" }));
  await screen.findByText("Na serveri je novšia revízia 1");
  expect(screen.getByLabelText("Dodávateľ *")).toHaveValue("Unsaved local");
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.click(
    screen.getByRole("button", { name: "Načítať uloženú verziu" }),
  );
  expect(screen.getByLabelText("Dodávateľ *")).toHaveValue("Unsaved local");
  confirm.mockReturnValue(true);
  fireEvent.click(
    screen.getByRole("button", { name: "Načítať uloženú verziu" }),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Dodávateľ *")).toHaveValue("Other editor"),
  );
});

test("service failure is visible and retry loads the review", async () => {
  unavailable = true;
  page();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "služba ešte nie je dostupná",
  );
  unavailable = false;
  fireEvent.click(screen.getByRole("button", { name: "Skúsiť znova" }));
  await screen.findByLabelText("Dodávateľ *");
});

test("export reuses its key after a lost response; no apply happens implicitly", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockRejectedValueOnce(new TypeError("network"))
    .mockResolvedValue(ok(submissionExample) as never);
  server.status = "confirmed";
  server.revision = 2;
  render(
    <QueryClientProvider client={client}>
      <SubmissionActions review={server} profile={profileExample as Profile} />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Exportovať JSON" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Exportovať JSON" }));
  await screen.findByRole("button", { name: "Stiahnuť JSON" });
  expect(post.mock.calls[0][1]).toEqual(post.mock.calls[1][1]);
  expect(post).toHaveBeenLastCalledWith(
    "/api/v1/submissions",
    expect.objectContaining({
      body: expect.objectContaining({
        mode: "export",
        reviewRevision: 2,
        targetContext: { applicationId: null },
      }),
    }),
  );
});

test("apply requires consent and retains the original intent across reload and unknown outcomes", async () => {
  configured = true;
  server.status = "confirmed";
  server.revision = 2;
  const post = vi
    .spyOn(api, "POST")
    .mockRejectedValueOnce(new TypeError("lost response"))
    .mockResolvedValue(
      ok({
        ...submissionExample,
        mode: "egrant",
        status: "unknown",
        targetContext: { applicationId: "test-application" },
      }) as never,
    );
  const component = () => (
    <QueryClientProvider client={client}>
      <SubmissionActions review={server} profile={profileExample as Profile} />
    </QueryClientProvider>
  );
  const view = render(component());
  await screen.findByLabelText("Identifikátor cieľovej žiadosti");
  expect(
    screen.getByRole("button", { name: "Zapísať do eGrantu" }),
  ).toBeDisabled();
  expect(post).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Identifikátor cieľovej žiadosti"), {
    target: { value: "test-application" },
  });
  fireEvent.click(screen.getByRole("checkbox", { name: /Potvrdzujem zápis/ }));
  fireEvent.click(screen.getByRole("button", { name: "Zapísať do eGrantu" }));
  await screen.findByRole("button", { name: "Overiť pôvodnú požiadavku" });
  view.unmount();
  render(component());
  expect(
    await screen.findByLabelText("Identifikátor cieľovej žiadosti"),
  ).toHaveValue("test-application");
  expect(
    screen.getByLabelText("Identifikátor cieľovej žiadosti"),
  ).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Overiť pôvodnú požiadavku" }),
  );
  await screen.findByText(
    "Výsledok zápisu je neznámy — vyžaduje overenie správcom",
  );
  expect(post.mock.calls[0][1]).toEqual(post.mock.calls[1][1]);
  expect(
    screen.queryByRole("button", { name: "Overiť pôvodnú požiadavku" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Zapísať do eGrantu" }),
  ).toBeDisabled();
});

test("replace stays unavailable without a safe current-state preview", async () => {
  configured = true;
  server.status = "confirmed";
  const profile = copy(profileExample) as Profile;
  profile.tableFields[0].writeMode = "replace";
  const post = vi.spyOn(api, "POST");
  render(
    <QueryClientProvider client={client}>
      <SubmissionActions review={server} profile={profile} />
    </QueryClientProvider>,
  );
  await screen.findByText(/Profil požaduje nahradenie tabuľky/);
  expect(
    screen.queryByRole("button", { name: "Zapísať do eGrantu" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Exportovať JSON" })).toBeEnabled();
  expect(post).not.toHaveBeenCalled();
});

test("empty configurable profiles and duplicate warnings have useful states", async () => {
  overrides["/api/v1/profiles/{id}"] = {
    ...profileExample,
    scalarFields: [],
    tableFields: [],
  };
  overrides["/api/v1/reviews/{extraction_id}"] = {
    ...server,
    fields: [],
    tables: [],
  };
  overrides["/api/v1/extractions/{id}"] = {
    ...extractionExample,
    fields: [],
    tables: [],
    warnings: [...extractionExample.warnings, ...extractionExample.warnings],
  };
  page();
  expect(screen.getByText("Načítavame uložený koncept…")).toBeInTheDocument();
  await screen.findByText("Profil nemá samostatné polia.");
  expect(
    screen.getAllByRole("checkbox", { name: /Rozumiem upozorneniu/ }),
  ).toHaveLength(1);
});
