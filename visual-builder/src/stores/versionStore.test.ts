import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useVersionStore } from './versionStore';
import type { WorkflowVersion } from '../types';

vi.mock('../services', () => ({
  api: {
    versions: {
      list: vi.fn(),
      create: vi.fn(),
      restore: vi.fn(),
    },
  },
}));

describe('versionStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useVersionStore.setState({
      versions: [],
      loading: false,
      error: null,
    });
  });

  describe('Initial state', () => {
    it('should have empty versions and not loading', () => {
      const state = useVersionStore.getState();
      expect(state.versions).toEqual([]);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('fetchVersions', () => {
    it('should fetch and store versions on success', async () => {
      const mockVersions: WorkflowVersion[] = [
        {
          id: 'v1',
          workflowId: 'wf1',
          version: 1,
          message: 'Initial version',
          createdAt: '2024-01-01',
          createdBy: 'user1',
          snapshot: {},
        },
        {
          id: 'v2',
          workflowId: 'wf1',
          version: 2,
          message: 'Updated workflow',
          createdAt: '2024-01-02',
          createdBy: 'user1',
          snapshot: {},
        },
      ];

      const { api } = await import('../services');
      vi.mocked(api.versions.list).mockResolvedValue(mockVersions);

      await useVersionStore.getState().fetchVersions('wf1');

      expect(useVersionStore.getState().versions).toEqual(mockVersions);
      expect(useVersionStore.getState().loading).toBe(false);
      expect(useVersionStore.getState().error).toBeNull();
    });

    it('should handle error', async () => {
      const { api } = await import('../services');
      vi.mocked(api.versions.list).mockRejectedValue(
        new Error('Network error')
      );

      await useVersionStore.getState().fetchVersions('wf1');

      expect(useVersionStore.getState().loading).toBe(false);
      expect(useVersionStore.getState().error).toBe('Network error');
    });

    it('should set loading states correctly', async () => {
      const { api } = await import('../services');
      vi.mocked(api.versions.list).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 50))
      );

      const promise = useVersionStore.getState().fetchVersions('wf1');
      expect(useVersionStore.getState().loading).toBe(true);

      await promise;
      expect(useVersionStore.getState().loading).toBe(false);
    });
  });

  describe('createVersion', () => {
    it('should prepend version to array on success', async () => {
      const existingVersions: WorkflowVersion[] = [
        {
          id: 'v1',
          workflowId: 'wf1',
          version: 1,
          message: 'Initial version',
          createdAt: '2024-01-01',
          createdBy: 'user1',
          snapshot: {},
        },
      ];

      useVersionStore.setState({ versions: existingVersions });

      const newVersion: WorkflowVersion = {
        id: 'v2',
        workflowId: 'wf1',
        version: 2,
        message: 'New version',
        createdAt: '2024-01-02',
        createdBy: 'user1',
        snapshot: {},
      };

      const { api } = await import('../services');
      vi.mocked(api.versions.create).mockResolvedValue(newVersion);

      await useVersionStore.getState().createVersion('wf1', 'New version');

      const versions = useVersionStore.getState().versions;
      expect(versions).toHaveLength(2);
      expect(versions[0]).toEqual(newVersion);
      expect(versions[1]).toEqual(existingVersions[0]);
    });

    it('should throw on error', async () => {
      const { api } = await import('../services');
      vi.mocked(api.versions.create).mockRejectedValue(
        new Error('Validation error')
      );

      await expect(
        useVersionStore.getState().createVersion('wf1', 'New version')
      ).rejects.toThrow();

      expect(useVersionStore.getState().error).toBe('Validation error');
    });

    it('should clear error on retry', async () => {
      const { api } = await import('../services');

      // First call fails
      vi.mocked(api.versions.create).mockRejectedValueOnce(
        new Error('Network error')
      );
      await expect(
        useVersionStore.getState().createVersion('wf1', 'Version 1')
      ).rejects.toThrow();
      expect(useVersionStore.getState().error).toBe('Network error');

      // Second call succeeds
      const newVersion: WorkflowVersion = {
        id: 'v1',
        workflowId: 'wf1',
        version: 1,
        message: 'Version 1',
        createdAt: '2024-01-01',
        createdBy: 'user1',
        snapshot: {},
      };
      vi.mocked(api.versions.create).mockResolvedValue(newVersion);
      await useVersionStore.getState().createVersion('wf1', 'Version 1');
      expect(useVersionStore.getState().error).toBeNull();
    });
  });

  describe('restoreVersion', () => {
    it('should call API and clear loading on success', async () => {
      const { api } = await import('../services');
      vi.mocked(api.versions.restore).mockResolvedValue(undefined);

      await useVersionStore.getState().restoreVersion('wf1', 'v1');

      expect(api.versions.restore).toHaveBeenCalledWith('wf1', 'v1');
      expect(useVersionStore.getState().loading).toBe(false);
      expect(useVersionStore.getState().error).toBeNull();
    });

    it('should throw on error', async () => {
      const { api } = await import('../services');
      vi.mocked(api.versions.restore).mockRejectedValue(
        new Error('Not found')
      );

      await expect(
        useVersionStore.getState().restoreVersion('wf1', 'v1')
      ).rejects.toThrow();

      expect(useVersionStore.getState().error).toBe('Not found');
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useVersionStore.setState({ error: 'Some error' });

      useVersionStore.getState().clearError();

      expect(useVersionStore.getState().error).toBeNull();
    });
  });

  describe('Loading states', () => {
    it('should toggle loading correctly for fetchVersions', async () => {
      const { api } = await import('../services');
      let resolvePromise: (value: WorkflowVersion[]) => void;
      const promise = new Promise<WorkflowVersion[]>(
        (resolve) => (resolvePromise = resolve)
      );

      vi.mocked(api.versions.list).mockReturnValue(promise);

      const fetchPromise = useVersionStore.getState().fetchVersions('wf1');
      expect(useVersionStore.getState().loading).toBe(true);

      resolvePromise!([]);
      await fetchPromise;
      expect(useVersionStore.getState().loading).toBe(false);
    });

    it('should toggle loading correctly for createVersion', async () => {
      const { api } = await import('../services');
      let resolvePromise: (value: WorkflowVersion) => void;
      const promise = new Promise<WorkflowVersion>(
        (resolve) => (resolvePromise = resolve)
      );

      vi.mocked(api.versions.create).mockReturnValue(promise);

      const createPromise = useVersionStore
        .getState()
        .createVersion('wf1', 'New version');
      expect(useVersionStore.getState().loading).toBe(true);

      resolvePromise!({
        id: 'v1',
        workflowId: 'wf1',
        version: 1,
        message: 'New version',
        createdAt: '2024-01-01',
        createdBy: 'user1',
        snapshot: {},
      });
      await createPromise;
      expect(useVersionStore.getState().loading).toBe(false);
    });
  });
});
