import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "integration.spec.ts",
  workers: 1,
  use: { baseURL: "http://localhost:5176", browserName: "chromium" },
  webServer: [
    {
      command: "../.venv/bin/python ../tests/e2e/serve_submissions.py",
      port: 8013,
      reuseExistingServer: false,
    },
    {
      command:
        "API_PROXY_TARGET=http://127.0.0.1:8013 npm run dev -- --port 5176",
      port: 5176,
      reuseExistingServer: false,
    },
  ],
});
