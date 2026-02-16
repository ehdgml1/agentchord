import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, setAuthToken, getAuthToken } from './api';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('api client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setAuthToken(null);
  });

  afterEach(() => {
    setAuthToken(null);
  });

  describe('authentication', () => {
    it('sets and gets auth token', () => {
      setAuthToken('test-token-123');
      expect(getAuthToken()).toBe('test-token-123');
    });

    it('clears auth token when set to null', () => {
      setAuthToken('test-token-123');
      setAuthToken(null);
      expect(getAuthToken()).toBeNull();
    });

    it('includes Authorization header when token is set', async () => {
      setAuthToken('my-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      await api.workflows.list();

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer my-token',
          }),
        })
      );
    });

    it('does not include Authorization header when token is null', async () => {
      setAuthToken(null);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      await api.workflows.list();

      const headers = mockFetch.mock.calls[0][1]?.headers as Record<string, string>;
      expect(headers.Authorization).toBeUndefined();
    });
  });

  describe('error handling', () => {
    it('throws ApiError with message from response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Invalid workflow data' }),
      });

      await expect(api.workflows.list()).rejects.toMatchObject({
        name: 'ApiError',
        message: 'Invalid workflow data',
        statusCode: 400,
      });
    });

    it('throws ApiError with default message when no message in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      });

      await expect(api.workflows.list()).rejects.toMatchObject({
        name: 'ApiError',
        message: 'HTTP 500: Internal Server Error',
        statusCode: 500,
      });
    });

    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network failed'));

      await expect(api.workflows.list()).rejects.toMatchObject({
        name: 'ApiError',
        message: 'Network failed',
        statusCode: 0,
      });
    });

    it('handles non-JSON error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => {
          throw new Error('Not JSON');
        },
      });

      await expect(api.workflows.get('123')).rejects.toMatchObject({
        name: 'ApiError',
        message: 'HTTP 404: Not Found',
        statusCode: 404,
      });
    });
  });

  describe('workflows endpoint', () => {
    it('lists workflows and unwraps response', async () => {
      const mockWorkflows = [
        { id: '1', name: 'Workflow 1' },
        { id: '2', name: 'Workflow 2' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      const result = await api.workflows.list();

      expect(result).toEqual(mockWorkflows);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows',
        expect.objectContaining({ headers: expect.any(Object) })
      );
    });

    it('creates workflow with POST request', async () => {
      const newWorkflow = {
        name: 'New Workflow',
        nodes: [],
        edges: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 'new-id', ...newWorkflow }),
      });

      await api.workflows.create(newWorkflow);

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newWorkflow),
        })
      );
    });

    it('runs workflow with input and mode', async () => {
      const mockExecution = { id: 'exec-1', status: 'running' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExecution,
      });

      const result = await api.workflows.run('workflow-1', '{"key":"value"}', 'full');

      expect(result).toEqual(mockExecution);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows/workflow-1/run',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ input: '{"key":"value"}', mode: 'full' }),
        })
      );
    });
  });

  describe('secrets endpoint', () => {
    it('lists secret names and unwraps response', async () => {
      const mockSecretResponses = [
        { name: 'API_KEY', description: '', createdAt: null, updatedAt: null },
        { name: 'DATABASE_URL', description: '', createdAt: null, updatedAt: null },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSecretResponses,
      });

      const result = await api.secrets.list();

      expect(result).toEqual(['API_KEY', 'DATABASE_URL']);
      expect(mockFetch).toHaveBeenCalledWith('/api/secrets', expect.any(Object));
    });

    it('creates secret', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.secrets.create('NEW_KEY', 'secret-value');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/secrets',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'NEW_KEY', value: 'secret-value' }),
        })
      );
    });

    it('updates secret', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.secrets.update('API_KEY', 'new-value');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/secrets/API_KEY',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ value: 'new-value' }),
        })
      );
    });

    it('deletes secret', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.secrets.delete('OLD_KEY');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/secrets/OLD_KEY',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('query parameters', () => {
    it('adds query parameters to URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await api.executions.list('workflow-123');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/executions?workflow_id=workflow-123',
        expect.any(Object)
      );
    });

    it('skips null and undefined parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await api.admin.audit.list({ userId: 'user-1', action: undefined });

      // URL should only include userId, not action
      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('userId=user-1');
      expect(url).not.toContain('action=');
    });
  });

  describe('204 No Content responses', () => {
    it('returns undefined for 204 responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const result = await api.secrets.delete('KEY');

      expect(result).toBeUndefined();
    });
  });

  describe('schedules endpoint', () => {
    it('lists schedules and unwraps response', async () => {
      const mockSchedules = [
        { id: 's1', workflowId: 'w1', expression: '0 9 * * *' },
        { id: 's2', workflowId: 'w1', expression: '0 17 * * *' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ schedules: mockSchedules }),
      });

      const result = await api.schedules.list('w1');

      expect(result).toEqual(mockSchedules);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/schedules?workflow_id=w1',
        expect.any(Object)
      );
    });

    it('creates schedule', async () => {
      const mockSchedule = {
        id: 's1',
        workflowId: 'w1',
        expression: '0 9 * * *',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSchedule,
      });

      const result = await api.schedules.create({
        workflowId: 'w1',
        expression: '0 9 * * *',
      });

      expect(result).toEqual(mockSchedule);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/schedules',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ workflow_id: 'w1', expression: '0 9 * * *' }),
        })
      );
    });

    it('deletes schedule', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.schedules.delete('s1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/schedules/s1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('versions endpoint', () => {
    it('lists versions and unwraps response', async () => {
      const mockVersions = [
        {
          id: 'v1',
          workflowId: 'w1',
          versionNumber: 1,
          message: 'init',
          createdAt: '2024-01-01',
        },
        {
          id: 'v2',
          workflowId: 'w1',
          versionNumber: 2,
          message: 'update',
          createdAt: '2024-01-02',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ versions: mockVersions }),
      });

      const result = await api.versions.list('w1');

      expect(result).toEqual(mockVersions);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows/w1/versions',
        expect.any(Object)
      );
    });

    it('creates version', async () => {
      const mockVersion = {
        id: 'v1',
        workflowId: 'w1',
        versionNumber: 1,
        message: 'init',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockVersion,
      });

      const result = await api.versions.create('w1', 'init');

      expect(result).toEqual(mockVersion);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows/w1/versions',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ message: 'init' }),
        })
      );
    });

    it('restores version', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.versions.restore('w1', 'v1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/workflows/w1/versions/v1/restore',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('admin endpoints', () => {
    it('lists users and unwraps response', async () => {
      const mockUsers = [
        { id: 'u1', email: 'test@test.com', role: 'admin' },
        { id: 'u2', email: 'user@test.com', role: 'user' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ users: mockUsers }),
      });

      const result = await api.admin.users.list();

      expect(result).toEqual(mockUsers);
      expect(mockFetch).toHaveBeenCalledWith('/api/users', expect.any(Object));
    });

    it('updates user role', async () => {
      const mockUser = { id: 'u1', email: 'test@test.com', role: 'admin' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUser,
      });

      const result = await api.admin.users.updateRole('u1', 'admin');

      expect(result).toEqual(mockUser);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users/u1/role',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ role: 'admin' }),
        })
      );
    });

    it('lists audit logs and unwraps response', async () => {
      const mockLogs = [
        { id: 'l1', action: 'create', resourceType: 'workflow' },
        { id: 'l2', action: 'update', resourceType: 'user' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ logs: mockLogs }),
      });

      const result = await api.admin.audit.list();

      expect(result).toEqual(mockLogs);
      expect(mockFetch).toHaveBeenCalledWith('/api/audit', expect.any(Object));
    });

    it('lists audit logs with filters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ logs: [] }),
      });

      await api.admin.audit.list({ userId: 'u1', action: 'create' });

      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('userId=u1');
      expect(url).toContain('action=create');
    });

    it('lists AB tests and unwraps response', async () => {
      const mockTests = [
        { id: 't1', name: 'Test A/B', status: 'draft' },
        { id: 't2', name: 'Test C/D', status: 'active' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ tests: mockTests }),
      });

      const result = await api.admin.abTests.list();

      expect(result).toEqual(mockTests);
      expect(mockFetch).toHaveBeenCalledWith('/api/ab-tests', expect.any(Object));
    });

    it('creates AB test', async () => {
      const newTest = { name: 'New Test', status: 'draft' };
      const mockTest = { id: 't1', ...newTest };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTest,
      });

      const result = await api.admin.abTests.create(newTest);

      expect(result).toEqual(mockTest);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/ab-tests',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newTest),
        })
      );
    });

    it('gets AB test stats', async () => {
      const mockStats = {
        A: { executions: 10, successRate: 0.9 },
        B: { executions: 12, successRate: 0.85 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      });

      const result = await api.admin.abTests.getStats('t1');

      expect(result).toEqual(mockStats);
      expect(mockFetch).toHaveBeenCalledWith('/api/ab-tests/t1/stats', expect.any(Object));
    });

    it('starts AB test', async () => {
      const mockTest = { id: 't1', name: 'Test', status: 'active' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTest,
      });

      const result = await api.admin.abTests.start('t1');

      expect(result).toEqual(mockTest);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/ab-tests/t1/start',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('stops AB test', async () => {
      const mockTest = { id: 't1', name: 'Test', status: 'completed' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTest,
      });

      const result = await api.admin.abTests.stop('t1');

      expect(result).toEqual(mockTest);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/ab-tests/t1/stop',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('mcp endpoint', () => {
    it('lists MCP servers', async () => {
      const mockServers = [
        { id: 'm1', name: 'Server 1', status: 'connected' },
        { id: 'm2', name: 'Server 2', status: 'disconnected' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockServers,
      });

      const result = await api.mcp.listServers();

      expect(result).toEqual(mockServers);
      expect(mockFetch).toHaveBeenCalledWith('/api/mcp/servers', expect.any(Object));
    });

    it('connects MCP server', async () => {
      const newServer = { name: 'New Server', url: 'http://localhost:3000' };
      const mockServer = { id: 'm1', ...newServer, status: 'connected' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockServer,
      });

      const result = await api.mcp.connectServer(newServer);

      expect(result).toEqual(mockServer);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/servers',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newServer),
        })
      );
    });

    it('disconnects MCP server', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.mcp.disconnectServer('m1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/servers/m1',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('gets tools from MCP server', async () => {
      const mockTools = [
        { name: 'tool1', description: 'Tool 1' },
        { name: 'tool2', description: 'Tool 2' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      });

      const result = await api.mcp.getTools('m1');

      expect(result).toEqual(mockTools);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/servers/m1/tools',
        expect.any(Object)
      );
    });

    it('checks MCP server health', async () => {
      const mockHealth = { healthy: true };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockHealth,
      });

      const result = await api.mcp.healthCheck('m1');

      expect(result).toEqual(mockHealth);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/mcp/servers/m1/health',
        expect.any(Object)
      );
    });
  });

  describe('executions endpoint', () => {
    it('lists executions and unwraps response', async () => {
      const mockExecutions = [
        { id: 'e1', status: 'completed' },
        { id: 'e2', status: 'running' },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ executions: mockExecutions }),
      });

      const result = await api.executions.list();

      expect(result).toEqual(mockExecutions);
      expect(mockFetch).toHaveBeenCalledWith('/api/executions', expect.any(Object));
    });

    it('lists executions filtered by workflow', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ executions: [] }),
      });

      await api.executions.list('wf-123');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/executions?workflow_id=wf-123',
        expect.any(Object)
      );
    });

    it('gets execution by id', async () => {
      const mockExecution = { id: 'e1', status: 'completed' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExecution,
      });

      const result = await api.executions.get('e1');

      expect(result).toEqual(mockExecution);
      expect(mockFetch).toHaveBeenCalledWith('/api/executions/e1', expect.any(Object));
    });

    it('stops execution', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await api.executions.stop('e1');

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/executions/e1/stop',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('resumes execution', async () => {
      const mockExecution = { id: 'e1', status: 'running' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExecution,
      });

      const result = await api.executions.resume('e1');

      expect(result).toEqual(mockExecution);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/executions/e1/resume',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });
});
