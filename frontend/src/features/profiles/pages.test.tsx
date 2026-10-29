import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ProfilesPage, ProfileEditorPage } from "./pages";

const calls = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../../shared/api", () => ({
  api: { GET: calls.get, POST: calls.post },
}));

const form = {
  id: "00000000-0000-4000-8000-000000000002",
  name: "Grant A",
  isIllustrative: true,
  originalJson: { unsupported: { preserved: true } },
  fields: [
    {
      tag: "invoice_id",
      label: "Číslo",
      type: "string",
      required: true,
      options: null,
    },
  ],
  tables: [
    {
      tag: "expenses",
      label: "Výdavky",
      columns: [
        {
          tag: "amount",
          label: "Suma",
          type: "money",
          required: true,
          options: null,
        },
      ],
    },
  ],
};
const profile = {
  id: "00000000-0000-4000-8000-000000000003",
  version: 1,
  name: "Faktúry",
  documentKind: "invoice",
  formId: form.id,
  scalarFields: [
    {
      key: "number",
      label: "Číslo",
      type: "string",
      description: "Invoice number",
      required: true,
      targetTag: "invoice_id",
    },
  ],
  tableFields: [
    {
      key: "items",
      label: "Výdavky",
      targetTag: "expenses",
      writeMode: "append",
      columns: [
        {
          key: "total",
          label: "Suma",
          type: "money",
          description: "Line total",
          required: true,
          targetTag: "amount",
        },
      ],
    },
  ],
};

function show(
  path: string,
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  }),
) {
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/profiles/new" element={<ProfileEditorPage />} />
          <Route path="/profiles/:id" element={<ProfileEditorPage />} />
          <Route path="/review/:id" element={<h1>Kontrola návrhu</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  calls.get.mockReset();
  calls.post.mockReset();
  calls.get.mockImplementation(async (path: string) => {
    if (path === "/api/v1/forms")
      return {
        data: { data: [form], pagination: { limit: 200, offset: 0, total: 1 } },
      };
    if (path === "/api/v1/forms/{id}") return { data: { data: form } };
    if (path === "/api/v1/profiles")
      return {
        data: {
          data: [profile],
          pagination: { limit: 200, offset: 0, total: 1 },
        },
      };
    if (path === "/api/v1/profiles/{id}") return { data: { data: profile } };
    if (path === "/api/v1/capabilities")
      return {
        data: {
          data: {
            mode: "fixture",
            aiConfigured: false,
            ocrConfigured: false,
            egrantConfigured: false,
          },
        },
      };
    if (path === "/api/v1/documents")
      return {
        data: {
          data: [
            {
              id: "00000000-0000-4000-8000-000000000001",
              filename: "synthetic.csv",
              status: "ready",
              mediaType: "text/csv",
            },
          ],
          pagination: { limit: 200, offset: 0, total: 1 },
        },
      };
    throw new Error("Unexpected API path");
  });
});
afterEach(cleanup);

