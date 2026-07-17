import { test, expect } from '@playwright/test';

test('Chat input is available', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', {
    name: /initialize system/i,
  }).click();

  await expect(
    page.getByPlaceholder(/Ask something about your PDFs/i)
  ).toBeVisible();
});