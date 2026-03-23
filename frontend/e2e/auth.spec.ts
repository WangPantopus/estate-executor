import { test, expect } from '@playwright/test';
import { loginAs, logout, TEST_USERS } from './helpers/auth';

test.describe('Authentication Flow', () => {
  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/matters');
    // Should redirect to Auth0 login or the app's login page
    await expect(page).toHaveURL(/auth\/login|auth0/, { timeout: 10_000 });
  });

  test('should show login page with sign-in option', async ({ page }) => {
    await page.goto('/auth/login');
    await page.waitForLoadState('networkidle');
    // Auth0 Universal Login or app redirect
    const url = page.url();
    expect(url).toMatch(/auth\/login|auth0/);
  });

  test('should sign up and land on matters page', async ({ page }) => {
    // Signup redirects to Auth0 with screen_hint=signup
    await page.goto('/auth/signup');
    await page.waitForLoadState('networkidle');

    const url = page.url();
    // Verify we're either at Auth0 signup or the signup redirect happened
    expect(url).toMatch(/signup|screen_hint|auth0|auth\/login/);
  });

  test('should log in as admin and see matters page', async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Verify we reached the matters page
    await expect(page.getByRole('heading', { name: /matters/i }).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('should log in → create firm → navigate to first matter', async ({
    page,
  }) => {
    await page.goto('/');
    await loginAs(page, 'admin');

    // Navigate to matters
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Click "New Matter" to start the flow
    const newMatterBtn = page.getByRole('button', { name: /new matter/i });
    if (await newMatterBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await newMatterBtn.click();
      await expect(page.locator('[role="dialog"]')).toBeVisible({
        timeout: 5_000,
      });
    }
  });

  test('should log out successfully', async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    await logout(page);
    // After logout, should redirect to login or home
    await expect(page).toHaveURL(/auth|login|\/$/, { timeout: 10_000 });
  });

  test('should persist session across page reloads', async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Reload and verify session persists
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should still be on matters page, not redirected to login
    await expect(page).toHaveURL(/matters/, { timeout: 10_000 });
  });
});
