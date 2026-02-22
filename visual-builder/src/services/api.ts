/**
 * API client for Visual Builder backend
 *
 * This module provides type-safe HTTP client functions for all backend
 * API endpoints including workflows, executions, MCP servers, and secrets.
 */

import type {
  Workflow,
  Execution,
  ExecutionMode,
  MCPServer,
  MCPServerCreate,
  MCPTool,
  WorkflowVersion,
} from '../types';
import type {
  Schedule,
  CreateScheduleData,
  UpdateScheduleData,
} from '../types/schedule';
import type {
  User,
  Role,
  AuditLog,
  AuditFilters,
  ABTest,
  ABTestCreate,
  ABTestStats,
} from '../types/admin';
import type { DocumentFileInfo } from '../types/blocks';

export interface LLMProviderStatus {
  name: string;
  configured: boolean;
  models: string[];
}

export interface LLMModelInfo {
  id: string;
  provider: string;
  displayName: string;
  contextWindow: number;
  costPer1kInput: number;
  costPer1kOutput: number;
}

export interface LLMKeyStatus {
  provider: string;
  hasUserKey: boolean;
  hasServerKey: boolean;
  configured: boolean;
}

const API_BASE = '/api';

/**
 * Auth token storage for API requests.
 * Set via setAuthToken() when user logs in.
 */
let authToken: string | null = null;

/**
 * Set the authentication token for API requests
 */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/**
 * Get the current authentication token
 */
export function getAuthToken(): string | null {
  return authToken;
}

/**
 * API error wrapper with status code
 */
class ApiError extends Error {
  statusCode: number;
  details?: unknown;

  constructor(
    message: string,
    statusCode: number,
    details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit & { params?: Record<string, unknown> }
): Promise<T> {
  let url = `${API_BASE}${endpoint}`;

  // Add query parameters if provided
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value));
      }
    });
    const queryString = params.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(authToken && { Authorization: `Bearer ${authToken}` }),
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));

      // Auto-logout on 401 (token expired/invalid)
      if (response.status === 401 && authToken) {
        // Import dynamically to avoid circular deps
        const { useAuthStore } = await import('../stores/authStore');
        useAuthStore.getState().logout();
      }

      throw new ApiError(
        errorData.error?.message || errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(
      error instanceof Error ? error.message : 'Network request failed',
      0
    );
  }
}

/**
 * Workflow API endpoints
 */
