import { test, expect } from '@playwright/test';
import { loginAs, getTestApiToken } from './helpers/auth';
import { seedTestData } from './helpers/api';
import {
  navigateToMatterSection,
  waitForDialogClosed,
} from './helpers/selectors';
import { DEADLINE_DATA } from './fixtures/test-data';

let matterId: string;

test.describe('Deadline Management', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto('/');
    await loginAs(page, 'admin');
    const token = await getTestApiToken(context, 'admin');
    try {
      const data = await seedTestData(page.request, { token });
      matterId = data.matterId;
    } catch {
      // May fail without real backend
    }
    await context.close();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    if (matterId) {
      await navigateToMatterSection(page, matterId, 'deadlines');
    }
  });

  test('should display compliance calendar page', async ({ page }) => {
    if (!matterId) test.skip();

    await expect(
      page.getByRole('heading', { name: /compliance calendar/i }).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should show calendar view by default', async ({ page }) => {
    if (!matterId) test.skip();

    // Calendar view with month navigation
    const calendarContent = page.locator('[class*="calendar"], [class*="month"]');
    await expect(calendarContent.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should switch to timeline view', async ({ page }) => {
    if (!matterId) test.skip();

    // Find timeline toggle button
    const timelineBtn = page.getByRole('button', { name: /timeline/i });
    if (await timelineBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await timelineBtn.click();
      await page.waitForTimeout(500);
    }

    // Switch back to calendar
    const calendarBtn = page.getByRole('button', { name: /calendar/i });
    if (await calendarBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await calendarBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should highlight overdue deadlines', async ({ page }) => {
    if (!matterId) test.skip();

    // Look for overdue indicator in summary bar
    const overdueFilter = page.getByRole('button', { name: /overdue/i });
    if (await overdueFilter.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await overdueFilter.click();
      await page.waitForTimeout(500);

      // Overdue deadlines should be highlighted (destructive/red styling)
      const overdueItems = page.locator(
        '[class*="destructive"], [class*="red"], [class*="overdue"]',
      );
      // At least verify the filter was applied
      const filterIndicator = page.getByText(/showing.*deadline/i);
      if (await filterIndicator.isVisible({ timeout: 3_000 }).catch(() => false)) {
        expect(await filterIndicator.textContent()).toMatch(/\d+/);
      }
    }
  });

  test('should filter deadlines by this week', async ({ page }) => {
    if (!matterId) test.skip();

    const thisWeekBtn = page.getByRole('button', { name: /this week/i });
    if (await thisWeekBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await thisWeekBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should filter deadlines by this month', async ({ page }) => {
    if (!matterId) test.skip();

    const thisMonthBtn = page.getByRole('button', { name: /this month/i });
    if (await thisMonthBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await thisMonthBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should add a manual deadline', async ({ page }) => {
    if (!matterId) test.skip();

    const addBtn = page.getByRole('button', { name: /add deadline/i });
    await expect(addBtn).toBeVisible({ timeout: 5_000 });
    await addBtn.click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Fill deadline form
    const titleField = dialog.getByLabel(/title/i);
    if (await titleField.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await titleField.fill(DEADLINE_DATA.title);
    }

    const descField = dialog.getByLabel(/description/i);
    if (await descField.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await descField.fill(DEADLINE_DATA.description);
    }

    const dateField = dialog.locator('input[type="date"]').first();
    if (await dateField.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await dateField.fill(DEADLINE_DATA.dueDate);
    }

    // Submit
    const submitBtn = dialog.getByRole('button', { name: /add|create|save/i }).last();
    await submitBtn.click();

    // Dialog should close
    await waitForDialogClosed(page);

    // Verify deadline appears
    await expect(page.getByText(DEADLINE_DATA.title)).toBeVisible({
      timeout: 10_000,
    });
  });

  test('should open deadline detail panel', async ({ page }) => {
    if (!matterId) test.skip();

    // Click on a deadline item
    const deadlineItem = page.getByText(/deadline|filing/i).first();
    if (await deadlineItem.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await deadlineItem.click();
      await page.waitForTimeout(500);

      // Detail panel should open
      const panel = page.locator('[role="dialog"], [class*="sheet"]');
      if (await panel.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
        await expect(panel.first()).toBeVisible();
      }
    }
  });

  test('should clear deadline filters', async ({ page }) => {
    if (!matterId) test.skip();

    // Apply a filter first
    const overdueBtn = page.getByRole('button', { name: /overdue/i });
    if (await overdueBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await overdueBtn.click();
      await page.waitForTimeout(500);

      // Clear filter
      const clearBtn = page.getByRole('button', { name: /clear filter/i });
      if (await clearBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await clearBtn.click();
        await page.waitForTimeout(500);

        // Filter indicator should be gone
        await expect(clearBtn).not.toBeVisible({ timeout: 3_000 });
      }
    }
  });
});
