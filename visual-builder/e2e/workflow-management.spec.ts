import { test, expect } from '@playwright/test';
import { setupMocks, loginAs } from './fixtures';

test.describe('Workflow Management', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await loginAs(page);
  });

  test.describe('Workflow List', () => {
    test('displays all workflows', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });
      await expect(page.getByRole('heading', { name: 'Data Pipeline' })).toBeVisible();
      await expect(page.getByText('Customer Support Bot')).toBeVisible();
    });

    test('shows workflow details', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Processes incoming emails')).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('2 nodes')).toBeVisible();
    });

    test('shows empty state when no workflows', async ({ page }) => {
      // Override workflow API to return empty list
      await page.route('**/api/workflows', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workflows: [] }) });
        } else {
          await route.continue();
        }
      });
      await page.goto('/');
      await expect(page.getByText('No workflows yet')).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('Create your first workflow')).toBeVisible();
    });
  });

  test.describe('Search', () => {
    test('filters workflows by name', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.getByPlaceholder('Search workflows...').fill('Email');
      await expect(page.getByText('Email Processor')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Data Pipeline' })).not.toBeVisible();
      await expect(page.getByText('Customer Support Bot')).not.toBeVisible();
    });

    test('filters workflows by description', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.getByPlaceholder('Search workflows...').fill('ETL');
      await expect(page.getByRole('heading', { name: 'Data Pipeline' })).toBeVisible();
      await expect(page.getByText('Email Processor')).not.toBeVisible();
    });

    test('shows no results message', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.getByPlaceholder('Search workflows...').fill('nonexistent');
      await expect(page.getByText(/No workflows matching/)).toBeVisible();
    });

    test('search is case-insensitive', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.getByPlaceholder('Search workflows...').fill('email processor');
      await expect(page.getByText('Email Processor')).toBeVisible();
    });
  });

  test.describe('Sort', () => {
    test('sorts by name A-Z', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.locator('select').selectOption('name-asc');

      const cards = page.locator('h3');
      await expect(cards.first()).toHaveText('Customer Support Bot');
    });

    test('sorts by name Z-A', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.locator('select').selectOption('name-desc');

      const cards = page.locator('h3');
      await expect(cards.first()).toHaveText('Email Processor');
    });
  });

  test.describe('Create Workflow', () => {
    test('clicking New Workflow navigates to editor', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });

      await page.getByRole('button', { name: /new workflow/i }).click();
      await expect(page).toHaveURL(/\/workflows\/new/);
    });

    test('empty state create button navigates to editor', async ({ page }) => {
      await page.route('**/api/workflows', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ workflows: [] }) });
        } else {
          await route.continue();
        }
      });
      await page.goto('/');
      await expect(page.getByText('Create your first workflow')).toBeVisible({ timeout: 10000 });

      await page.getByText('Create your first workflow').click();
      await expect(page).toHaveURL(/\/workflows\/new/);
    });
  });

  test.describe('Open Workflow', () => {
    test('clicking a workflow card navigates to editor', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      await page.getByText('Email Processor').click();
      await expect(page).toHaveURL(/\/workflows\/wf-1/);
    });
  });

  test.describe('Delete Workflow', () => {
    test('shows confirmation dialog before deleting', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('Email Processor')).toBeVisible({ timeout: 10000 });

      // Hover to reveal action buttons, then click delete
      const card = page.locator('.group').filter({ hasText: 'Email Processor' });
      await card.hover();
      await card.locator('button').filter({ has: page.locator('.text-destructive') }).click();

      // Confirmation dialog should appear
      await expect(page.getByText('Delete Workflow')).toBeVisible();
      await expect(page.getByText(/Are you sure/)).toBeVisible();
    });
  });

  test.describe('User Info', () => {
    test('displays user email in header', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByText('test@example.com')).toBeVisible({ timeout: 10000 });
    });
  });
});