const workflows = {
  /**
   * List all workflows
   */
  async list(): Promise<Workflow[]> {
    const res = await fetchApi<{ workflows: Workflow[] }>('/workflows');
    return res.workflows;
  },

  /**
   * Get a specific workflow by ID
   */
  get(id: string): Promise<Workflow> {
    return fetchApi<Workflow>(`/workflows/${id}`);
  },

  /**
   * Create a new workflow
   */
  create(data: Omit<Workflow, 'id' | 'createdAt' | 'updatedAt'>): Promise<Workflow> {
    return fetchApi<Workflow>('/workflows', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing workflow
   */
  update(
    id: string,
    data: Partial<Omit<Workflow, 'id' | 'createdAt' | 'updatedAt'>>
  ): Promise<Workflow> {
    return fetchApi<Workflow>(`/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a workflow
   */
  delete(id: string): Promise<void> {
    return fetchApi<void>(`/workflows/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Execute a workflow
   */
  run(id: string, input: string, mode: ExecutionMode): Promise<Execution> {
    return fetchApi<Execution>(`/workflows/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ input, mode }),
    });
  },

  /**
   * Validate a workflow structure
   */
  validate(id: string): Promise<{ errors: string[] }> {
    return fetchApi<{ errors: string[] }>(`/workflows/${id}/validate`);
  },
};

/**
 * Execution API endpoints
 */
const executions = {
  /**
   * List executions, optionally filtered by workflow ID
   */
  async list(workflowId?: string): Promise<Execution[]> {
    const query = workflowId ? `?workflow_id=${workflowId}` : '';
    const res = await fetchApi<{ executions: Execution[] }>(`/executions${query}`);
    return res.executions;
  },

  /**
   * Get a specific execution by ID
   */
  get(id: string): Promise<Execution> {
    return fetchApi<Execution>(`/executions/${id}`);
  },

  /**
   * Stop a running execution
   */
  stop(id: string): Promise<void> {
    return fetchApi<void>(`/executions/${id}/stop`, {
      method: 'POST',
    });
  },

  /**
   * Resume a paused execution
   */
  resume(id: string): Promise<Execution> {
    return fetchApi<Execution>(`/executions/${id}/resume`, {
      method: 'POST',
    });
  },
};

/**
 * MCP server API endpoints
 */
const mcp = {
  /**
   * List all configured MCP servers
   */
  listServers(): Promise<MCPServer[]> {
    return fetchApi<MCPServer[]>('/mcp/servers');
  },

  /**
   * Connect a new MCP server
   */
  connectServer(data: MCPServerCreate): Promise<MCPServer> {
    return fetchApi<MCPServer>('/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Disconnect an MCP server
   */
  disconnectServer(id: string): Promise<void> {
    return fetchApi<void>(`/mcp/servers/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Get tools from a specific MCP server
   */
  getTools(serverId: string): Promise<MCPTool[]> {
    return fetchApi<MCPTool[]>(`/mcp/servers/${serverId}/tools`);
  },

  /**
   * Health check for an MCP server
   */
  healthCheck(serverId: string): Promise<{ healthy: boolean }> {
    return fetchApi<{ healthy: boolean }>(`/mcp/servers/${serverId}/health`);
  },
};

/**
 * Secrets API endpoints
 */
const secrets = {
  /**
   * List all secret names (values are not returned)
   */
  async list(): Promise<string[]> {
    const res = await fetchApi<{ name: string }[]>('/secrets');
    return res.map(s => s.name);
  },

  /**
   * Create a new secret
   */
  create(name: string, value: string): Promise<void> {
    return fetchApi<void>('/secrets', {
      method: 'POST',
      body: JSON.stringify({ name, value }),
    });
  },

  /**
   * Update an existing secret
   */
  update(name: string, value: string): Promise<void> {
    return fetchApi<void>(`/secrets/${name}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    });
  },

  /**
   * Delete a secret
   */
  delete(name: string): Promise<void> {
    return fetchApi<void>(`/secrets/${name}`, {
      method: 'DELETE',
    });
  },
};

/**
 * Schedule API endpoints
 */
const schedules = {
  /**
   * List schedules for a workflow
   */
  async list(workflowId: string): Promise<Schedule[]> {
    const res = await fetchApi<{ schedules: Schedule[] }>(`/schedules?workflow_id=${workflowId}`);
    return res.schedules;
  },

  /**
   * Create a new schedule
   */
  create(data: CreateScheduleData): Promise<Schedule> {
    return fetchApi<Schedule>('/schedules', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: data.workflowId,
        expression: data.expression,
        input: data.input,
        timezone: data.timezone,
      }),
    });
  },

  /**
   * Update an existing schedule
   */
  update(id: string, data: UpdateScheduleData): Promise<Schedule> {
    return fetchApi<Schedule>(`/schedules/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a schedule
   */
  delete(id: string): Promise<void> {
    return fetchApi<void>(`/schedules/${id}`, {
      method: 'DELETE',
    });
  },

  /**
   * Toggle schedule enabled/disabled
   */
  toggle(id: string): Promise<Schedule> {
    return fetchApi<Schedule>(`/schedules/${id}/toggle`, {
      method: 'POST',
    });
  },
};

/**
 * Version history API endpoints
 */
const versions = {
  /**
   * List all versions for a workflow
   */
  async list(workflowId: string): Promise<WorkflowVersion[]> {
    const res = await fetchApi<{ versions: WorkflowVersion[] }>(`/workflows/${workflowId}/versions`);
    return res.versions;
  },

  /**
   * Create a new version snapshot
   */
  create(workflowId: string, message: string): Promise<WorkflowVersion> {
    return fetchApi<WorkflowVersion>(`/workflows/${workflowId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  /**
   * Restore workflow to a specific version
   */
  restore(workflowId: string, versionId: string): Promise<void> {
    return fetchApi<void>(`/workflows/${workflowId}/versions/${versionId}/restore`, {
      method: 'POST',
    });
  },
};

/**
 * Admin API endpoints
 */
const admin = {
  users: {
    /**
     * List all users
     */
    async list(): Promise<User[]> {
      const res = await fetchApi<{ users: User[] }>('/users');
      return res.users;
    },

    /**
     * Update user role
     */
    updateRole(id: string, role: Role): Promise<User> {
      return fetchApi<User>(`/users/${id}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role }),
      });
    },
  },

  audit: {
    /**
     * List audit logs with optional filters
     */
    async list(filters?: AuditFilters): Promise<AuditLog[]> {
      const res = await fetchApi<{ logs: AuditLog[] }>('/audit', { params: filters as Record<string, unknown> });
      return res.logs;
    },
  },

  abTests: {
    /**
     * List all A/B tests
     */
    async list(): Promise<ABTest[]> {
      const res = await fetchApi<{ tests: ABTest[] }>('/ab-tests');
      return res.tests;
    },

    /**
     * Create a new A/B test
     */
    create(data: ABTestCreate): Promise<ABTest> {
      return fetchApi<ABTest>('/ab-tests', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    /**
     * Get statistics for an A/B test
     */
    getStats(id: string): Promise<{ A: ABTestStats; B: ABTestStats }> {
      return fetchApi<{ A: ABTestStats; B: ABTestStats }>(`/ab-tests/${id}/stats`);
    },

    /**
     * Start an A/B test
     */
    start(id: string): Promise<ABTest> {
      return fetchApi<ABTest>(`/ab-tests/${id}/start`, {
        method: 'POST',
      });
    },

    /**
     * Stop an A/B test
     */
    stop(id: string): Promise<ABTest> {
      return fetchApi<ABTest>(`/ab-tests/${id}/stop`, {
        method: 'POST',
      });
    },

    /**
     * Export A/B test results to CSV
     */
    exportCsv(id: string): Promise<string> {
      return fetchApi<string>(`/ab-tests/${id}/export`);
    },
  },
};

/**
 * LLM API endpoints
 */
const llm = {
  /**
   * List all LLM providers and their configuration status
   */
  async listProviders(): Promise<{ providers: LLMProviderStatus[]; defaultModel: string }> {
    return fetchApi<{ providers: LLMProviderStatus[]; defaultModel: string }>('/llm/providers');
  },

  /**
   * List all available LLM models across all providers
   */
  async listModels(): Promise<LLMModelInfo[]> {
    const res = await fetchApi<{ models: LLMModelInfo[] }>('/llm/models');
    return res.models;
  },

  /**
   * Get API key status for all providers
   */
  async getKeyStatus(): Promise<LLMKeyStatus[]> {
    const res = await fetchApi<{ keys: LLMKeyStatus[] }>('/llm/keys');
    return res.keys;
  },

  /**
   * Save a user API key for a provider
   */
  async setKey(provider: string, apiKey: string): Promise<void> {
    await fetchApi(`/llm/keys/${provider}`, {
      method: 'PUT',
      body: JSON.stringify({ apiKey }),
    });
  },

  /**
   * Validate an API key for a provider
   */
  async validateKey(provider: string, apiKey: string): Promise<{ valid: boolean; error?: string }> {
    return fetchApi(`/llm/keys/${provider}/validate`, {
      method: 'POST',
      body: JSON.stringify({ apiKey }),
    });
  },

  /**
   * Delete a user API key for a provider
   */
  async deleteKey(provider: string): Promise<void> {
    await fetchApi(`/llm/keys/${provider}`, {
      method: 'DELETE',
    });
  },
};

/**
 * Complete API client
 */
/**
 * Playground API endpoints
 */
const playground = {
  /**
   * Send a chat message to execute a workflow with conversation history
   */
  async chat(
    workflowId: string,
    message: string,
    history: { role: string; content: string }[]
  ): Promise<{ executionId: string; status: string }> {
    return fetchApi('/playground/chat', {
      method: 'POST',
      body: JSON.stringify({
        workflowId,
        message,
        history,
      }),
    });
  },
};

/**
 * Document upload API endpoints
 */
const documents = {
  /**
   * Upload a document file for RAG processing
   */
  async upload(file: File): Promise<DocumentFileInfo> {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE}/documents/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...(authToken && { Authorization: `Bearer ${authToken}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || errorData.error?.message || `Upload failed: ${response.status}`,
        response.status,
        errorData
      );
    }

    return response.json();
  },

  /**
   * List all uploaded documents
   */
  async list(): Promise<DocumentFileInfo[]> {
    return fetchApi<DocumentFileInfo[]>('/documents');
  },

  /**
   * Delete an uploaded document
   */
  async delete(fileId: string): Promise<void> {
    return fetchApi<void>(`/documents/${fileId}`, {
      method: 'DELETE',
    });
  },
};

export const api = {
  workflows,
  executions,
  mcp,
  secrets,
  schedules,
  versions,
  admin,
  llm,
  playground,
  documents,
};

export { ApiError };