test("lists forms and profiles, searches and exposes import failures", async () => {
  show("/profiles");
  expect(await screen.findByText("Grant A")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Hľadať formulár alebo profil"), {
    target: { value: "absent" },
  });
  expect(screen.queryByText("Grant A")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Názov formulára"), {
    target: { value: "New form" },
  });
  fireEvent.change(screen.getByLabelText("Definícia JSON"), {
    target: { value: "{broken" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Importovať formulár" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("JSON");
  expect(calls.post).not.toHaveBeenCalled();
});

test("imports JSON without dropping unsupported configuration", async () => {
  calls.post.mockResolvedValue({ data: { data: form } });
  show("/profiles");
  await screen.findByText("Grant A");
  const definition = {
    illustrative: true,
    fields: [],
    tables: [],
    custom: { html: "<script>alert(1)</script>" },
  };
  fireEvent.change(screen.getByLabelText("Názov formulára"), {
    target: { value: "Imported" },
  });
  fireEvent.change(screen.getByLabelText("Definícia JSON"), {
    target: { value: JSON.stringify(definition) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Importovať formulár" }));
  await waitFor(() =>
    expect(calls.post).toHaveBeenCalledWith("/api/v1/forms", {
      body: { name: "Imported", definition },
    }),
  );
  expect(
    await screen.findByRole("heading", { name: "Nastavenie profilu" }),
  ).toBeInTheDocument();
});

test("edits and saves an immutable version with stable target tags", async () => {
  calls.post.mockImplementation(
    async (_path: string, options: { body: object }) => ({
      data: { data: { ...profile, ...options.body, version: 2 } },
    }),
  );
  show(`/profiles/${profile.id}`);
  const label = await screen.findByLabelText("Názov extrahovaného poľa 1");
  fireEvent.change(label, { target: { value: "Nové označenie" } });
  expect(screen.getByText("Neuložené zmeny")).toBeInTheDocument();
  const unload = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(unload);
  expect(unload.defaultPrevented).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Uložiť novú verziu" }));
  await waitFor(() =>
    expect(calls.post).toHaveBeenCalledWith(
      "/api/v1/profiles/{id}/versions",
      expect.objectContaining({
        body: expect.objectContaining({
          expectedVersion: 1,
          scalarFields: [
            expect.objectContaining({
              label: "Nové označenie",
              targetTag: "invoice_id",
            }),
          ],
        }),
      }),
    ),
  );
  expect(await screen.findByText("Uložená verzia 2")).toBeInTheDocument();
});

test("shows mapping errors next to fields and does not save invalid settings", async () => {
  show(`/profiles/${profile.id}`);
  fireEvent.change(await screen.findByLabelText("Typ extrahovaného poľa 1"), {
    target: { value: "date" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Uložiť novú verziu" }));
  expect(
    await screen.findByText("Typ sa nezhoduje s cieľovým poľom."),
  ).toBeInTheDocument();
  expect(calls.post).not.toHaveBeenCalled();
});

test("preserves draft on concurrent version conflict", async () => {
  calls.post.mockResolvedValue({
    error: { error: { code: "CONFLICT", details: null } },
  });
  show(`/profiles/${profile.id}`);
  fireEvent.change(await screen.findByLabelText("Názov profilu"), {
    target: { value: "My draft" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Uložiť novú verziu" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("novšiu verziu");
  expect(screen.getByLabelText("Názov profilu")).toHaveValue("My draft");
});

test("starts shared extraction with saved version and navigates to review", async () => {
  calls.post.mockResolvedValue({
    data: {
      data: {
        extractions: [
          {
            id: "run-1",
            documentId: "00000000-0000-4000-8000-000000000001",
            status: "queued",
          },
        ],
      },
    },
  });
  show(`/profiles/${profile.id}`);
  await screen.findByRole("option", { name: "synthetic.csv" });
  fireEvent.change(await screen.findByLabelText("Dokument na skúšku"), {
    target: { value: "00000000-0000-4000-8000-000000000001" },
  });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Spustiť skúšku" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Spustiť skúšku" }));
  expect(
    await screen.findByRole("heading", { name: "Kontrola návrhu" }),
  ).toBeInTheDocument();
  expect(calls.post).toHaveBeenCalledWith("/api/v1/extractions", {
    body: {
      documentIds: ["00000000-0000-4000-8000-000000000001"],
      profileId: profile.id,
      profileVersion: 1,
    },
  });
});

test("never enables a live trial when the AI adapter is unavailable", async () => {
  const original = calls.get.getMockImplementation()!;
  calls.get.mockImplementation((path, ...args) =>
    path === "/api/v1/capabilities"
      ? Promise.resolve({
          data: {
            data: {
              mode: "live",
              aiConfigured: false,
              ocrConfigured: false,
              egrantConfigured: false,
            },
          },
        })
      : original(path, ...args),
  );
  show(`/profiles/${profile.id}`);
  await screen.findByRole("option", { name: "synthetic.csv" });
  fireEvent.change(await screen.findByLabelText("Dokument na skúšku"), {
    target: { value: "00000000-0000-4000-8000-000000000001" },
  });
  expect(screen.getByRole("button", { name: "Spustiť skúšku" })).toBeDisabled();
  expect(
    await screen.findByText("Živá extrakcia nie je nakonfigurovaná."),
  ).toBeInTheDocument();
});

test("keeps historical versions read-only and fetches the requested version", async () => {
  show(`/profiles/${profile.id}?version=1`);
  expect(await screen.findByLabelText("Názov profilu")).toBeDisabled();
  expect(
    screen.queryByRole("button", { name: "Uložiť novú verziu" }),
  ).not.toBeInTheDocument();
  expect(calls.get).toHaveBeenCalledWith("/api/v1/profiles/{id}", {
    params: { path: { id: profile.id }, query: { version: 1 } },
  });
});

test("waits for current profile before initializing a cached editor", async () => {
  const original = calls.get.getMockImplementation()!;
  let complete!: (value: unknown) => void;
  calls.get.mockImplementation((path, ...args) =>
    path === "/api/v1/profiles/{id}"
      ? new Promise((resolve) => {
          complete = resolve;
        })
      : original(path, ...args),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  client.setQueryData(["profile", profile.id, null], profile);
  show(`/profiles/${profile.id}`, client);
  await waitFor(() =>
    expect(calls.get).toHaveBeenCalledWith(
      "/api/v1/profiles/{id}",
      expect.anything(),
    ),
  );
  expect(screen.queryByLabelText("Názov profilu")).not.toBeInTheDocument();
  complete({
    data: { data: { ...profile, name: "Latest title", version: 2 } },
  });
  expect(await screen.findByLabelText("Názov profilu")).toHaveValue(
    "Latest title",
  );
  expect(screen.getByText("Uložená verzia 2")).toBeInTheDocument();
});

test("retains draft when navigation is declined and can discard explicitly", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  show(`/profiles/${profile.id}`);
  fireEvent.change(await screen.findByLabelText("Názov profilu"), {
    target: { value: "Unfinished" },
  });
  fireEvent.click(screen.getByRole("link", { name: "← Profily a formuláre" }));
  expect(screen.getByLabelText("Názov profilu")).toHaveValue("Unfinished");
  expect(confirm).toHaveBeenCalled();
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Zahodiť zmeny" }));
  expect(screen.getByLabelText("Názov profilu")).toHaveValue(profile.name);
  expect(screen.queryByText("Neuložené zmeny")).not.toBeInTheDocument();
  confirm.mockRestore();
});

test("cancels native history traversal when the browser supports Navigation API", async () => {
  const navigation = new EventTarget();
  Object.defineProperty(window, "navigation", {
    value: navigation,
    configurable: true,
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  show(`/profiles/${profile.id}`);
  fireEvent.change(await screen.findByLabelText("Názov profilu"), {
    target: { value: "Unfinished" },
  });
  const traverse = Object.assign(new Event("navigate", { cancelable: true }), {
    navigationType: "traverse",
  });
  navigation.dispatchEvent(traverse);
  expect(traverse.defaultPrevented).toBe(true);
  confirm.mockRestore();
  Reflect.deleteProperty(window, "navigation");
});

test("surfaces shared extraction failure without navigating or fake success", async () => {
  calls.post.mockResolvedValue({
    error: { error: { code: "FEATURE_UNAVAILABLE", details: null } },
  });
  show(`/profiles/${profile.id}`);
  await screen.findByRole("option", { name: "synthetic.csv" });
  fireEvent.change(screen.getByLabelText("Dokument na skúšku"), {
    target: { value: "00000000-0000-4000-8000-000000000001" },
  });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Spustiť skúšku" }),
    ).toBeEnabled(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Spustiť skúšku" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "ešte nie je pripojená",
  );
  expect(
    screen.getByRole("heading", { name: "Nastavenie profilu" }),
  ).toBeInTheDocument();
});

test("searches forms by table columns and retains table matches in the editor", async () => {
  show("/profiles");
  await screen.findByText(form.name);
  fireEvent.change(screen.getByLabelText("Hľadať formulár alebo profil"), {
    target: { value: "amount" },
  });
  expect(screen.getByText(form.name)).toBeInTheDocument();
  cleanup();
  show(`/profiles/${profile.id}`);
  fireEvent.change(await screen.findByLabelText("Hľadať pole alebo tabuľku"), {
    target: { value: "amount" },
  });
  expect(
    screen.getByRole("checkbox", { name: "Výdavky · expenses" }),
  ).toBeInTheDocument();
});

test("does not trust cached capabilities after a failed refresh", async () => {
  const original = calls.get.getMockImplementation()!;
  calls.get.mockImplementation((path, ...args) =>
    path === "/api/v1/capabilities"
      ? Promise.reject(new Error("offline"))
      : original(path, ...args),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  client.setQueryData(["capabilities"], {
    mode: "fixture",
    aiConfigured: false,
    ocrConfigured: false,
    egrantConfigured: false,
  });
  show(`/profiles/${profile.id}`, client);
  await screen.findByRole("option", { name: "synthetic.csv" });
  await screen.findByRole("alert");
  fireEvent.change(screen.getByLabelText("Dokument na skúšku"), {
    target: { value: "00000000-0000-4000-8000-000000000001" },
  });
  expect(screen.getByRole("button", { name: "Spustiť skúšku" })).toBeDisabled();
});
