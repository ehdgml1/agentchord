/**
 * Zustand store for workflow version history
 *
 * Manages version snapshots for workflows including listing,
 * creating, and restoring versions.
 */

import { create } from 'zustand';
import type { WorkflowVersion } from '../types';
import { api } from '../services';

/**
 * Version store state and actions interface
 */
interface VersionState {
  // State
  versions: WorkflowVersion[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchVersions: (workflowId: string) => Promise<void>;
  createVersion: (workflowId: string, message: string) => Promise<void>;
  restoreVersion: (workflowId: string, versionId: string) => Promise<void>;
  clearError: () => void;
}

/**
 * Version history store
 */
export const useVersionStore = create<VersionState>((set) => ({
  versions: [],
  loading: false,
  error: null,

  fetchVersions: async (workflowId) => {
    set({ loading: true, error: null });
    try {
      const versions = await api.versions.list(workflowId);
      set({ versions, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch versions',
        loading: false,
      });
    }
  },

  createVersion: async (workflowId, message) => {
    set({ loading: true, error: null });
    try {
      const newVersion = await api.versions.create(workflowId, message);
      set((state) => ({
        versions: [newVersion, ...state.versions],
        loading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create version',
        loading: false,
      });
      throw error;
    }
  },

  restoreVersion: async (workflowId, versionId) => {
    set({ loading: true, error: null });
    try {
      await api.versions.restore(workflowId, versionId);
      set({ loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to restore version',
        loading: false,
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
