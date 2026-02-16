/**
 * Tests for ABTestDashboard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ABTestDashboard } from './ABTestDashboard';
import { useAdminStore } from '../../stores/adminStore';
import { api } from '../../services/api';
import type { ABTest } from '../../types/admin';

// Mock dependencies
vi.mock('../../stores/adminStore');
vi.mock('../../services/api', () => ({
  api: {
    admin: {
      abTests: {
        create: vi.fn(),
        start: vi.fn(),
        stop: vi.fn(),
        exportCsv: vi.fn(),
        getStats: vi.fn(),
      },
    },
  },
}));

// Mock UI components
vi.mock('../ui/table', () => ({
  Table: ({ children }: { children: React.ReactNode }) => <table>{children}</table>,
  TableHeader: ({ children }: { children: React.ReactNode }) => <thead>{children}</thead>,
  TableBody: ({ children }: { children: React.ReactNode }) => <tbody>{children}</tbody>,
  TableRow: ({ children }: { children: React.ReactNode }) => <tr>{children}</tr>,
  TableHead: ({ children }: { children: React.ReactNode }) => <th>{children}</th>,
  TableCell: ({ children }: { children: React.ReactNode }) => <td>{children}</td>,
}));
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));
vi.mock('../ui/dialog', () => ({
  Dialog: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children }: any) => <div>{children}</div>,
}));
vi.mock('../ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}));
vi.mock('../ui/badge', () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));
vi.mock('../ui/card', () => ({
  Card: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

const mockAbTests: ABTest[] = [
  {
    id: 'test-1',
    name: 'Test A/B',
    workflowAId: 'wf-a',
    workflowBId: 'wf-b',
    status: 'draft',
    trafficSplit: 50,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'test-2',
    name: 'Running Test',
    workflowAId: 'wf-c',
    workflowBId: 'wf-d',
    status: 'running',
    trafficSplit: 70,
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
  {
    id: 'test-3',
    name: 'Completed Test',
    workflowAId: 'wf-e',
    workflowBId: 'wf-f',
    status: 'completed',
    trafficSplit: 30,
    createdAt: '2024-01-03T00:00:00Z',
    updatedAt: '2024-01-03T00:00:00Z',
  },
];

describe('ABTestDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAdminStore).mockReturnValue({
      abTests: mockAbTests,
      abTestsLoading: false,
      abTestsError: null,
      fetchABTests: vi.fn(),
      users: [],
      usersLoading: false,
      usersError: null,
      fetchUsers: vi.fn(),
      updateUserRole: vi.fn(),
      auditLogs: [],
      auditLogsLoading: false,
      auditLogsError: null,
      fetchAuditLogs: vi.fn(),
    });
  });

  describe('Loading States', () => {
    it('renders loading state when abTestsLoading is true and no tests', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: [],
        abTestsLoading: true,
        abTestsError: null,
        fetchABTests: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);
      expect(screen.getByText('Loading A/B tests...')).toBeInTheDocument();
    });

    it('does not show loading when tests exist', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: mockAbTests,
        abTestsLoading: true,
        abTestsError: null,
        fetchABTests: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);
      expect(screen.queryByText('Loading A/B tests...')).not.toBeInTheDocument();
      expect(screen.getByText('Test A/B')).toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('renders error message when abTestsError exists', () => {
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: [],
        abTestsLoading: false,
        abTestsError: 'Failed to fetch A/B tests',
        fetchABTests: vi.fn(),
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);
      expect(screen.getByText(/Failed to fetch A\/B tests/)).toBeInTheDocument();
    });
  });

  describe('A/B Test List', () => {
    it('renders all A/B tests', () => {
      render(<ABTestDashboard />);

      expect(screen.getByText('Test A/B')).toBeInTheDocument();
      expect(screen.getByText('Running Test')).toBeInTheDocument();
      expect(screen.getByText('Completed Test')).toBeInTheDocument();
    });

    it('displays status badges for each test', () => {
      render(<ABTestDashboard />);

      expect(screen.getByText('draft')).toBeInTheDocument();
      expect(screen.getByText('running')).toBeInTheDocument();
      expect(screen.getByText('completed')).toBeInTheDocument();
    });

    it('displays traffic split percentages', () => {
      render(<ABTestDashboard />);

      expect(screen.getByText('50% / 50%')).toBeInTheDocument();
      expect(screen.getByText('70% / 30%')).toBeInTheDocument();
      expect(screen.getByText('30% / 70%')).toBeInTheDocument();
    });

    it('shows Start button for draft tests', () => {
      render(<ABTestDashboard />);

      const startButtons = screen.getAllByText('Start');
      expect(startButtons).toHaveLength(1);
    });

    it('shows Stop button for running tests', () => {
      render(<ABTestDashboard />);

      const stopButtons = screen.getAllByText('Stop');
      expect(stopButtons).toHaveLength(1);
    });
  });

  describe('Create A/B Test', () => {
    it('opens create dialog when clicking Create New Test', async () => {
      const user = userEvent.setup();
      render(<ABTestDashboard />);

      const createButton = screen.getByText('Create New Test');
      await user.click(createButton);

      expect(screen.getByText('Create A/B Test')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Test Name')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Workflow A ID')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Workflow B ID')).toBeInTheDocument();
    });

    it('creates A/B test with form values', async () => {
      const user = userEvent.setup();
      const mockCreate = vi.fn().mockResolvedValue(undefined);
      const mockFetch = vi.fn();
      vi.mocked(api.admin.abTests.create).mockImplementation(mockCreate);
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: mockAbTests,
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);

      await user.click(screen.getByText('Create New Test'));

      const nameInput = screen.getByPlaceholderText('Test Name');
      const workflowAInput = screen.getByPlaceholderText('Workflow A ID');
      const workflowBInput = screen.getByPlaceholderText('Workflow B ID');

      await user.type(nameInput, 'New Test');
      await user.type(workflowAInput, 'workflow-a');
      await user.type(workflowBInput, 'workflow-b');

      const createButtons = screen.getAllByText('Create');
      await user.click(createButtons[createButtons.length - 1]);

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledWith({
          name: 'New Test',
          workflowAId: 'workflow-a',
          workflowBId: 'workflow-b',
          trafficSplit: 50,
        });
      });
    });

    it('closes dialog and resets form after creation', async () => {
      const user = userEvent.setup();
      vi.mocked(api.admin.abTests.create).mockResolvedValue(undefined);

      render(<ABTestDashboard />);

      await user.click(screen.getByText('Create New Test'));
      await user.type(screen.getByPlaceholderText('Test Name'), 'Test');
      const createButtons = screen.getAllByText('Create');
      await user.click(createButtons[createButtons.length - 1]);

      await waitFor(() => {
        expect(screen.queryByText('Create A/B Test')).not.toBeInTheDocument();
      });
    });
  });

  describe('Test Actions', () => {
    it('calls start API when clicking Start button', async () => {
      const user = userEvent.setup();
      const mockStart = vi.fn().mockResolvedValue(undefined);
      const mockFetch = vi.fn();
      vi.mocked(api.admin.abTests.start).mockImplementation(mockStart);
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: mockAbTests,
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);

      const startButton = screen.getByText('Start');
      await user.click(startButton);

      await waitFor(() => {
        expect(mockStart).toHaveBeenCalledWith('test-1');
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it('calls stop API when clicking Stop button', async () => {
      const user = userEvent.setup();
      const mockStop = vi.fn().mockResolvedValue(undefined);
      const mockFetch = vi.fn();
      vi.mocked(api.admin.abTests.stop).mockImplementation(mockStop);
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: mockAbTests,
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      render(<ABTestDashboard />);

      const stopButton = screen.getByText('Stop');
      await user.click(stopButton);

      await waitFor(() => {
        expect(mockStop).toHaveBeenCalledWith('test-2');
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it('exports CSV when clicking Export button', async () => {
      const user = userEvent.setup();
      const mockExport = vi.fn().mockResolvedValue('csv,data');
      vi.mocked(api.admin.abTests.exportCsv).mockImplementation(mockExport);

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

      render(<ABTestDashboard />);

      const exportButtons = screen.getAllByText('Export');
      await user.click(exportButtons[0]);

      await waitFor(() => {
        expect(mockExport).toHaveBeenCalledWith('test-1');
        expect(mockClick).toHaveBeenCalled();
      });
    });
  });

  describe('Statistics Dialog', () => {
    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it('opens stats dialog when clicking Stats button', async () => {
      const user = userEvent.setup();
      const mockGetStats = vi.fn().mockResolvedValue({
        A: { count: 100, successRate: 0.95, avgDurationMs: 150 },
        B: { count: 100, successRate: 0.97, avgDurationMs: 140 },
      });
      vi.mocked(api.admin.abTests.getStats).mockImplementation(mockGetStats);

      render(<ABTestDashboard />);

      const statsButtons = screen.getAllByText('Stats');
      await user.click(statsButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Test A\/B - Statistics/)).toBeInTheDocument();
        expect(screen.getByText('Variant A')).toBeInTheDocument();
        expect(screen.getByText('Variant B')).toBeInTheDocument();
      });
    });

    it('displays loading state while fetching stats', async () => {
      const user = userEvent.setup();
      vi.mocked(api.admin.abTests.getStats).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<ABTestDashboard />);

      const statsButtons = screen.getAllByText('Stats');
      await user.click(statsButtons[0]);

      expect(screen.getByText('Loading stats...')).toBeInTheDocument();
    });

    it('displays stats with formatted values', async () => {
      const user = userEvent.setup();
      const mockGetStats = vi.fn().mockResolvedValue({
        A: { count: 100, successRate: 0.955, avgDurationMs: 150.75 },
        B: { count: 80, successRate: 0.9725, avgDurationMs: 140.5 },
      });
      vi.mocked(api.admin.abTests.getStats).mockImplementation(mockGetStats);

      render(<ABTestDashboard />);

      const statsButtons = screen.getAllByText('Stats');
      await user.click(statsButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Count: 100/)).toBeInTheDocument();
        expect(screen.getByText(/Count: 80/)).toBeInTheDocument();
        expect(screen.getByText(/95\.50%/)).toBeInTheDocument();
        expect(screen.getByText(/97\.25%/)).toBeInTheDocument();
      }, { timeout: 3000 });

      // Check for duration values which may be formatted as 151ms or 140ms
      expect(screen.getByText(/Avg Duration: 151ms/)).toBeInTheDocument();
      expect(screen.getByText(/Avg Duration: 141ms/)).toBeInTheDocument();
    });
  });

  describe('Data Fetching', () => {
    it('fetches A/B tests on mount', () => {
      const mockFetch = vi.fn();
      vi.mocked(useAdminStore).mockReturnValue({
        abTests: mockAbTests,
        abTestsLoading: false,
        abTestsError: null,
        fetchABTests: mockFetch,
        users: [],
        usersLoading: false,
        usersError: null,
        fetchUsers: vi.fn(),
        updateUserRole: vi.fn(),
        auditLogs: [],
        auditLogsLoading: false,
        auditLogsError: null,
        fetchAuditLogs: vi.fn(),
      });

      // Restore original createElement after tests
      vi.restoreAllMocks();

      render(<ABTestDashboard />);

      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
