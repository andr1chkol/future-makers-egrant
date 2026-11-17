import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import foundation from "../../../playwright.config";

export default defineConfig({
  ...foundation,
  testDir: "./e2e",
  testMatch: "profiles.spec.ts",
  webServer: (Array.isArray(foundation.webServer)
    ? foundation.webServer
    : []
  ).map((server) => ({
    ...server,
    cwd: fileURLToPath(new URL("../../../", import.meta.url)),
  })),
});
