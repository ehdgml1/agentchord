import { Page } from '@playwright/test';

// --- Mock Data ---

// Create a fake JWT token that won't expire (exp far in future)
function createMockJWT(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify({ ...payload, exp: Math.floor(Date.now() / 1000) + 86400 }));
  const sig = btoa('mock-signature');
  return `${header}.${body}.${sig}`;
}

export const MOCK_TOKEN = createMockJWT({
  sub: 'user-1',
  email: 'test@example.com',
  role: 'user',
});

export const MOCK_ADMIN_TOKEN = createMockJWT({
  sub: 'admin-1',
  email: 'admin@example.com',
  role: 'admin',
});

export const MOCK_USER = {
  user_id: 'user-1',
  email: 'test@example.com',
  role: 'user',
  token: MOCK_TOKEN,
};

export const MOCK_ADMIN = {
  user_id: 'admin-1',
  email: 'admin@example.com',
  role: 'admin',
  token: MOCK_ADMIN_TOKEN,
};

export const MOCK_WORKFLOWS = [
  {
    id: 'wf-1',
    name: 'Email Processor',
    description: 'Processes incoming emails',
    nodes: [
      { id: 'n1', type: 'agent', position: { x: 100, y: 100 }, data: { label: 'Agent 1', blockType: 'agent' } },
      { id: 'n2', type: 'agent', position: { x: 300, y: 100 }, data: { label: 'Agent 2', blockType: 'agent' } },
    ],
    edges: [{ id: 'e1', source: 'n1', target: 'n2' }],
    owner_id: 'user-1',
    created_at: '2024-06-01T10:00:00Z',
    updated_at: '2024-06-15T14:30:00Z',
    // camelCase aliases (backend uses alias)
    createdAt: '2024-06-01T10:00:00Z',
    updatedAt: '2024-06-15T14:30:00Z',
  },
  {
    id: 'wf-2',
    name: 'Data Pipeline',
    description: 'ETL data pipeline',
    nodes: [
      { id: 'n1', type: 'agent', position: { x: 100, y: 100 }, data: { label: 'Agent 1', blockType: 'agent' } },
    ],
    edges: [],
    owner_id: 'user-1',
    created_at: '2024-05-20T08:00:00Z',
    updated_at: '2024-06-10T12:00:00Z',
    createdAt: '2024-05-20T08:00:00Z',
    updatedAt: '2024-06-10T12:00:00Z',
  },
  {
    id: 'wf-3',
    name: 'Customer Support Bot',
    description: 'Automated customer support',
    nodes: [
      { id: 'n1', type: 'agent', position: { x: 100, y: 100 }, data: { label: 'Support Agent', blockType: 'agent' } },
      { id: 'n2', type: 'condition', position: { x: 300, y: 100 }, data: { label: 'Check Priority', blockType: 'condition' } },
      { id: 'n3', type: 'agent', position: { x: 500, y: 50 }, data: { label: 'Escalate', blockType: 'agent' } },
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2' },
      { id: 'e2', source: 'n2', target: 'n3' },
    ],
    owner_id: 'user-1',
    created_at: '2024-06-05T09:00:00Z',
    updated_at: '2024-06-20T16:00:00Z',
    createdAt: '2024-06-05T09:00:00Z',
    updatedAt: '2024-06-20T16:00:00Z',
  },
];

// --- Helper Functions ---

/**
 * Setup API mocks for authentication endpoints
 */
export async function mockAuthAPI(page: Page) {
  // Login endpoint
  await page.route('**/api/auth/login', async (route) => {
    const body = JSON.parse(route.request().postData() || '{}');
    if (body.email === 'test@example.com' && body.password === 'password123') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_USER) });
    } else if (body.email === 'admin@example.com' && body.password === 'admin123') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN) });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { message: 'Invalid credentials' } }),
      });
    }
  });

  // Register endpoint
  await page.route('**/api/auth/register', async (route) => {
    const body = JSON.parse(route.request().postData() || '{}');
    if (body.email === 'existing@example.com') {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ error: { message: 'Email already registered' } }),
      });
    } else {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          user_id: 'new-user-1',
          email: body.email,
          role: 'user',
          token: MOCK_TOKEN,
        }),
      });
    }
  });

  // Token refresh
  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ token: MOCK_TOKEN }),
    });
  });
}

/**
 * Setup API mocks for workflow endpoints
 */
export async function mockWorkflowAPI(page: Page) {
  // List workflows
  await page.route('**/api/workflows', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workflows: MOCK_WORKFLOWS }),
      });
    } else if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'wf-new-1',
          name: body.name || 'Untitled Workflow',
          description: body.description || '',
          nodes: body.nodes || [],
          edges: body.edges || [],
          owner_id: 'user-1',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }),
      });
    }
  });

  // Single workflow CRUD
  await page.route('**/api/workflows/*', async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    // Extract workflow ID from URL
    const match = url.match(/\/api\/workflows\/([^/?]+)/);
    const workflowId = match ? match[1] : null;

    if (method === 'GET' && workflowId) {
      const wf = MOCK_WORKFLOWS.find(w => w.id === workflowId);
      if (wf) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(wf) });
      } else {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { message: 'Not found' } }) });
      }
    } else if (method === 'PUT' && workflowId) {
      const body = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: workflowId, ...body, updatedAt: new Date().toISOString() }),
      });
    } else if (method === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });
}

/**
 * Login as a user by setting localStorage auth state directly
 * (faster than going through the login flow)
 */
export async function loginAs(page: Page, user: 'user' | 'admin' = 'user') {
  const mockUser = user === 'admin' ? MOCK_ADMIN : MOCK_USER;
  const token = user === 'admin' ? MOCK_ADMIN_TOKEN : MOCK_TOKEN;

  await page.addInitScript((authData) => {
    localStorage.setItem('auth-storage', JSON.stringify({
      state: {
        token: authData.token,
        user: { id: authData.user_id, email: authData.email, role: authData.role },
        isAuthenticated: true,
      },
      version: 0,
    }));
  }, { ...mockUser, token });
}

/**
 * Setup all common API mocks (auth + workflows)
 */
export async function setupMocks(page: Page) {
  await mockAuthAPI(page);
  await mockWorkflowAPI(page);
}
