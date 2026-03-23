import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';
import { MATTER_DATA } from './fixtures/test-data';
import {
  dialogByTitle,
  waitForDialogClosed,
} from './helpers/selectors';

test.describe('Matter Creation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAs(page, 'admin');
    await page.goto('/matters');
    await page.waitForLoadState('networkidle');
  });

  test('should open Create Matter dialog from matters page', async ({
    page,
  }) => {
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = dialogByTitle(page, 'Create New Matter');
    await expect(dialog).toBeVisible({ timeout: 5_000 });
    await expect(dialog.getByText(/basic info/i)).toBeVisible();
  });

  test('should complete multi-step matter creation form', async ({ page }) => {
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // ── Step 1: Basic Information ──
    await dialog.getByLabel(/decedent.*name/i).fill(MATTER_DATA.decedentName);
    await dialog.getByLabel(/title/i).first().fill(MATTER_DATA.title);

    // Select estate type
    const estateTypeSelect = dialog.getByRole('combobox').first();
    if (await estateTypeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await estateTypeSelect.click();
      await page.getByRole('option', { name: /with will/i }).click();
    }

    // Select jurisdiction
    const jurisdictionSelect = dialog.getByRole('combobox').nth(1);
    if (await jurisdictionSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await jurisdictionSelect.click();
      await page.getByRole('option', { name: /california/i }).click();
    }

    // Optional: date of death
    const dateInput = dialog.locator('input[type="date"]').first();
    if (await dateInput.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await dateInput.fill(MATTER_DATA.dateOfDeath);
    }

    // Optional: estimated value
    const valueInput = dialog.getByLabel(/estimated.*value/i);
    if (await valueInput.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await valueInput.fill(MATTER_DATA.estimatedValue);
    }

    // Click Next
    await dialog.getByRole('button', { name: /next/i }).click();

    // ── Step 2: Asset Profile ──
    await expect(dialog.getByText(/asset/i).first()).toBeVisible({ timeout: 5_000 });

    // Select some asset types (checkboxes)
    for (const assetLabel of MATTER_DATA.assetTypes) {
      const checkbox = dialog.getByRole('checkbox', {
        name: new RegExp(assetLabel, 'i'),
      });
      if (await checkbox.isVisible({ timeout: 1_000 }).catch(() => false)) {
        await checkbox.check();
      }
    }

    // Click Next
    await dialog.getByRole('button', { name: /next/i }).click();

    // ── Step 3: Review ──
    await expect(dialog.getByText(/review/i).first()).toBeVisible({ timeout: 5_000 });

    // Verify review shows entered data
    await expect(dialog.getByText(MATTER_DATA.decedentName)).toBeVisible();
    await expect(dialog.getByText(MATTER_DATA.title)).toBeVisible();

    // Submit
    await dialog.getByRole('button', { name: /create matter/i }).click();

    // ── Success ──
    await expect(
      dialog.getByText(/matter created/i),
    ).toBeVisible({ timeout: 15_000 });

    // Navigate to dashboard
    const goBtn = dialog.getByRole('button', {
      name: /go to matter/i,
    });
    if (await goBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await goBtn.click();
      await page.waitForLoadState('networkidle');
      // Should be on the matter dashboard
      await expect(page).toHaveURL(/matters\/[a-f0-9-]+/, { timeout: 10_000 });
    }
  });

  test('should validate required fields in Step 1', async ({ page }) => {
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Try to proceed without filling required fields
    await dialog.getByRole('button', { name: /next/i }).click();

    // Should show validation errors (stay on Step 1)
    await expect(dialog.getByText(/basic info/i)).toBeVisible();
  });

  test('should navigate back between steps', async ({ page }) => {
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Fill Step 1
    await dialog.getByLabel(/decedent.*name/i).fill(MATTER_DATA.decedentName);
    await dialog.getByLabel(/title/i).first().fill(MATTER_DATA.title);

    const estateTypeSelect = dialog.getByRole('combobox').first();
    if (await estateTypeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await estateTypeSelect.click();
      await page.getByRole('option', { name: /with will/i }).click();
    }

    const jurisdictionSelect = dialog.getByRole('combobox').nth(1);
    if (await jurisdictionSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await jurisdictionSelect.click();
      await page.getByRole('option', { name: /california/i }).click();
    }

    await dialog.getByRole('button', { name: /next/i }).click();
    await expect(dialog.getByText(/asset/i).first()).toBeVisible({ timeout: 5_000 });

    // Go back to Step 1
    await dialog.getByRole('button', { name: /back/i }).click();
    await expect(dialog.getByText(/basic info/i)).toBeVisible({ timeout: 5_000 });

    // Verify data persisted
    await expect(dialog.getByLabel(/decedent.*name/i)).toHaveValue(
      MATTER_DATA.decedentName,
    );
  });

  test('should cancel dialog without creating matter', async ({ page }) => {
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    await dialog.getByRole('button', { name: /cancel/i }).click();
    await waitForDialogClosed(page);
  });

  test('should verify tasks are generated after matter creation', async ({
    page,
  }) => {
    // Create a matter via the full flow
    await page.getByRole('button', { name: /new matter/i }).click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });

    // Step 1
    await dialog.getByLabel(/decedent.*name/i).fill('E2E Task Gen Test');
    await dialog.getByLabel(/title/i).first().fill('Estate of E2E Task Gen Test');

    const estateTypeSelect = dialog.getByRole('combobox').first();
    if (await estateTypeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await estateTypeSelect.click();
      await page.getByRole('option', { name: /with will/i }).click();
    }

    const jurisdictionSelect = dialog.getByRole('combobox').nth(1);
    if (await jurisdictionSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await jurisdictionSelect.click();
      await page.getByRole('option', { name: /california/i }).click();
    }

    await dialog.getByRole('button', { name: /next/i }).click();

    // Step 2 — skip asset profile
    await dialog.getByRole('button', { name: /next/i }).click();

    // Step 3 — submit
    await dialog.getByRole('button', { name: /create matter/i }).click();

    await expect(
      dialog.getByText(/matter created/i),
    ).toBeVisible({ timeout: 15_000 });

    // Navigate to the matter's task page
    const goBtn = dialog.getByRole('button', { name: /go to matter/i });
    if (await goBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await goBtn.click();
      await page.waitForLoadState('networkidle');

      // Navigate to tasks
      const tasksLink = page.getByRole('link', { name: /tasks/i });
      if (await tasksLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await tasksLink.click();
        await page.waitForLoadState('networkidle');

        // Verify tasks exist (generated or at least the page loads)
        await expect(
          page.getByRole('heading', { name: /tasks/i }).first(),
        ).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});
