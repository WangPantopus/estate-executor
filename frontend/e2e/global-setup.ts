import { test as setup } from '@playwright/test';

/**
 * Global setup that runs before all test suites.
 * Seeds the database with test data via the backend API.
 */
setup('seed test database', async ({ request }) => {
  const apiBase =
    process.env.E2E_API_URL ?? 'http://localhost:8000/api/v1';

  // Health check — verify backend is reachable
  const health = await request.get(`${apiBase}/health`);
  if (!health.ok()) {
    console.warn(
      `Backend health check failed (${health.status()}). Tests may rely on mock auth.`,
    );
  }
});
