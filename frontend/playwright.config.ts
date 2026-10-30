import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  testIgnore: "integration.spec.ts",
  use: { baseURL: "http://localhost:5174", browserName: "chromium" },
  webServer: [
    {
      command:
        "DEV_AUTH_BYPASS=true APP_MODE=fixture COOKIE_SECURE=false PUBLIC_ORIGIN=http://localhost:5174 ../.venv/bin/python -m uvicorn app.main:app --port 8011 --no-access-log --app-dir ../backend",
      env: process.env.TEST_DATABASE_URL
        ? { DATABASE_URL: process.env.TEST_DATABASE_URL }
        : {},
      port: 8011,
      reuseExistingServer: false,
    },
    {
      command:
        "API_PROXY_TARGET=http://127.0.0.1:8011 npm run dev -- --port 5174",
      port: 5174,
      reuseExistingServer: false,
    },
  ],
});
