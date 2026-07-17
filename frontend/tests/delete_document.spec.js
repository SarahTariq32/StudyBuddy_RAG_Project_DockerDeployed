import { test, expect } from '@playwright/test';

test('Documents page loads', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', {
    name: /initialize system/i,
  }).click();

  await expect(
    page.getByText(/YOUR PDFs/i)
  ).toBeVisible();
});