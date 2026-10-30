import { expect, test } from "vitest";
import { sourceContainsCell } from "./sourceLocation";

test("a selected spreadsheet cell finds its exact source or containing CSV row", () => {
  expect(sourceContainsCell("A2:I2", "b2")).toBe(true);
  expect(sourceContainsCell("Z2:AB2", "AA2")).toBe(true);
  expect(sourceContainsCell("B2", "b2")).toBe(true);
  expect(sourceContainsCell("A2:I2", "A2:I2")).toBe(true);
  expect(sourceContainsCell("A2:I2", "J2")).toBe(false);
  expect(sourceContainsCell("A2:I2", "B3")).toBe(false);
  expect(sourceContainsCell("A2:I2", "not a cell")).toBe(false);
  expect(sourceContainsCell(null, "B2")).toBe(false);
  expect(sourceContainsCell(null, "")).toBe(true);
});
