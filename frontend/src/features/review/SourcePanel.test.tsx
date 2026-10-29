import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "../../shared/api";
import { SourcePanel } from "./SourcePanel";
import documentExample from "../../../../contracts/examples/document.json";
import normalizedExample from "../../../../contracts/examples/normalized-document.json";

let client: QueryClient;
let mediaType: string;
beforeEach(() => {
  mediaType = "application/pdf";
  client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  vi.spyOn(api, "GET").mockImplementation(
    async (path) =>
      ({
        data: {
          data:
            path === "/api/v1/documents/{id}"
              ? { ...documentExample, mediaType, pageCount: 1 }
              : {
                  ...normalizedExample,
                  units: normalizedExample.units.map((unit) => ({
                    ...unit,
                    page: 1,
                    sheet: null,
                    cell: null,
                  })),
                },
        },
        response: new Response(null, { status: 200 }),
      }) as never,
  );
});
afterEach(() => {
  cleanup();
  client.clear();
  vi.restoreAllMocks();
});

test("PDF navigation uses existing source units and a supported page", async () => {
  render(
    <QueryClientProvider client={client}>
      <SourcePanel
        documentId={documentExample.id}
        selected={{
          documentId: documentExample.id,
          unitId: "row-2",
          quote: "DEMO-2026-001",
          page: 1,
          sheet: null,
          cell: null,
        }}
      />
    </QueryClientProvider>,
  );
  expect(
    await screen.findByRole("link", { name: "Otvoriť PDF — strana 1" }),
  ).toHaveAttribute(
    "href",
    `/api/v1/documents/${documentExample.id}/content#page=1`,
  );
  expect(screen.getByTitle("Náhľad PDF")).toHaveAttribute("sandbox", "");
  expect(
    await screen.findByRole("region", { name: "Vybraný zdroj" }),
  ).toHaveTextContent("DEMO-2026-001");
});

test("failed image preview is explicit while normalized text remains available", async () => {
  mediaType = "image/png";
  render(
    <QueryClientProvider client={client}>
      <SourcePanel documentId={documentExample.id} selected={null} />
    </QueryClientProvider>,
  );
  fireEvent.error(await screen.findByAltText("Nahraný zdrojový dokument"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Náhľad obrázka sa nepodarilo načítať",
  );
  expect(screen.getByText("Text dokumentu")).toBeInTheDocument();
});
