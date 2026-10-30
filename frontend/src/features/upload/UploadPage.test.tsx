import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { api } from "../../shared/api";
import { UploadPage } from "./UploadPage";

const documentId = "00000000-0000-4000-8000-000000000001";
const profileId = "00000000-0000-4000-8000-000000000003";
let documents: Record<string, unknown>[];
let extractions: Record<string, unknown>[];
let failList: boolean;
let failUpload: boolean;
let status: string;

function document() {
  return {
    id: documentId,
    filename: "podklady.csv",
    mediaType: "text/csv",
    status,
    contentHash: "a".repeat(64),
    duplicateOf: null,
    createdAt: "2026-10-30T12:00:00Z",
    pageCount: null,
    warnings: [],
    error:
      status === "failed"
        ? { code: "OCR_TIMEOUT", message: "timeout", details: null }
        : null,
  };
}
function page(data: unknown[]) {
  return { data, pagination: { total: data.length, limit: 50, offset: 0 } };
}
function mount() {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={["/documents"]}>
        <Routes>
          <Route path="/documents" element={<UploadPage />} />
          <Route path="/review/:id" element={<h1>Kontrola údajov</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  documents = [];
  extractions = [];
  failList = false;
  failUpload = false;
  status = "ready";
  vi.spyOn(api, "GET").mockImplementation((async (path: string) => {
    if (path === "/api/v1/documents")
      return failList
        ? { error: { error: { code: "FEATURE_UNAVAILABLE" } } }
        : { data: page(documents) };
    if (path === "/api/v1/profiles")
      return {
        data: page([{ id: profileId, version: 2, name: "Grantový profil" }]),
      };
    if (path === "/api/v1/extractions") return { data: page(extractions) };
    if (path === "/api/v1/capabilities")
      return {
        data: {
          data: { ocrConfigured: false, aiConfigured: true, mode: "fixture" },
        },
      };
    return { data: { data: document() } };
  }) as never);
  vi.spyOn(api, "POST").mockImplementation((async (path: string) => {
    if (path === "/api/v1/documents") {
      if (failUpload) return { error: { error: { code: "MIME_MISMATCH" } } };
      documents = [document()];
      return { data: { data: documents } };
    }
    if (path.endsWith("/retries")) {
      status = "ready";
      documents = [document()];
      return { data: { data: documents[0] } };
    }
    if (path === "/api/v1/extractions") {
      extractions = [{ id: "run-one", documentId, status: "queued" }];
      return { data: { data: { extractions } } };
    }
  }) as never);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("uploads a file, selects a profile and opens the separate review link", async () => {
  mount();
  expect(await screen.findByText(/Zatiaľ tu nie sú/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Vybrať dokumenty"), {
    target: {
      files: [new File(["a,b"], "podklady.csv", { type: "text/csv" })],
    },
  });
  fireEvent.click(await screen.findByLabelText("Vybrať podklady.csv"));
  fireEvent.change(screen.getByLabelText("Extrakčný profil"), {
    target: { value: `${profileId}:2` },
  });
  fireEvent.click(
    screen.getByRole("button", { name: /Spustiť ukážkovú extrakciu/ }),
  );
  const link = await screen.findByRole("link", { name: /Skontrolovať údaje/ });
  expect(link).toHaveAttribute("href", "/review/run-one");
  expect(api.POST).toHaveBeenCalledWith("/api/v1/extractions", {
    body: { documentIds: [documentId], profileId, profileVersion: 2 },
  });
  fireEvent.click(link);
  expect(
    await screen.findByRole("heading", { name: "Kontrola údajov" }),
  ).toBeInTheDocument();
});

test("partial upload rejection retains the previously accepted document after remount", async () => {
  documents = [document()];
  failUpload = true;
  const first = mount();
  await screen.findByText("podklady.csv");
  fireEvent.change(screen.getByLabelText("Vybrať dokumenty"), {
    target: {
      files: [new File(["bad"], "bad.pdf", { type: "application/pdf" })],
    },
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /Obsah súboru nezodpovedá/,
  );
  expect(
    within(screen.getByRole("list", { name: "Prijaté dokumenty" })).getByText(
      "podklady.csv",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Zopakovať nahrávanie" }),
  ).toBeEnabled();
  first.unmount();
  mount();
  expect(await screen.findByText("podklady.csv")).toBeInTheDocument();
});

test("failed processing can be retried and refreshed", async () => {
  status = "failed";
  documents = [document()];
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Zopakovať spracovanie" }),
  );
  expect(await screen.findByText("Pripravený")).toBeInTheDocument();
  expect(api.POST).toHaveBeenCalledWith("/api/v1/documents/{id}/retries", {
    params: { path: { id: documentId } },
  });
  fireEvent.click(screen.getByRole("button", { name: "Obnoviť zoznam" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Obnoviť zoznam" }),
    ).toBeEnabled(),
  );
});

test("list failure has a usable recovery and provider configuration is explained", async () => {
  failList = true;
  mount();
  expect(
    await screen.findByText(/Zoznam sa nepodarilo načítať/),
  ).toBeInTheDocument();
  expect(screen.getByText(/OCR nie je dostupné/)).toBeInTheDocument();
  failList = false;
  fireEvent.click(screen.getByRole("button", { name: "Obnoviť zoznam" }));
  expect(await screen.findByText(/Zatiaľ tu nie sú/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Spustiť/ })).toBeDisabled();
});

test("automatic retry remains pollable and becomes ready without manual retry", async () => {
  status = "uploaded";
  documents = [
    {
      ...document(),
      error: { code: "OCR_TIMEOUT", message: "timeout", details: null },
    },
  ];
  mount();
  expect(await screen.findByText("Čaká na spracovanie")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Zopakovať spracovanie" }),
  ).not.toBeInTheDocument();
  status = "ready";
  documents = [document()];
  expect(
    await screen.findByText("Pripravený", {}, { timeout: 4000 }),
  ).toBeInTheDocument();
});

test("network failures show Slovak recovery text without raw exception content", async () => {
  vi.mocked(api.POST).mockRejectedValueOnce(new Error("private-provider-key"));
  mount();
  await screen.findByText(/Zatiaľ tu nie sú/);
  fireEvent.change(screen.getByLabelText("Vybrať dokumenty"), {
    target: { files: [new File(["a,b"], "data.csv", { type: "text/csv" })] },
  });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Operácia zlyhala. Skontrolujte pripojenie a skúste znova.",
  );
  expect(screen.queryByText("private-provider-key")).not.toBeInTheDocument();
});
