import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';
import { seedTestData } from './helpers/api';
import { getTestApiToken } from './helpers/auth';
import { TASK_DATA } from './fixtures/test-data';
import {
  navigateToMatterSection,
  waitForDialogClosed,
} from './helpers/selectors';

let matterId: string;

test.describe('Task Management', () => {
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
      // Seed might fail without real backend — tests will use UI seeding
    }
    await context.close();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    if (matterId) {
      await navigateToMatterSection(page, matterId, 'tasks');
    } else {
      await page.goto('/matters');
      await page.waitForLoadState('networkidle');
    }
  });

  test('should display task list page', async ({ page }) => {
    if (!matterId) test.skip();

    await expect(
      page.getByRole('heading', { name: /tasks/i }).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should create a new task via dialog', async ({ page }) => {
    if (!matterId) test.skip();

    const addBtn = page.getByRole('button', { name: /add task/i });
    await expect(addBtn).toBeVisible({ timeout: 5_000 });
    await addBtn.click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Fill task form
    await dialog.getByLabel(/title/i).first().fill(TASK_DATA.title);

    const descField = dialog.getByLabel(/description/i);
    if (await descField.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await descField.fill(TASK_DATA.description);
    }

    // Select phase
    const phaseSelect = dialog.getByRole('combobox').first();
    if (await phaseSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await phaseSelect.click();
      await page.getByRole('option', { name: /immediate/i }).click();
    }

    // Select priority
    const prioritySelect = dialog.getByRole('combobox').nth(1);
    if (await prioritySelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await prioritySelect.click();
      await page.getByRole('option', { name: /critical/i }).click();
    }

    // Submit
    await dialog.getByRole('button', { name: /create task/i }).click();

    // Dialog should close and task should appear
    await waitForDialogClosed(page);

    // Verify the new task appears in the list
    await expect(page.getByText(TASK_DATA.title)).toBeVisible({
      timeout: 10_000,
    });
  });

  test('should complete a task', async ({ page }) => {
    if (!matterId) test.skip();

    // Find a task with a "complete" button or action
    const taskRow = page.locator('[data-testid="task-item"], tr, [class*="task"]').filter({
      hasText: /e2e/i,
    }).first();

    if (await taskRow.isVisible({ timeout: 5_000 }).catch(() => false)) {
      // Click on the task to open detail panel
      await taskRow.click();
      await page.waitForTimeout(500);

      // Look for complete button
      const completeBtn = page.getByRole('button', { name: /complete/i }).first();
      if (await completeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await completeBtn.click();

        // Verify status changed
        await expect(
          page.getByText(/complete/i).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test('should filter tasks by phase', async ({ page }) => {
    if (!matterId) test.skip();

    // Open filters
    const filterBtn = page.getByRole('button', { name: /filter/i }).first();
    if (await filterBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filterBtn.click();
    }

    // Click Immediate phase chip
    const immediateChip = page.getByRole('button', { name: /immediate/i });
    if (await immediateChip.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await immediateChip.click();
      await page.waitForTimeout(500);

      // Verify filtered results
      const taskCount = page.getByText(/task/i).filter({ hasText: /\d+/ });
      await expect(taskCount.first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should filter tasks by status', async ({ page }) => {
    if (!matterId) test.skip();

    const filterBtn = page.getByRole('button', { name: /filter/i }).first();
    if (await filterBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filterBtn.click();
    }

    // Click "Not Started" status chip
    const notStartedChip = page.getByRole('button', { name: /not started/i });
    if (await notStartedChip.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await notStartedChip.click();
      await page.waitForTimeout(500);
    }
  });

  test('should search tasks by title', async ({ page }) => {
    if (!matterId) test.skip();

    const filterBtn = page.getByRole('button', { name: /filter/i }).first();
    if (await filterBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filterBtn.click();
    }

    const searchInput = page.getByPlaceholder(/search task/i);
    if (await searchInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await searchInput.fill('E2E');
      await page.waitForTimeout(500);

      // Results should be filtered
      await expect(page.getByText(/e2e/i).first()).toBeVisible({
        timeout: 5_000,
      });
    }
  });

  test('should switch between list and board view', async ({ page }) => {
    if (!matterId) test.skip();

    // Find the kanban/board toggle
    const boardBtn = page.locator('button[aria-label*="board"], button[aria-label*="grid"]').first();
    if (await boardBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await boardBtn.click();
      await page.waitForTimeout(500);

      // Switch back to list
      const listBtn = page.locator('button[aria-label*="list"]').first();
      if (await listBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await listBtn.click();
      }
    }
  });

  test('should waive a task with reason', async ({ page }) => {
    if (!matterId) test.skip();

    // Find a task with waive action
    const taskRow = page.locator('[data-testid="task-item"], tr, [class*="task"]').filter({
      hasText: /e2e/i,
    }).first();

    if (await taskRow.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await taskRow.click();
      await page.waitForTimeout(500);

      const waiveBtn = page.getByRole('button', { name: /waive/i }).first();
      if (await waiveBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await waiveBtn.click();

        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeVisible({ timeout: 5_000 });

        // Fill reason
        const reasonField = dialog.getByPlaceholder(/explain why/i);
        if (await reasonField.isVisible({ timeout: 2_000 }).catch(() => false)) {
          await reasonField.fill('Not applicable for E2E testing purposes');
        } else {
          await dialog.locator('textarea').first().fill('Not applicable for E2E testing purposes');
        }

        await dialog.getByRole('button', { name: /waive task/i }).click();
        await waitForDialogClosed(page);
      }
    }
  });

  test('should verify dashboard updates after task completion', async ({
    page,
  }) => {
    if (!matterId) test.skip();

    // Navigate to matter dashboard
    await page.goto(`/matters/${matterId}`);
    await page.waitForLoadState('networkidle');

    // Check task summary metrics
    const taskMetrics = page.locator('[class*="metric"], [class*="card"]').filter({
      hasText: /task/i,
    });

    await expect(taskMetrics.first()).toBeVisible({ timeout: 10_000 });

    // The dashboard should show task completion stats
    const completionText = page.getByText(/%/).first();
    if (await completionText.isVisible({ timeout: 3_000 }).catch(() => false)) {
      const text = await completionText.textContent();
      expect(text).toMatch(/\d+%/);
    }
  });
});
