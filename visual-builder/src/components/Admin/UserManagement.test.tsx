/**
 * Tests for UserManagement component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserManagement } from './UserManagement';
import { useAdminStore } from '../../stores/adminStore';
import type { User } from '../../types/admin';

// Mock dependencies
vi.mock('../../stores/adminStore');

// Mock UI components
vi.mock('../ui/table', () => ({
  Table: ({ children }: { children: React.ReactNode }) => <table>{children}</table>,
  TableHeader: ({ children }: { children: React.ReactNode }) => <thead>{children}</thead>,
  TableBody: ({ children }: { children: React.ReactNode }) => <tbody>{children}</tbody>,
  TableRow: ({ children }: { children: React.ReactNode }) => <tr>{children}</tr>,
  TableHead: ({ children }: { children: React.ReactNode }) => <th>{children}</th>,
  TableCell: ({ children }: { children: React.ReactNode }) => <td>{children}</td>,
}));
vi.mock('../ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}));
vi.mock('../ui/select', () => ({
  Select: ({ value, onValueChange, children, disabled }: any) => (
    <select
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      disabled={disabled}
    >
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: () => null,
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

const mockUsers: User[] = [
  {
    id: 'user-1',
    name: 'Alice Smith',
    email: 'alice@example.com',
    role: 'admin',
    createdAt: '2024-01-01T00:00:00Z',
    lastLoginAt: '2024-01-10T00:00:00Z',
  },
  {
    id: 'user-2',
    name: 'Bob Jones',
    email: 'bob@example.com',
    role: 'editor',
    createdAt: '2024-01-02T00:00:00Z',
    lastLoginAt: null,
  },
  {
    id: 'user-3',
    name: 'Charlie Brown',
    email: 'charlie@example.com',
    role: 'viewer',
    createdAt: '2024-01-03T00:00:00Z',
    lastLoginAt: '2024-01-09T00:00:00Z',
  },
  ...Array.from({ length: 12 }, (_, i) => ({
    id: `user-${i + 4}`,
    name: `User ${i + 4}`,
    email: `user${i + 4}@example.com`,
    role: 'viewer' as const,
    createdAt: '2024-01-04T00:00:00Z',
    lastLoginAt: '2024-01-08T00:00:00Z',
  })),
];

describe('UserManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAdminStore).mockReturnValue({
      users: mockUsers.slice(0, 3),
      usersLoading: false,
      usersError: null,
      fetchUsers: vi.fn(),
      updateUserRole: vi.fn().mockResolvedValue(undefined),
      abTests: [],
      abTestsLoading: false,
      abTestsError: null,
      fetchABTests: vi.fn(),
      auditLogs: [],
      auditLogsLoading: false,
      auditLogsError: null,
      fetchAuditLogs: vi.fn(),
    });
  });

  describe('Loading States', () => {
    it('renders loading state when usersLoading is true and no users', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        users: [],
        usersLoading: true,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);
      expect(screen.getByText('Loading users...')).toBeInTheDocument();
    });

    it('does not show loading when users exist', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers.slice(0, 3),
        usersLoading: true,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);
      expect(screen.queryByText('Loading users...')).not.toBeInTheDocument();
      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('renders error message when usersError exists', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        users: [],
        usersLoading: false,
        usersError: 'Failed to fetch users',
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);
      expect(screen.getByText(/Failed to fetch users/)).toBeInTheDocument();
    });
  });

  describe('User List', () => {
    it('renders all users', () => {
      render(<UserManagement />);

      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Jones')).toBeInTheDocument();
      expect(screen.getByText('Charlie Brown')).toBeInTheDocument();
    });

    it('displays user emails', () => {
      render(<UserManagement />);

      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
      expect(screen.getByText('bob@example.com')).toBeInTheDocument();
      expect(screen.getByText('charlie@example.com')).toBeInTheDocument();
    });

    it('displays user roles in dropdowns', () => {
      render(<UserManagement />);

      const selects = screen.getAllByRole('combobox');
      expect(selects).toHaveLength(3);
    });

    it('displays last login date or "Never"', () => {
      render(<UserManagement />);

      expect(screen.getByText('Never')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('filters users by name', async () => {
      const user = userEvent.setup();
      render(<UserManagement />);

      const searchInput = screen.getByPlaceholderText(/Search by name or email/i);
      await user.type(searchInput, 'alice');

      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
      expect(screen.queryByText('Bob Jones')).not.toBeInTheDocument();
      expect(screen.queryByText('Charlie Brown')).not.toBeInTheDocument();
    });

    it('filters users by email', async () => {
      const user = userEvent.setup();
      render(<UserManagement />);

      const searchInput = screen.getByPlaceholderText(/Search by name or email/i);
      await user.type(searchInput, 'bob@');

      expect(screen.getByText('Bob Jones')).toBeInTheDocument();
      expect(screen.queryByText('Alice Smith')).not.toBeInTheDocument();
    });

    it('is case insensitive', async () => {
      const user = userEvent.setup();
      render(<UserManagement />);

      const searchInput = screen.getByPlaceholderText(/Search by name or email/i);
      await user.type(searchInput, 'CHARLIE');

      expect(screen.getByText('Charlie Brown')).toBeInTheDocument();
    });

    it('resets to page 1 when searching', async () => {
      const user = userEvent.setup();
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      // Go to page 2
      const nextButton = screen.getByText('Next');
      await user.click(nextButton);

      // Then search
      const searchInput = screen.getByPlaceholderText(/Search by name or email/i);
      await user.type(searchInput, 'alice');

      // Should show results from page 1
      expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    });
  });

  describe('Role Management', () => {
    it('calls updateUserRole when changing role', async () => {
      const user = userEvent.setup();
      const mockUpdateRole = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers.slice(0, 3),
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: mockUpdateRole,
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const selects = screen.getAllByRole('combobox');
      await user.selectOptions(selects[0], 'editor');

      await waitFor(() => {
        expect(mockUpdateRole).toHaveBeenCalledWith('user-1', 'editor');
      });
    });

    it('disables select while updating role', async () => {
      const user = userEvent.setup();
      let resolveUpdate: () => void;
      const updatePromise = new Promise<void>((resolve) => {
        resolveUpdate = resolve;
      });
      const mockUpdateRole = vi.fn(() => updatePromise);

      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers.slice(0, 3),
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: mockUpdateRole,
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const selects = screen.getAllByRole('combobox');
      await user.selectOptions(selects[0], 'editor');

      await waitFor(() => {
        expect(selects[0]).toBeDisabled();
      });

      resolveUpdate!();
      await waitFor(() => {
        expect(selects[0]).not.toBeDisabled();
      });
    });
  });

  describe('Pagination', () => {
    it('shows pagination when more than 10 users', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
      expect(screen.getByText(/Showing 1 to 10 of 15 users/)).toBeInTheDocument();
    });

    it('does not show pagination for 10 or fewer users', () => {
      render(<UserManagement />);

      expect(screen.queryByText('Previous')).not.toBeInTheDocument();
      expect(screen.queryByText('Next')).not.toBeInTheDocument();
    });

    it('navigates to next page', async () => {
      const user = userEvent.setup();
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const nextButton = screen.getByText('Next');
      await user.click(nextButton);

      expect(screen.getByText(/Showing 11 to 15 of 15 users/)).toBeInTheDocument();
    });

    it('navigates to previous page', async () => {
      const user = userEvent.setup();
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const nextButton = screen.getByText('Next');
      await user.click(nextButton);

      const prevButton = screen.getByText('Previous');
      await user.click(prevButton);

      expect(screen.getByText(/Showing 1 to 10 of 15 users/)).toBeInTheDocument();
    });

    it('disables Previous button on first page', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const prevButton = screen.getByText('Previous');
      expect(prevButton).toBeDisabled();
    });

    it('disables Next button on last page', async () => {
      const user = userEvent.setup();
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers,
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      const nextButton = screen.getByText('Next');
      await user.click(nextButton);

      expect(nextButton).toBeDisabled();
    });
  });

  describe('Data Fetching', () => {
    it('fetches users on mount', () => {
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        users: mockUsers.slice(0, 3),
        usersLoading: false,
        usersError: null,
        fetchUsers: mockFetch,
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<UserManagement />);

      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
