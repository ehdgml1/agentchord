/**
 * Zustand store for admin functionality
 *
 * Manages users, audit logs, and A/B tests state with API integration
 */

import { create } from 'zustand';
import type { User, AuditLog, ABTest, Role, AuditFilters } from '../types/admin';

/**
 * Admin store state and actions interface
 */
interface AdminState {
  // Users
  users: User[];
  usersLoading: boolean;
  usersError: string | null;

  // Audit logs
  auditLogs: AuditLog[];
  auditLogsLoading: boolean;
  auditLogsError: string | null;

  // A/B tests
  abTests: ABTest[];
  abTestsLoading: boolean;
  abTestsError: string | null;

  // Actions
  fetchUsers: () => Promise<void>;
  updateUserRole: (userId: string, role: Role) => Promise<void>;
  fetchAuditLogs: (filters?: AuditFilters) => Promise<void>;
  fetchABTests: () => Promise<void>;
}

/**
 * Main admin store
 */
export const useAdminStore = create<AdminState>((set, get) => ({
  // Initial state
  users: [],
  usersLoading: false,
  usersError: null,

  auditLogs: [],
  auditLogsLoading: false,
  auditLogsError: null,

  abTests: [],
  abTestsLoading: false,
  abTestsError: null,

  // Fetch users from API
  fetchUsers: async () => {
    set({ usersLoading: true, usersError: null });
    try {
      const { api } = await import('../services/api');
      const users = await api.admin.users.list();
      set({ users, usersLoading: false });
    } catch (error) {
      set({
        usersError: error instanceof Error ? error.message : 'Failed to fetch users',
        usersLoading: false,
      });
    }
  },

  // Update user role
  updateUserRole: async (userId: string, role: Role) => {
    try {
      const { api } = await import('../services/api');
      const updatedUser = await api.admin.users.updateRole(userId, role);

      set({
        users: get().users.map((u) => (u.id === userId ? updatedUser : u)),
      });
    } catch (error) {
      throw new Error(
        error instanceof Error ? error.message : 'Failed to update user role'
      );
    }
  },

  // Fetch audit logs with optional filters
  fetchAuditLogs: async (filters?: AuditFilters) => {
    set({ auditLogsLoading: true, auditLogsError: null });
    try {
      const { api } = await import('../services/api');
      const auditLogs = await api.admin.audit.list(filters);
      set({ auditLogs, auditLogsLoading: false });
    } catch (error) {
      set({
        auditLogsError:
          error instanceof Error ? error.message : 'Failed to fetch audit logs',
        auditLogsLoading: false,
      });
    }
  },

  // Fetch A/B tests
  fetchABTests: async () => {
    set({ abTestsLoading: true, abTestsError: null });
    try {
      const { api } = await import('../services/api');
      const abTests = await api.admin.abTests.list();
      set({ abTests, abTestsLoading: false });
    } catch (error) {
      set({
        abTestsError:
          error instanceof Error ? error.message : 'Failed to fetch A/B tests',
        abTestsLoading: false,
      });
    }
  },
}));
