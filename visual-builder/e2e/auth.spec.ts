import { test, expect } from '@playwright/test';
import { mockAuthAPI, mockWorkflowAPI, loginAs, setupMocks } from './fixtures';

test.describe('Authentication Flow', () => {

  test.describe('Login', () => {
    test('shows login form on initial load', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('AgentChord')).toBeVisible();
      await expect(page.getByPlaceholder('you@example.com')).toBeVisible();
      await expect(page.getByPlaceholder('••••••••')).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });

    test('successful login redirects to dashboard', async ({ page }) => {
      await setupMocks(page);
      await page.goto('/');

      await page.getByPlaceholder('you@example.com').fill('test@example.com');
      await page.getByPlaceholder('••••••••').fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should redirect to workflow list
      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('test@example.com')).toBeVisible();
    });

    test('failed login shows error message', async ({ page }) => {
      await mockAuthAPI(page);
      await page.goto('/');

      await page.getByPlaceholder('you@example.com').fill('wrong@example.com');
      await page.getByPlaceholder('••••••••').fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show error
      await expect(page.getByText('Invalid credentials')).toBeVisible({ timeout: 5000 });
      // Should still be on login page
      await expect(page.getByPlaceholder('you@example.com')).toBeVisible();
    });

    test('sign in button disabled when fields empty', async ({ page }) => {
      await page.goto('/');
      const signInButton = page.getByRole('button', { name: /sign in/i });
      await expect(signInButton).toBeDisabled();
    });

    test('shows loading state during login', async ({ page }) => {
      // Delay the response to see loading state
      await page.route('**/api/auth/login', async (route) => {
        await new Promise(r => setTimeout(r, 1000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            user_id: 'user-1', email: 'test@example.com', role: 'user',
            token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEiLCJleHAiOjk5OTk5OTk5OTl9.mock',
          }),
        });
      });
      await mockWorkflowAPI(page);
      await page.goto('/');

      await page.getByPlaceholder('you@example.com').fill('test@example.com');
      await page.getByPlaceholder('••••••••').fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText('Please wait...')).toBeVisible();
    });
  });

  test.describe('Registration', () => {
    test('can switch to register mode', async ({ page }) => {
      await page.goto('/');
      await page.getByText("Don't have an account? Sign up").click();
      await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
      await expect(page.getByText('Create a new account')).toBeVisible();
    });

    test('successful registration redirects to dashboard', async ({ page }) => {
      await setupMocks(page);
      await page.goto('/');

      await page.getByText("Don't have an account? Sign up").click();
      await page.getByPlaceholder('you@example.com').fill('newuser@example.com');
      await page.getByPlaceholder('••••••••').fill('newpassword123');
      await page.getByRole('button', { name: /create account/i }).click();

      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
    });

    test('registration with existing email shows error', async ({ page }) => {
      await mockAuthAPI(page);
      await page.goto('/');

      await page.getByText("Don't have an account? Sign up").click();
      await page.getByPlaceholder('you@example.com').fill('existing@example.com');
      await page.getByPlaceholder('••••••••').fill('password123');
      await page.getByRole('button', { name: /create account/i }).click();

      await expect(page.getByText('Email already registered')).toBeVisible({ timeout: 5000 });
    });

    test('can switch back to login mode', async ({ page }) => {
      await page.goto('/');
      await page.getByText("Don't have an account? Sign up").click();
      await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();

      await page.getByText('Already have an account? Sign in').click();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });
  });

  test.describe('Logout', () => {
    test('logout returns to login page', async ({ page }) => {
      await setupMocks(page);
      await loginAs(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /logout/i }).click();

      await expect(page.getByPlaceholder('you@example.com')).toBeVisible({ timeout: 5000 });
    });

    test('logout clears auth state', async ({ page }) => {
      await setupMocks(page);
      await loginAs(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /logout/i }).click();

      // Check localStorage is cleared
      const authStorage = await page.evaluate(() => {
        const data = localStorage.getItem('auth-storage');
        return data ? JSON.parse(data) : null;
      });
      expect(authStorage?.state?.isAuthenticated).toBeFalsy();
    });
  });

  test.describe('Session Persistence', () => {
    test('stays logged in after page reload', async ({ page }) => {
      await setupMocks(page);
      await loginAs(page);
      await page.goto('/');

      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });

      // Reload page
      await page.reload();

      // Should still be on dashboard
      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('test@example.com')).toBeVisible();
    });
  });
});
