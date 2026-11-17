const {
  defineConfig,
} = require("../../frontend/node_modules/@playwright/test");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const python = path.join(
  root,
  process.platform === "win32"
    ? ".venv/Scripts/python.exe"
    : ".venv/bin/python",
);
module.exports = defineConfig({
  testDir: __dirname,
  testMatch: "upload.spec.cjs",
  workers: 1,
  timeout: 45000,
  outputDir: path.join(root, ".private/browser-results"),
  use: {
    baseURL: "http://localhost:5175",
    browserName: "chromium",
    channel: "chromium",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" tests/documents/serve.py`,
      cwd: root,
      port: 8012,
      reuseExistingServer: !!process.env.DOCUMENT_REUSE_TEST_SERVERS,
      env: {
        PYTHONPATH: path.join(root, "backend"),
        PYTHONUTF8: "1",
        DEV_AUTH_BYPASS: "true",
        APP_MODE: "fixture",
        COOKIE_SECURE: "false",
        PUBLIC_ORIGIN: "http://localhost:5175",
        DATABASE_URL:
          process.env.DOCUMENT_E2E_DATABASE_URL ||
          "postgresql+psycopg://egrant@127.0.0.1:55432/egrant_test_documents_e2e",
        FILE_STORAGE_PATH: path.join(root, ".private/browser-files"),
      },
    },
    {
      command: "npm run dev -- --port 5175",
      cwd: path.join(root, "frontend"),
      port: 5175,
      reuseExistingServer: !!process.env.DOCUMENT_REUSE_TEST_SERVERS,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8012" },
    },
  ],
});
