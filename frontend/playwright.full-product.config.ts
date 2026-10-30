import path from "node:path";
import { defineConfig } from "@playwright/test";

const python = path.resolve(
  process.cwd(),
  "..",
  process.platform === "win32"
    ? ".venv/Scripts/python.exe"
    : ".venv/bin/python",
);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "full-product.spec.ts",
  outputDir: "../.private/full-product-playwright",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: "http://localhost:5179",
    browserName: "chromium",
    trace: "retain-on-failure",
    actionTimeout: 15_000,
  },
  webServer: [
    {
      command: `"${python}" ../tests/e2e/serve_full_product.py`,
      port: 8017,
      gracefulShutdown: { signal: "SIGTERM", timeout: 30_000 },
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5179",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8017" },
      port: 5179,
      reuseExistingServer: false,
    },
  ],
});
