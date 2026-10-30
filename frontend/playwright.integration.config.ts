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
  testMatch: "integration.spec.ts",
  workers: 1,
  use: { baseURL: "http://localhost:5176", browserName: "chromium" },
  webServer: [
    {
      command: `"${python}" ../tests/e2e/serve_submissions.py`,
      port: 8013,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5176",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8013" },
      port: 5176,
      reuseExistingServer: false,
    },
  ],
});
