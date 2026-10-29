import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

// The end-to-end suite drives the real stack: a FastAPI backend and the Next.js
// frontend, talking over the BFF route handlers exactly as in production, with
// nothing mocked at that boundary. Both servers run against a throwaway
// database and a synthetic content directory under e2e/.tmp, so the real data/
// and content/ are never touched.

const BACKEND_PORT = 8731;
const FRONTEND_PORT = 3731;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
// The frontend is reached over "localhost" rather than "127.0.0.1" so the
// browser origin matches the host Next puts into server-built redirect URLs
// (the /r/{token} redeem route). Otherwise the host-only session cookie set on
// one host would not travel to the other, and the recruiter gate would bounce
// a valid session. In production both are the one real domain behind Caddy.
const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;

const TMP_DIR = path.join(__dirname, "e2e", ".tmp");
// The admin password comes from the environment; a fixed local default keeps
// the suite zero-config while a real secret never lives in committed code.
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "e2e-admin-password";
// The test authentik from deploy/authentik-test. Its tests only run when it is
// up and AUTHENTIK_URL points at it, as in the CI. Locally the suite runs
// without it as before.
const AUTHENTIK_URL = process.env.AUTHENTIK_URL;
const AUTHENTIK_COMPOSE = path.join(
  __dirname,
  "..",
  "deploy",
  "authentik-test",
  "compose.yaml",
);
// The application slug and client ID of wediga.dev in the blueprint.
const OIDC_CLIENT_ID = "wediga-dev";

// The client secret is a fixed test value defined only in the test
// authentik's compose file, so it is read from there.
function testClientSecret(): string {
  const match = readFileSync(AUTHENTIK_COMPOSE, "utf-8").match(
    /WEDIGA_OIDC_CLIENT_SECRET: (\S+)/,
  );

  if (!match) {
    throw new Error(`no WEDIGA_OIDC_CLIENT_SECRET in ${AUTHENTIK_COMPOSE}`);
  }

  return match[1];
}

// With the test authentik up, the backend gets the login through it switched
// on. Without it the login stays off, as in production.
const OIDC_ENV: Record<string, string> = AUTHENTIK_URL
  ? {
      OIDC_ENABLED: "true",
      OIDC_ISSUER: `${AUTHENTIK_URL}/application/o/${OIDC_CLIENT_ID}/`,
      OIDC_CLIENT_ID,
      OIDC_CLIENT_SECRET: testClientSecret(),
      OIDC_REDIRECT_URI: `${FRONTEND_URL}/auth/callback`,
    }
  : {};

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    ...(AUTHENTIK_URL
      ? [
          {
            name: "authentik",
            testDir: "./e2e/authentik",
            use: { ...devices["Desktop Chrome"] },
          },
        ]
      : []),
  ],
  webServer: [
    {
      command: "bash e2e/start-backend.sh",
      url: `${BACKEND_URL}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        WEDIGA_DB_PATH: path.join(TMP_DIR, "data", "e2e.db"),
        WEDIGA_CONTENT_DIR: path.join(TMP_DIR, "content"),
        BACKEND_PORT: String(BACKEND_PORT),
        ADMIN_PASSWORD,
        SESSION_SECRET: "e2e-session-secret-not-for-production",
        COOKIE_SECURE: "false",
        ...OIDC_ENV,
      },
    },
    {
      command: `npm run build && npm run start -- -p ${FRONTEND_PORT} -H localhost`,
      url: FRONTEND_URL,
      timeout: 240_000,
      reuseExistingServer: false,
      env: {
        BACKEND_URL,
      },
    },
  ],
});
