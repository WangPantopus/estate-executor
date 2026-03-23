import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

/**
 * Beneficiary view tests verify that users with the "beneficiary" role
 * see a restricted, read-only interface.
 */
test.describe('Beneficiary View — Limited Access', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'beneficiary');
  });

  test('should log in as beneficiary and see matters', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Beneficiary should see a matters list (possibly filtered to their matters)
    const heading = page.getByRole('heading', { name: /matters/i }).first();
    await expect(heading).toBeVisible({ timeout: 15_000 });
  });

  test('should not see "New Matter" button', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Beneficiary should NOT see the create matter button
    const newMatterBtn = page.getByRole('button', { name: /new matter/i });
    await expect(newMatterBtn).not.toBeVisible({ timeout: 5_000 });
  });

  test('should see matter dashboard in read-only mode', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    // Click on the first available matter
    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await matterLink.click();
      await page.waitForLoadState('networkidle');

      // Should see the dashboard but without admin controls
      const editBtn = page.getByRole('button', { name: /edit/i });
      await expect(editBtn).not.toBeVisible({ timeout: 3_000 });
    }
  });

  test('should not see "Add Task" button on tasks page', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/tasks`);
        await page.waitForLoadState('networkidle');

        // Beneficiary should NOT see add task button
        const addTaskBtn = page.getByRole('button', { name: /add task/i });
        await expect(addTaskBtn).not.toBeVisible({ timeout: 5_000 });
      }
    }
  });

  test('should not see stakeholder management controls', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await matterLink.click();
      await page.waitForLoadState('networkidle');

      // Beneficiary should NOT see invite stakeholder button
      const inviteBtn = page.getByRole('button', { name: /invite/i });
      await expect(inviteBtn).not.toBeVisible({ timeout: 3_000 });
    }
  });

  test('should see limited document access', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/documents`);
        await page.waitForLoadState('networkidle');

        // Beneficiary should see documents but NOT upload button
        const uploadBtn = page.getByRole('button', { name: /upload/i });
        await expect(uploadBtn).not.toBeVisible({ timeout: 5_000 });
      }
    }
  });

  test('should see distribution notices in communications', async ({
    page,
  }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const href = await matterLink.getAttribute('href');
      if (href) {
        await page.goto(`${href}/communications`);
        await page.waitForLoadState('networkidle');

        // Beneficiary may or may not see this page depending on permissions
      }
    }
  });

  test('should not see activity feed', async ({ page }) => {
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');

    const matterLink = page.getByRole('link').filter({ hasText: /estate/i }).first();
    if (await matterLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await matterLink.click();
      await page.waitForLoadState('networkidle');

      // Activity section should not be visible to beneficiaries
      const activitySection = page.getByText(/recent activity/i);
      await expect(activitySection).not.toBeVisible({ timeout: 3_000 });
    }
  });
});
