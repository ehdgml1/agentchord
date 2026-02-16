/**
 * Zustand store for workflow execution state
 *
 * Manages execution history, current execution state, and execution
 * operations including running, stopping, and resuming workflows.
 */

import { create } from 'zustand';
import type { Execution, ExecutionMode } from '../types';
import { api, ApiError } from '../services/api';

/**
 * Execution store state and actions interface
 */
interface ExecutionState {
  /** List of executions */
  executions: Execution[];
  /** Currently viewed execution detail */
  currentExecution: Execution | null;
  /** Loading state for async operations */
  isLoading: boolean;
  /** Error message from last failed operation */
  error: string | null;

  /** Fetch executions list, optionally filtered by workflow ID */
  fetchExecutions: (workflowId?: string) => Promise<void>;
  /** Fetch a specific execution by ID */
  fetchExecution: (id: string) => Promise<void>;
  /** Execute a workflow and return the execution */
  runWorkflow: (
    workflowId: string,
    input: string,
    mode: ExecutionMode
  ) => Promise<Execution>;
  /** Stop a running execution */
  stopExecution: (id: string) => Promise<void>;
  /** Resume a paused execution */
  resumeExecution: (id: string) => Promise<void>;
  /** Clear error message */
  clearError: () => void;
}

/**
 * Main execution store
 */
export const useExecutionStore = create<ExecutionState>((set, get) => ({
  executions: [],
  currentExecution: null,
  isLoading: false,
  error: null,

  fetchExecutions: async (workflowId?: string) => {
    set({ isLoading: true, error: null });

    try {
      const executions = await api.executions.list(workflowId);
      set({ executions, isLoading: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to fetch executions';
      set({ error: message, isLoading: false });
    }
  },

  fetchExecution: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      const execution = await api.executions.get(id);
      set({ currentExecution: execution, isLoading: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to fetch execution';
      set({ error: message, isLoading: false });
    }
  },

  runWorkflow: async (workflowId: string, input: string, mode: ExecutionMode) => {
    set({ isLoading: true, error: null });

    try {
      const execution = await api.workflows.run(workflowId, input, mode);

      set((state) => ({
        executions: [execution, ...state.executions],
        currentExecution: execution,
        isLoading: false,
      }));

      return execution;
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to run workflow';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  stopExecution: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      await api.executions.stop(id);

      await get().fetchExecution(id);

      set({ isLoading: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to stop execution';
      set({ error: message, isLoading: false });
    }
  },

  resumeExecution: async (id: string) => {
    set({ isLoading: true, error: null });

    try {
      const execution = await api.executions.resume(id);

      set((state) => ({
        executions: state.executions.map((e) =>
          e.id === execution.id ? execution : e
        ),
        currentExecution: execution,
        isLoading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to resume execution';
      set({ error: message, isLoading: false });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));

/**
 * Selector hook for executions list
 */
export const useExecutions = () =>
  useExecutionStore((state) => state.executions);

/**
 * Selector hook for current execution
 */
export const useCurrentExecution = () =>
  useExecutionStore((state) => state.currentExecution);

/**
 * Selector hook for loading state
 */
export const useExecutionLoading = () =>
  useExecutionStore((state) => state.isLoading);

/**
 * Selector hook for error state
 */
export const useExecutionError = () =>
  useExecutionStore((state) => state.error);
