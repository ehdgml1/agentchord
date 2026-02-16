import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useExecutionStore } from './executionStore';

// Mock the api module
vi.mock('../services/api', () => ({
  api: {
    executions: {
      list: vi.fn(),
      get: vi.fn(),
      stop: vi.fn(),
      resume: vi.fn(),
    },
    workflows: {
      run: vi.fn(),
    },
  },
  ApiError: class extends Error {
    statusCode: number;
    constructor(message: string, statusCode: number) {
      super(message);
      this.name = 'ApiError';
      this.statusCode = statusCode;
    }
  },
}));

import { api } from '../services/api';
import type { Execution } from '../types';

const mockExecutions: Execution[] = [
  {
    id: 'e1',
    workflowId: 'w1',
    status: 'completed',
    mode: 'full',
    triggerType: 'manual',
    triggerId: null,
    input: 'test input 1',
    output: 'test output 1',
    error: null,
    nodeExecutions: [],
    startedAt: '2024-01-01T00:00:00Z',
    completedAt: '2024-01-01T00:01:00Z',
    durationMs: 60000,
  },
  {
    id: 'e2',
    workflowId: 'w1',
    status: 'running',
    mode: 'mock',
    triggerType: 'manual',
    triggerId: null,
    input: 'test input 2',
    output: null,
    error: null,
    nodeExecutions: [],
    startedAt: '2024-01-01T00:02:00Z',
    completedAt: null,
    durationMs: null,
  },
];

describe('executionStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useExecutionStore.setState({
      executions: [],
      currentExecution: null,
      isLoading: false,
      error: null,
    });
  });

  describe('fetchExecutions', () => {
    it('loads executions from API', async () => {
      vi.mocked(api.executions.list).mockResolvedValueOnce(mockExecutions);

      await useExecutionStore.getState().fetchExecutions();

      const state = useExecutionStore.getState();
      expect(state.executions).toEqual(mockExecutions);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('passes workflowId filter to API', async () => {
      vi.mocked(api.executions.list).mockResolvedValueOnce([]);

      await useExecutionStore.getState().fetchExecutions('w1');

      expect(api.executions.list).toHaveBeenCalledWith('w1');
    });

    it('handles API errors gracefully', async () => {
      vi.mocked(api.executions.list).mockRejectedValueOnce(new Error('Network error'));

      await useExecutionStore.getState().fetchExecutions();

      const state = useExecutionStore.getState();
      expect(state.error).toBe('Failed to fetch executions');
      expect(state.isLoading).toBe(false);
    });

    it('sets loading state during fetch', async () => {
      let resolvePromise: (value: Execution[]) => void;
      const promise = new Promise<Execution[]>((resolve) => { resolvePromise = resolve; });
      vi.mocked(api.executions.list).mockReturnValueOnce(promise);

      const fetchPromise = useExecutionStore.getState().fetchExecutions();
      expect(useExecutionStore.getState().isLoading).toBe(true);

      resolvePromise!([]);
      await fetchPromise;
      expect(useExecutionStore.getState().isLoading).toBe(false);
    });
  });

  describe('fetchExecution', () => {
    it('loads single execution', async () => {
      vi.mocked(api.executions.get).mockResolvedValueOnce(mockExecutions[0]);

      await useExecutionStore.getState().fetchExecution('e1');

      expect(useExecutionStore.getState().currentExecution).toEqual(mockExecutions[0]);
    });
  });

  describe('runWorkflow', () => {
    it('runs workflow and adds to executions list', async () => {
      const newExecution: Execution = {
        id: 'e3',
        workflowId: 'w1',
        status: 'running',
        mode: 'full',
        triggerType: 'manual',
        triggerId: null,
        input: 'test input',
        output: null,
        error: null,
        nodeExecutions: [],
        startedAt: '2024-01-01T00:03:00Z',
        completedAt: null,
        durationMs: null,
      };
      vi.mocked(api.workflows.run).mockResolvedValueOnce(newExecution);

      const result = await useExecutionStore.getState().runWorkflow('w1', 'test input', 'full');

      expect(result).toEqual(newExecution);
      expect(useExecutionStore.getState().executions[0]).toEqual(newExecution);
      expect(useExecutionStore.getState().currentExecution).toEqual(newExecution);
      expect(api.workflows.run).toHaveBeenCalledWith('w1', 'test input', 'full');
    });

    it('throws on run failure', async () => {
      vi.mocked(api.workflows.run).mockRejectedValueOnce(new Error('Server error'));

      await expect(
        useExecutionStore.getState().runWorkflow('w1', 'input', 'full')
      ).rejects.toThrow();

      expect(useExecutionStore.getState().error).toBe('Failed to run workflow');
    });
  });

  describe('stopExecution', () => {
    it('stops execution and refreshes state', async () => {
      const stoppedExecution: Execution = { ...mockExecutions[1], status: 'cancelled' };
      vi.mocked(api.executions.stop).mockResolvedValueOnce(undefined);
      vi.mocked(api.executions.get).mockResolvedValueOnce(stoppedExecution);

      await useExecutionStore.getState().stopExecution('e2');

      expect(api.executions.stop).toHaveBeenCalledWith('e2');
      expect(useExecutionStore.getState().currentExecution?.status).toBe('cancelled');
    });
  });

  describe('resumeExecution', () => {
    it('resumes execution and updates state', async () => {
      useExecutionStore.setState({ executions: [mockExecutions[1]] });
      const resumedExecution: Execution = { ...mockExecutions[1], status: 'running' };
      vi.mocked(api.executions.resume).mockResolvedValueOnce(resumedExecution);

      await useExecutionStore.getState().resumeExecution('e2');

      expect(api.executions.resume).toHaveBeenCalledWith('e2');
      expect(useExecutionStore.getState().currentExecution).toEqual(resumedExecution);
      expect(useExecutionStore.getState().executions[0]).toEqual(resumedExecution);
    });

    it('handles resume errors gracefully', async () => {
      vi.mocked(api.executions.resume).mockRejectedValueOnce(new Error('Cannot resume'));

      await useExecutionStore.getState().resumeExecution('e2');

      expect(useExecutionStore.getState().error).toBe('Failed to resume execution');
    });
  });

  describe('clearError', () => {
    it('clears error state', () => {
      useExecutionStore.setState({ error: 'some error' });
      useExecutionStore.getState().clearError();
      expect(useExecutionStore.getState().error).toBeNull();
    });
  });
});
