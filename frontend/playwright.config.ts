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
  testIgnore: "integration.spec.ts",
  use: { baseURL: "http://localhost:5174", browserName: "chromium" },
  webServer: [
    {
      command: `"${python}" ../tests/e2e/serve_app.py`,
      env: {
        DEV_AUTH_BYPASS: "true",
        APP_MODE: "fixture",
        COOKIE_SECURE: "false",
        PUBLIC_ORIGIN: "http://localhost:5174",
        ...(process.env.TEST_DATABASE_URL
          ? { DATABASE_URL: process.env.TEST_DATABASE_URL }
          : {}),
      },
      port: 8011,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5174",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8011" },
      port: 5174,
      reuseExistingServer: false,
    },
  ],
});
