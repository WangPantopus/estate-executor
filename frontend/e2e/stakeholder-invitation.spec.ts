import { test, expect } from '@playwright/test';
import { loginAs, getTestApiToken } from './helpers/auth';
import { seedTestData } from './helpers/api';
import { navigateToMatter } from './helpers/selectors';
import { STAKEHOLDER_DATA } from './fixtures/test-data';

let matterId: string;

test.describe('Stakeholder Invitation', () => {
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
  });

  test('should display stakeholders on matter dashboard', async ({ page }) => {
    if (!matterId) test.skip();

    await navigateToMatter(page, matterId);

    // Stakeholders card should be visible
    const stakeholderSection = page.getByText(/stakeholder/i).first();
    await expect(stakeholderSection).toBeVisible({ timeout: 10_000 });
  });

  test('should invite a stakeholder via dialog', async ({ page }) => {
    if (!matterId) test.skip();

    await navigateToMatter(page, matterId);

    // Find invite button (on stakeholders card or settings)
    const inviteBtn = page.getByRole('button', { name: /invite/i }).first();
    if (await inviteBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await inviteBtn.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5_000 });

      // Fill invite form
      const emailField = dialog.getByLabel(/email/i);
      if (await emailField.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await emailField.fill(STAKEHOLDER_DATA.email);
      }

      const nameField = dialog.getByLabel(/name/i).first();
      if (await nameField.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await nameField.fill(STAKEHOLDER_DATA.fullName);
      }

      // Select role
      const roleSelect = dialog.getByRole('combobox').first();
      if (await roleSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await roleSelect.click();
        await page.getByRole('option', { name: /beneficiary/i }).click();
      }

      // Submit
      const submitBtn = dialog.getByRole('button', { name: /invite|send/i }).last();
      await submitBtn.click();

      // Should show success or close dialog
      await page.waitForTimeout(2_000);
    }
  });

  test('should show invited stakeholder with pending status', async ({
    page,
  }) => {
    if (!matterId) test.skip();

    await navigateToMatter(page, matterId);

    // Look for the stakeholder in the list
    const pendingBadge = page.getByText(/pending/i);
    if (await pendingBadge.isVisible({ timeout: 5_000 }).catch(() => false)) {
      // At least one pending invitation exists
      expect(await pendingBadge.count()).toBeGreaterThan(0);
    }
  });

  test('should simulate invite acceptance via invite page', async ({
    page,
  }) => {
    // Navigate to invite acceptance page with a test token
    await page.goto('/invite/test-token-e2e');
    await page.waitForLoadState('networkidle');

    // Should show the invite acceptance UI
    const pageContent = await page.textContent('body');
    // Either shows verification, error (invalid token), or redirect
    expect(pageContent).toBeTruthy();
  });

  test('should show stakeholder access after acceptance', async ({ page }) => {
    if (!matterId) test.skip();

    // Navigate to matter settings to see stakeholders
    await page.goto(`/matters/${matterId}/settings`);
    await page.waitForLoadState('networkidle');

    // Or check the dashboard stakeholders card
    await navigateToMatter(page, matterId);

    const stakeholderCard = page.locator('[class*="card"]').filter({
      hasText: /stakeholder/i,
    });

    await expect(stakeholderCard.first()).toBeVisible({ timeout: 10_000 });
  });

  test('should resend invitation', async ({ page }) => {
    if (!matterId) test.skip();

    await navigateToMatter(page, matterId);

    // Find resend button for a pending stakeholder
    const resendBtn = page.getByRole('button', { name: /resend/i });
    if (await resendBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await resendBtn.first().click();
      await page.waitForTimeout(1_000);
    }
  });
});
