import { type Page, type BrowserContext } from '@playwright/test';

/**
 * Test user credentials — sourced from env vars or defaults.
 * In CI, set E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD etc.
 * Locally, the mock auth bypass cookie is used instead.
 */
export const TEST_USERS = {
  admin: {
    email: process.env.E2E_ADMIN_EMAIL ?? 'admin@e2e-test.local',
    password: process.env.E2E_ADMIN_PASSWORD ?? 'TestPassword123!',
    fullName: 'E2E Admin User',
    role: 'matter_admin' as const,
  },
  professional: {
    email: process.env.E2E_PROFESSIONAL_EMAIL ?? 'pro@e2e-test.local',
    password: process.env.E2E_PROFESSIONAL_PASSWORD ?? 'TestPassword123!',
    fullName: 'E2E Professional',
    role: 'professional' as const,
  },
  beneficiary: {
    email: process.env.E2E_BENEFICIARY_EMAIL ?? 'beneficiary@e2e-test.local',
    password: process.env.E2E_BENEFICIARY_PASSWORD ?? 'TestPassword123!',
    fullName: 'E2E Beneficiary',
    role: 'beneficiary' as const,
  },
  readOnly: {
    email: process.env.E2E_READONLY_EMAIL ?? 'readonly@e2e-test.local',
    password: process.env.E2E_READONLY_PASSWORD ?? 'TestPassword123!',
    fullName: 'E2E Read Only',
    role: 'read_only' as const,
  },
};

export type TestUserKey = keyof typeof TEST_USERS;

/**
 * Authenticate via Auth0 test user login flow.
 * If E2E_MOCK_AUTH is set, bypasses Auth0 by injecting a mock session cookie.
 */
export async function loginAs(
  page: Page,
  userKey: TestUserKey,
): Promise<void> {
  const user = TEST_USERS[userKey];

  if (process.env.E2E_MOCK_AUTH === 'true') {
    // Mock auth — set a session cookie that the backend/middleware recognises
    await page.context().addCookies([
      {
        name: 'appSession',
        value: JSON.stringify({
          user: {
            sub: `auth0|e2e-${userKey}`,
            email: user.email,
            name: user.fullName,
          },
        }),
        domain: new URL(page.url() || 'http://localhost:3000').hostname,
        path: '/',
        httpOnly: true,
        secure: false,
      },
    ]);
    await page.reload();
    return;
  }

  // Real Auth0 login flow
  await page.goto('/auth/login');
  await page.waitForURL(/auth0|\/auth\/login|\/auth\/callback/, {
    timeout: 10_000,
  });

  // Auth0 Universal Login form
  const emailInput = page.locator('input[name="email"], input[name="username"]');
  if (await emailInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await emailInput.fill(user.email);
    const passwordInput = page.locator('input[name="password"]');
    await passwordInput.fill(user.password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL('**/matters**', { timeout: 15_000 });
  }
}

/**
 * Log out of the current session.
 */
export async function logout(page: Page): Promise<void> {
  await page.goto('/auth/logout');
  await page.waitForURL(/auth0|login|\/$/, { timeout: 10_000 });
}

/**
 * Get an API access token for direct backend calls during test setup.
 */
export async function getTestApiToken(
  context: BrowserContext,
  userKey: TestUserKey,
): Promise<string> {
  // For mock auth, return a fixed token the test backend accepts
  if (process.env.E2E_MOCK_AUTH === 'true') {
    return `e2e-mock-token-${userKey}`;
  }

  // For real Auth0, retrieve from cookies after login
  const cookies = await context.cookies();
  const session = cookies.find((c) => c.name === 'appSession');
  if (session) {
    try {
      const parsed = JSON.parse(session.value);
      return parsed.accessToken ?? '';
    } catch {
      return '';
    }
  }
  return '';
}
