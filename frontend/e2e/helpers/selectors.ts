/**
 * Common selectors and helper functions for E2E tests.
 * Centralises locator strategies for reuse across test files.
 */
import { type Page, type Locator, expect } from '@playwright/test';

// ─── Navigation ────────────────────────────────────────────────────────

export function sidebarLink(page: Page, name: string): Locator {
  return page.getByRole('link', { name: new RegExp(name, 'i') });
}

export async function navigateToMatter(
  page: Page,
  matterId: string,
): Promise<void> {
  await page.goto(`/matters/${matterId}`);
  await page.waitForLoadState('networkidle');
}

export async function navigateToMatterSection(
  page: Page,
  matterId: string,
  section: string,
): Promise<void> {
  await page.goto(`/matters/${matterId}/${section}`);
  await page.waitForLoadState('networkidle');
}

// ─── Dialogs ───────────────────────────────────────────────────────────

export function dialogByTitle(page: Page, title: string | RegExp): Locator {
  const titleRegex = typeof title === 'string' ? new RegExp(title, 'i') : title;
  return page.locator('[role="dialog"]').filter({
    has: page.getByRole('heading', { name: titleRegex }),
  });
}

export async function waitForDialogClosed(page: Page): Promise<void> {
  await expect(page.locator('[role="dialog"]')).toHaveCount(0, {
    timeout: 10_000,
  });
}

// ─── Forms ─────────────────────────────────────────────────────────────

export async function fillSelect(
  page: Page,
  triggerText: string | RegExp,
  optionText: string | RegExp,
): Promise<void> {
  // Radix Select: click trigger, then click option
  const trigger = page.getByRole('combobox').filter({ hasText: triggerText });
  if (await trigger.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await trigger.click();
    await page.getByRole('option', { name: optionText }).click();
    return;
  }

  // Fallback: native select
  const nativeSelect = page.locator('select').filter({ hasText: triggerText });
  if (await nativeSelect.isVisible({ timeout: 1_000 }).catch(() => false)) {
    await nativeSelect.selectOption({ label: optionText.toString() });
  }
}

// ─── Assertions ────────────────────────────────────────────────────────

export async function expectToastMessage(
  page: Page,
  text: string | RegExp,
): Promise<void> {
  const toast = page.locator('[role="status"], [role="alert"]').filter({
    hasText: typeof text === 'string' ? new RegExp(text, 'i') : text,
  });
  await expect(toast.first()).toBeVisible({ timeout: 10_000 });
}

export async function expectPageHeading(
  page: Page,
  text: string | RegExp,
): Promise<void> {
  await expect(
    page.getByRole('heading', { name: text }).first(),
  ).toBeVisible({ timeout: 10_000 });
}

// ─── Waiting ───────────────────────────────────────────────────────────

export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  status = 200,
): Promise<void> {
  await page.waitForResponse(
    (res) =>
      (typeof urlPattern === 'string'
        ? res.url().includes(urlPattern)
        : urlPattern.test(res.url())) && res.status() === status,
    { timeout: 15_000 },
  );
}
