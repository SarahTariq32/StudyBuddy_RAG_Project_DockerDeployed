import { test, expect } from '@playwright/test';
import path from 'path';

test('Upload a PDF successfully', async ({ page }) => {
  await page.goto('/');

  // Open chat page
  await page.getByRole('button', { name: /initialize system/i }).click();

  // Wait for chat page
  await expect(
    page.getByPlaceholder(/Ask something about your PDFs/i)
  ).toBeVisible();

  // Upload directly to the hidden input
  const pdfPath = path.resolve(
    'tests',
    'fixtures',
    'test.pdf'
  );

  await page
    .locator('input[type="file"]')
    .setInputFiles(pdfPath);

  // Wait until upload finishes
  await expect(
    page.getByText(
        'test.pdf uploaded. Indexing in progress...'
    )
    ).toBeVisible({
    timeout: 60000,
    });
});