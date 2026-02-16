import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAdminStore } from './adminStore';
import type { User, AuditLog, ABTest, Role } from '../types/admin';

vi.mock('../services/api', () => ({
  api: {
    admin: {
      users: { list: vi.fn(), updateRole: vi.fn() },
      audit: { list: vi.fn() },
      abTests: { list: vi.fn() },
    },
  },
}));

describe('adminStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAdminStore.setState({
      users: [],
      usersLoading: false,
      usersError: null,
      auditLogs: [],
      auditLogsLoading: false,
      auditLogsError: null,
      abTests: [],
      abTestsLoading: false,
      abTestsError: null,
    });
  });

  describe('Initial state', () => {
    it('should have empty arrays and not loading', () => {
      const state = useAdminStore.getState();
      expect(state.users).toEqual([]);
      expect(state.usersLoading).toBe(false);
      expect(state.usersError).toBeNull();
      expect(state.auditLogs).toEqual([]);
      expect(state.auditLogsLoading).toBe(false);
      expect(state.auditLogsError).toBeNull();
      expect(state.abTests).toEqual([]);
      expect(state.abTestsLoading).toBe(false);
      expect(state.abTestsError).toBeNull();
    });
  });

  describe('fetchUsers', () => {
    it('should set loading, then store users on success', async () => {
      const mockUsers: User[] = [
        {
          id: 'u1',
          email: 'user1@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2024-01-01',
          lastLogin: '2024-01-02',
        },
        {
          id: 'u2',
          email: 'user2@example.com',
          role: 'admin',
          status: 'active',
          createdAt: '2024-01-01',
          lastLogin: '2024-01-02',
        },
      ];

      const { api } = await import('../services/api');
      vi.mocked(api.admin.users.list).mockResolvedValue(mockUsers);

      const promise = useAdminStore.getState().fetchUsers();
      expect(useAdminStore.getState().usersLoading).toBe(true);

      await promise;

      expect(useAdminStore.getState().usersLoading).toBe(false);
      expect(useAdminStore.getState().users).toEqual(mockUsers);
      expect(useAdminStore.getState().usersError).toBeNull();
    });

    it('should handle error and store error message', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.users.list).mockRejectedValue(
        new Error('Network error')
      );

      await useAdminStore.getState().fetchUsers();

      expect(useAdminStore.getState().usersLoading).toBe(false);
      expect(useAdminStore.getState().usersError).toBe('Network error');
      expect(useAdminStore.getState().users).toEqual([]);
    });

    it('should clear previous error on retry', async () => {
      const mockUsers: User[] = [];
      const { api } = await import('../services/api');

      // First call fails
      vi.mocked(api.admin.users.list).mockRejectedValueOnce(
        new Error('Network error')
      );
      await useAdminStore.getState().fetchUsers();
      expect(useAdminStore.getState().usersError).toBe('Network error');

      // Second call succeeds
      vi.mocked(api.admin.users.list).mockResolvedValue(mockUsers);
      await useAdminStore.getState().fetchUsers();
      expect(useAdminStore.getState().usersError).toBeNull();
    });
  });

  describe('updateUserRole', () => {
    it('should update user in array on success', async () => {
      const existingUsers: User[] = [
        {
          id: 'u1',
          email: 'user1@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2024-01-01',
          lastLogin: '2024-01-02',
        },
        {
          id: 'u2',
          email: 'user2@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2024-01-01',
          lastLogin: '2024-01-02',
        },
      ];

      useAdminStore.setState({ users: existingUsers });

      const updatedUser: User = {
        ...existingUsers[0],
        role: 'admin' as Role,
      };

      const { api } = await import('../services/api');
      vi.mocked(api.admin.users.updateRole).mockResolvedValue(updatedUser);

      await useAdminStore.getState().updateUserRole('u1', 'admin');

      const users = useAdminStore.getState().users;
      expect(users[0].role).toBe('admin');
      expect(users[1].role).toBe('user');
    });

    it('should throw on error', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.users.updateRole).mockRejectedValue(
        new Error('Permission denied')
      );

      await expect(
        useAdminStore.getState().updateUserRole('u1', 'admin')
      ).rejects.toThrow('Permission denied');
    });
  });

  describe('fetchAuditLogs', () => {
    it('should store logs on success', async () => {
      const mockLogs: AuditLog[] = [
        {
          id: 'log1',
          userId: 'u1',
          action: 'user.login',
          timestamp: '2024-01-01',
          metadata: {},
        },
        {
          id: 'log2',
          userId: 'u2',
          action: 'workflow.create',
          timestamp: '2024-01-02',
          metadata: {},
        },
      ];

      const { api } = await import('../services/api');
      vi.mocked(api.admin.audit.list).mockResolvedValue(mockLogs);

      await useAdminStore.getState().fetchAuditLogs();

      expect(useAdminStore.getState().auditLogsLoading).toBe(false);
      expect(useAdminStore.getState().auditLogs).toEqual(mockLogs);
      expect(useAdminStore.getState().auditLogsError).toBeNull();
    });

    it('should handle error', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.audit.list).mockRejectedValue(
        new Error('Database error')
      );

      await useAdminStore.getState().fetchAuditLogs();

      expect(useAdminStore.getState().auditLogsLoading).toBe(false);
      expect(useAdminStore.getState().auditLogsError).toBe('Database error');
    });

    it('should pass filters to API', async () => {
      const filters = {
        userId: 'u1',
        action: 'user.login',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      };

      const { api } = await import('../services/api');
      vi.mocked(api.admin.audit.list).mockResolvedValue([]);

      await useAdminStore.getState().fetchAuditLogs(filters);

      expect(api.admin.audit.list).toHaveBeenCalledWith(filters);
    });

    it('should set loading states correctly', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.audit.list).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 50))
      );

      const promise = useAdminStore.getState().fetchAuditLogs();
      expect(useAdminStore.getState().auditLogsLoading).toBe(true);

      await promise;
      expect(useAdminStore.getState().auditLogsLoading).toBe(false);
    });
  });

  describe('fetchABTests', () => {
    it('should store tests on success', async () => {
      const mockTests: ABTest[] = [
        {
          id: 'test1',
          name: 'Test A',
          enabled: true,
          createdAt: '2024-01-01',
          variants: [],
        },
        {
          id: 'test2',
          name: 'Test B',
          enabled: false,
          createdAt: '2024-01-02',
          variants: [],
        },
      ];

      const { api } = await import('../services/api');
      vi.mocked(api.admin.abTests.list).mockResolvedValue(mockTests);

      await useAdminStore.getState().fetchABTests();

      expect(useAdminStore.getState().abTestsLoading).toBe(false);
      expect(useAdminStore.getState().abTests).toEqual(mockTests);
      expect(useAdminStore.getState().abTestsError).toBeNull();
    });

    it('should handle error', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.abTests.list).mockRejectedValue(
        new Error('Service unavailable')
      );

      await useAdminStore.getState().fetchABTests();

      expect(useAdminStore.getState().abTestsLoading).toBe(false);
      expect(useAdminStore.getState().abTestsError).toBe('Service unavailable');
    });

    it('should set loading states correctly', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.admin.abTests.list).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 50))
      );

      const promise = useAdminStore.getState().fetchABTests();
      expect(useAdminStore.getState().abTestsLoading).toBe(true);

      await promise;
      expect(useAdminStore.getState().abTestsLoading).toBe(false);
    });
  });
});
