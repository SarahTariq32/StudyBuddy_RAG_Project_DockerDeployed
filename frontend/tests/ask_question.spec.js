import { test, expect } from '@playwright/test';

test('User can ask a question', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', {
    name: /initialize system/i,
  }).click();

  const input = page.getByPlaceholder(/Ask something about your PDFs/i);

  await expect(input).toBeVisible();

  await input.fill('Hello');

  await page.keyboard.press('Enter');

  // If the backend is working, the loading text should appear.
  await expect(
    page.getByText('Thinking...')
  ).toBeVisible();
});