import { test, expect } from '@playwright/test';
import { mockAuthAPI } from './fixtures';

test.describe('Application Health', () => {
  test('loads the login page', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AgentWeave')).toBeVisible();
  });

  test('shows sign in form', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible();
    await expect(page.getByPlaceholder('••••••••')).toBeVisible();
  });

  test('shows sign up link', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/sign up/i)).toBeVisible();
  });

  test('can switch to register mode', async ({ page }) => {
    await page.goto('/');
    await page.getByText(/sign up/i).click();
    await expect(page.getByText(/create account/i)).toBeVisible();
  });

  test('shows error on invalid login', async ({ page }) => {
    await mockAuthAPI(page);
    await page.goto('/');
    await page.getByPlaceholder('you@example.com').fill('test@test.com');
    await page.getByPlaceholder('••••••••').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();
    // Should show error message (Invalid credentials from mock)
    await expect(page.getByText('Invalid credentials')).toBeVisible({ timeout: 5000 });
  });
});
