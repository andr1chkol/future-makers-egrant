import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const frontend = fileURLToPath(new URL("../../../", import.meta.url));
const databaseUrl =
  process.env.TEST_DATABASE_URL ??
  "postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_profiles";
if (!new URL(databaseUrl).pathname.slice(1).startsWith("egrant_test")) {
  throw new Error(
    "TEST_DATABASE_URL must point to an isolated egrant_test database",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "integration.spec.ts",
  workers: 1,
  use: { baseURL: "http://localhost:5175", browserName: "chromium" },
  webServer: [
    {
      command:
        "../.venv/bin/python -m uvicorn browser_app:app --app-dir ../tests/profiles --port 8012 --no-access-log",
      env: {
        PYTHONPATH: "../backend",
        DATABASE_URL: databaseUrl,
        DEV_AUTH_BYPASS: "true",
        APP_MODE: "fixture",
        COOKIE_SECURE: "false",
        PUBLIC_ORIGIN: "http://localhost:5175",
      },
      cwd: frontend,
      port: 8012,
      reuseExistingServer: false,
    },
    {
      command:
        "API_PROXY_TARGET=http://127.0.0.1:8012 npm run dev -- --port 5175",
      cwd: frontend,
      port: 5175,
      reuseExistingServer: false,
    },
  ],
});
