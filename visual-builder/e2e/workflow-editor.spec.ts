import { test, expect } from '@playwright/test';
import { setupMocks, loginAs } from './fixtures';

test.describe('Workflow Editor', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await loginAs(page);
  });

  test.describe('New Workflow', () => {
    test('loads empty canvas for new workflow', async ({ page }) => {
      await page.goto('/workflows/new');
      // Canvas should be visible (react-flow renders a container)
      await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
    });

    test('does not make API call for new workflow', async ({ page }) => {
      let apiCalled = false;
      await page.route('**/api/workflows/new', async (route) => {
        apiCalled = true;
        await route.fulfill({ status: 404 });
      });

      await page.goto('/workflows/new');
      await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
      expect(apiCalled).toBe(false);
    });
  });

  test.describe('Existing Workflow', () => {
    test('loads workflow data from API', async ({ page }) => {
      await page.goto('/workflows/wf-1');
      // Canvas should render
      await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
    });

    test('redirects to dashboard on 404', async ({ page }) => {
      await page.route('**/api/workflows/nonexistent', async (route) => {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { message: 'Not found' } }) });
      });

      await page.goto('/workflows/nonexistent');
      // Should redirect back to dashboard
      await expect(page.getByRole('heading', { name: 'Workflows' })).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Editor Layout', () => {
    test('shows sidebar with node palette', async ({ page }) => {
      await page.goto('/workflows/new');
      await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
      // Sidebar should have draggable node types
      await expect(page.getByText('Agent', { exact: true })).toBeVisible();
    });
  });
});
