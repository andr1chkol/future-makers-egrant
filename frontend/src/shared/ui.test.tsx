import { render, screen } from "@testing-library/react";
import { test, expect } from "vitest";
import { FeatureUnavailable } from "./ui";

test("unimplemented feature communicates unavailable state", () => {
  render(<FeatureUnavailable title="Nahrať dokumenty" />);
  expect(
    screen.getByRole("heading", { name: "Nahrať dokumenty" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent(
    "Táto funkcia zatiaľ nie je dostupná.",
  );
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
