import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  forbidOnly: true,
  use: { baseURL: "http://localhost:5174", browserName: "chromium" },
  webServer: [
    {
      cwd: "../../../..",
      command:
        ".venv/bin/python -m uvicorn browser_server:app --port 8012 --no-access-log",
      env: {
        PYTHONPATH: "backend:tests/reviews",
        DEV_AUTH_BYPASS: "true",
        APP_MODE: "fixture",
        COOKIE_SECURE: "false",
        PUBLIC_ORIGIN: "http://localhost:5174",
      },
      url: "http://localhost:8012/health",
      reuseExistingServer: false,
    },
    {
      cwd: "../../..",
      command: "npm run dev -- --port 5174",
      env: { API_PROXY_TARGET: "http://127.0.0.1:8012" },
      port: 5174,
      reuseExistingServer: false,
    },
  ],
});
