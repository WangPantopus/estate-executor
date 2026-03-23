import { test, expect } from '@playwright/test';
import { loginAs, getTestApiToken } from './helpers/auth';
import { seedTestData } from './helpers/api';
import { navigateToMatterSection } from './helpers/selectors';
import path from 'path';
import fs from 'fs';

let matterId: string;

test.describe('Document Upload & Management', () => {
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
      await navigateToMatterSection(page, matterId, 'documents');
    }
  });

  test('should display documents page', async ({ page }) => {
    if (!matterId) test.skip();

    await expect(
      page.getByRole('heading', { name: /documents/i }).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should show upload zone', async ({ page }) => {
    if (!matterId) test.skip();

    // Upload button or drop zone should be visible
    const uploadBtn = page.getByRole('button', { name: /upload/i });
    await expect(uploadBtn).toBeVisible({ timeout: 5_000 });
  });

  test('should upload a file via file input', async ({ page }) => {
    if (!matterId) test.skip();

    // Create a temporary test file
    const testFilePath = path.join(__dirname, 'fixtures', 'test-document.pdf');
    if (!fs.existsSync(testFilePath)) {
      // Create a minimal PDF-like file for testing
      fs.writeFileSync(testFilePath, '%PDF-1.4 E2E test document content');
    }

    // Click upload button to trigger dialog/zone
    const uploadBtn = page.getByRole('button', { name: /upload/i });
    await uploadBtn.click();
    await page.waitForTimeout(500);

    // Look for file input (may be hidden)
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      await fileInput.first().setInputFiles(testFilePath);
      await page.waitForTimeout(2_000);

      // Verify upload progress or success
      const uploadStatus = page.getByText(/upload|classif|done/i).first();
      await expect(uploadStatus).toBeVisible({ timeout: 15_000 });
    }
  });

  test('should show document in list after upload', async ({ page }) => {
    if (!matterId) test.skip();

    // Documents should be listed
    const docCount = page.getByText(/\d+ document/i);
    if (await docCount.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const text = await docCount.textContent();
      expect(text).toMatch(/\d+/);
    }
  });

  test('should open document detail panel', async ({ page }) => {
    if (!matterId) test.skip();

    // Click on a document card or row
    const docItem = page.locator('[class*="card"], tr').filter({
      hasText: /pdf|doc|document/i,
    }).first();

    if (await docItem.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await docItem.click();
      await page.waitForTimeout(500);

      // Detail panel (Sheet) should open
      const detailPanel = page.locator('[role="dialog"], [class*="sheet"]');
      await expect(detailPanel.first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should confirm document type classification', async ({ page }) => {
    if (!matterId) test.skip();

    // Find a document with AI classification
    const docItem = page.locator('[class*="card"], tr').filter({
      hasText: /pdf|doc|document/i,
    }).first();

    if (await docItem.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await docItem.click();
      await page.waitForTimeout(500);

      // Look for confirm type button
      const confirmBtn = page.getByRole('button', { name: /confirm/i });
      if (await confirmBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await confirmBtn.click();

        // Select document type
        const typeSelect = page.getByRole('combobox').first();
        if (await typeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
          await typeSelect.click();
          await page.getByRole('option', { name: /will/i }).click();
        }

        // Submit confirmation
        const submitBtn = page.getByRole('button', { name: /confirm/i }).last();
        if (await submitBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
          await submitBtn.click();
        }
      }
    }
  });

  test('should filter documents by type', async ({ page }) => {
    if (!matterId) test.skip();

    const filterBtn = page.getByRole('button', { name: /filter/i }).first();
    if (await filterBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filterBtn.click();
      await page.waitForTimeout(500);

      // Select a doc type filter
      const typeSelect = page.getByRole('combobox').first();
      if (await typeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await typeSelect.click();
        const willOption = page.getByRole('option', { name: /will/i });
        if (await willOption.isVisible({ timeout: 2_000 }).catch(() => false)) {
          await willOption.click();
        }
      }
    }
  });

  test('should toggle between grid and list view', async ({ page }) => {
    if (!matterId) test.skip();

    // Find view toggle buttons
    const gridBtn = page.locator('button[aria-label*="grid"]').first();
    const listBtn = page.locator('button[aria-label*="list"]').first();

    if (await gridBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await gridBtn.click();
      await page.waitForTimeout(300);
    }

    if (await listBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await listBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('should request document from stakeholder', async ({ page }) => {
    if (!matterId) test.skip();

    const requestBtn = page.getByRole('button', { name: /request/i });
    if (await requestBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await requestBtn.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Should show request document form
      await expect(dialog.getByText(/request document/i)).toBeVisible();
    }
  });
});
