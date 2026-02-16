/**
 * Tests for AuditLogViewer component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuditLogViewer } from './AuditLogViewer';
import { useAdminStore } from '../../stores/adminStore';
import type { AuditLog } from '../../types/admin';

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
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));
vi.mock('../ui/dialog', () => ({
  Dialog: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
}));

const mockAuditLogs: AuditLog[] = [
  {
    id: 'log-1',
    userId: 'user-1',
    userName: 'Alice',
    action: 'CREATE',
    resourceType: 'workflow',
    resourceId: 'wf-1',
    ipAddress: '192.168.1.1',
    details: { name: 'New Workflow' },
    createdAt: '2024-01-01T10:00:00Z',
  },
  {
    id: 'log-2',
    userId: 'user-2',
    userName: 'Bob',
    action: 'UPDATE',
    resourceType: 'user',
    resourceId: 'user-3',
    ipAddress: null,
    details: { role: 'admin' },
    createdAt: '2024-01-02T11:00:00Z',
  },
  {
    id: 'log-3',
    userId: 'user-1',
    userName: 'Alice',
    action: 'DELETE',
    resourceType: 'workflow',
    resourceId: 'wf-2',
    ipAddress: '192.168.1.1',
    details: {},
    createdAt: '2024-01-03T12:00:00Z',
  },
];

describe('AuditLogViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAdminStore).mockReturnValue({
      auditLogs: mockAuditLogs,
      auditLogsLoading: false,
      auditLogsError: null,
      fetchAuditLogs: vi.fn(),
      users: [],
      usersLoading: false,
      usersError: null,
      fetchUsers: vi.fn(),
      updateUserRole: vi.fn(),
      abTests: [],
      abTestsLoading: false,
      abTestsError: null,
      fetchABTests: vi.fn(),
    });
  });

  describe('Loading States', () => {
    it('renders loading state when auditLogsLoading is true and no logs', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: [],
        auditLogsLoading: true,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);
      expect(screen.getByText('Loading audit logs...')).toBeInTheDocument();
    });

    it('does not show loading when logs exist', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: true,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);
      expect(screen.queryByText('Loading audit logs...')).not.toBeInTheDocument();
      expect(screen.getAllByText('Alice')).toHaveLength(2);
    });
  });

  describe('Error States', () => {
    it('renders error message when auditLogsError exists', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: 'Failed to fetch audit logs',
        fetchAuditLogs: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);
      expect(screen.getByText(/Failed to fetch audit logs/)).toBeInTheDocument();
    });
  });

  describe('Audit Log List', () => {
    it('renders all audit logs', () => {
      render(<AuditLogViewer />);

      expect(screen.getAllByText('Alice')).toHaveLength(2);
      expect(screen.getByText('Bob')).toBeInTheDocument();
    });

    it('displays actions for each log', () => {
      render(<AuditLogViewer />);

      expect(screen.getByText('CREATE')).toBeInTheDocument();
      expect(screen.getByText('UPDATE')).toBeInTheDocument();
      expect(screen.getByText('DELETE')).toBeInTheDocument();
    });

    it('displays resource information', () => {
      render(<AuditLogViewer />);

      expect(screen.getByText('workflow/wf-1')).toBeInTheDocument();
      expect(screen.getByText('user/user-3')).toBeInTheDocument();
      expect(screen.getByText('workflow/wf-2')).toBeInTheDocument();
    });

    it('displays IP addresses or "N/A"', () => {
      render(<AuditLogViewer />);

      expect(screen.getAllByText('192.168.1.1')).toHaveLength(2);
      expect(screen.getAllByText('N/A')).toHaveLength(1);
    });

    it('shows empty state when no logs', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      expect(screen.getByText('No audit logs found')).toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('renders all filter inputs', () => {
      render(<AuditLogViewer />);

      expect(screen.getByPlaceholderText('Start Date')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('End Date')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Filter by action')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Filter by user ID')).toBeInTheDocument();
    });

    it('calls fetchAuditLogs with filters on mount', () => {
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      expect(mockFetch).toHaveBeenCalledWith({});
    });

    it('updates filters when changing start date', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      const startDateInput = screen.getByPlaceholderText('Start Date');
      await user.type(startDateInput, '2024-01-01');

      // fetchAuditLogs should be called again with the new filter
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.objectContaining({ startDate: '2024-01-01' })
        );
      });
    });

    it('updates filters when changing action', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      const actionInput = screen.getByPlaceholderText('Filter by action');
      await user.type(actionInput, 'CREATE');

      // Wait for debounce (300ms) to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.objectContaining({ action: 'CREATE' })
        );
      }, { timeout: 2000 });
    });

    it('clears filter value when input is emptied', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      const actionInput = screen.getByPlaceholderText('Filter by action');
      await user.type(actionInput, 'CREATE');

      // Wait for first debounce
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.objectContaining({ action: 'CREATE' })
        );
      }, { timeout: 2000 });

      await user.clear(actionInput);

      // Wait for clear debounce
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith({});
      }, { timeout: 2000 });
    });
  });

  describe('Export CSV', () => {
    it('renders Export CSV button', () => {
      render(<AuditLogViewer />);

      expect(screen.getByText('Export CSV')).toBeInTheDocument();
    });

    it('disables Export CSV when no logs', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      expect(screen.getByText('Export CSV')).toBeDisabled();
    });

    it('exports logs as CSV when clicked', async () => {
      const user = userEvent.setup();

      // Mock URL and DOM APIs
      global.URL.createObjectURL = vi.fn(() => 'blob:url');
      global.URL.revokeObjectURL = vi.fn();
      const mockClick = vi.fn();
      const mockAnchor = { click: mockClick, href: '', download: '' };
      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
        if (tag === 'a') {
          return mockAnchor as any;
        }
        return originalCreateElement(tag);
      });

      render(<AuditLogViewer />);

      const exportButton = screen.getByText('Export CSV');
      await user.click(exportButton);

      expect(mockClick).toHaveBeenCalled();
      expect(global.URL.createObjectURL).toHaveBeenCalled();

      vi.restoreAllMocks();
    });
  });

  describe('Detail Dialog', () => {
    it('opens detail dialog when clicking View button', async () => {
      const user = userEvent.setup();
      render(<AuditLogViewer />);

      const viewButtons = screen.getAllByText('View');
      await user.click(viewButtons[0]);

      expect(screen.getByText('Audit Log Details')).toBeInTheDocument();
      expect(screen.getByText('log-1')).toBeInTheDocument();
    });

    it('displays all log details in dialog', async () => {
      const user = userEvent.setup();
      render(<AuditLogViewer />);

      const viewButtons = screen.getAllByText('View');
      await user.click(viewButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('log-1')).toBeInTheDocument();
      });

      // Check that the dialog contains the expected information
      const dialogContent = screen.getByText('Audit Log Details').closest('div');
      expect(dialogContent?.textContent).toContain('Alice');
      expect(dialogContent?.textContent).toContain('user-1');
      expect(dialogContent?.textContent).toContain('CREATE');
      expect(dialogContent?.textContent).toContain('workflow/wf-1');
    });

    it('displays formatted JSON details', async () => {
      const user = userEvent.setup();
      render(<AuditLogViewer />);

      const viewButtons = screen.getAllByText('View');
      await user.click(viewButtons[0]);

      const detailsElement = screen.getByText(/"name":/);
      expect(detailsElement).toBeInTheDocument();
    });

    it('shows "N/A" for null IP address in detail dialog', async () => {
      const user = userEvent.setup();
      render(<AuditLogViewer />);

      const viewButtons = screen.getAllByText('View');
      await user.click(viewButtons[1]); // Bob's log has null IP

      // Get all N/A texts and verify at least one exists
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });
  });

  describe('Data Fetching', () => {
    it('fetches audit logs on mount', () => {
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        auditLogs: mockAuditLogs,
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        abTests: [],
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: vi.fn(),
      });

      render(<AuditLogViewer />);

      expect(mockFetch).toHaveBeenCalledWith({});
    });
  });
});
