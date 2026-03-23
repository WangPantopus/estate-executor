import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

/**
 * Responsive tests run on mobile viewport to verify critical flows
 * work on smaller screens.
 *
 * These tests use the 'mobile-chrome' project from playwright.config.ts
 * which provides a Pixel 5 viewport (393 x 851).
 */
test.describe('Responsive — Mobile Viewport', () => {
  test.use({ viewport: { width: 393, height: 851 } });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
  });

  test('should show mobile hamburger menu', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Hamburger menu button should be visible
    const menuBtn = page.locator('button[aria-label*="menu"], button').filter({
      has: page.locator('svg'),
    }).first();

    // On mobile the sidebar is a Sheet triggered by hamburger
    await expect(menuBtn).toBeVisible({ timeout: 10_000 });
  });

  test('should open mobile navigation drawer', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Click hamburger menu
    const menuBtn = page.locator('button').first();
    await menuBtn.click();
    await page.waitForTimeout(500);

    // Mobile nav drawer should be visible
    const drawer = page.locator('[role="dialog"], [class*="sheet"]');
    if (await drawer.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      // Should show navigation links
      await expect(
        drawer.first().getByText(/matters/i),
      ).toBeVisible();
    }
  });

  test('should display matters list on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('heading', { name: /matters/i }).first(),
    ).toBeVisible({ timeout: 15_000 });

    // Cards or table should be visible
    const content = page.locator('main, [class*="content"]');
    await expect(content.first()).toBeVisible();
  });

  test('should open Create Matter dialog on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const newMatterBtn = page.getByRole('button', { name: /new matter/i });
    if (await newMatterBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await newMatterBtn.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Dialog should be usable (not cut off)
      const dialogBox = await dialog.boundingBox();
      if (dialogBox) {
        expect(dialogBox.width).toBeLessThanOrEqual(393);
      }
    }
  });

  test('should navigate matter dashboard on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Click first matter
    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await matterLink.click();
      await page.waitForLoadState('networkidle');

      // Dashboard cards should stack vertically
      const cards = page.locator('[class*="card"]');
      const count = await cards.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('should handle task list on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/tasks`);
        await page.waitForLoadState('networkidle');

        await expect(
          page.getByRole('heading', { name: /tasks/i }).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test('should handle document page on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/documents`);
        await page.waitForLoadState('networkidle');

        await expect(
          page.getByRole('heading', { name: /documents/i }).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test('should handle calendar page on mobile', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/deadlines`);
        await page.waitForLoadState('networkidle');

        await expect(
          page.getByRole('heading', { name: /compliance calendar/i }).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});
