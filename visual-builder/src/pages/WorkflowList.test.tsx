import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkflowList } from './WorkflowList';
import { useWorkflowStore } from '../stores/workflowStore';
import { useAuthStore } from '../stores/authStore';
import { api } from '../services/api';
import { toast } from 'sonner';
import type { Workflow } from '../types/workflow';

const mockNavigate = vi.fn();
const mockClearWorkflow = vi.fn();
const mockLogout = vi.fn();
const mockConfirm = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector) => {
    const state = { clearWorkflow: mockClearWorkflow };
    return selector ? selector(state) : state;
  }),
}));

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn((selector) => {
    const state = { user: { email: 'test@example.com' }, logout: mockLogout };
    return selector ? selector(state) : state;
  }),
}));

vi.mock('../services/api', () => ({
  api: {
    workflows: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('../components/ui/confirm-dialog', () => ({
  useConfirm: () => mockConfirm,
}));

vi.mock('../components/ui/skeleton', () => ({
  WorkflowListSkeleton: () => <div data-testid="workflow-list-skeleton">Loading...</div>,
}));

const mockWorkflows: Workflow[] = [
  {
    id: 'wf-1',
    name: 'Test Workflow 1',
    description: 'First test workflow',
    nodes: [{ id: 'n1', type: 'trigger', data: {}, position: { x: 0, y: 0 } }],
    edges: [],
    updatedAt: '2024-01-15T10:00:00Z',
    createdAt: '2024-01-10T10:00:00Z',
  },
  {
    id: 'wf-2',
    name: 'Test Workflow 2',
    description: 'Second test workflow',
    nodes: [
      { id: 'n1', type: 'trigger', data: {}, position: { x: 0, y: 0 } },
      { id: 'n2', type: 'agent', data: {}, position: { x: 100, y: 0 } },
    ],
    edges: [],
    updatedAt: '2024-01-20T10:00:00Z',
    createdAt: '2024-01-12T10:00:00Z',
  },
  {
    id: 'wf-3',
    name: 'Alpha Workflow',
    description: 'Testing search',
    nodes: [],
    edges: [],
    updatedAt: '2024-01-10T10:00:00Z',
    createdAt: '2024-01-05T10:00:00Z',
  },
];

describe('WorkflowList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading state', () => {
    it('shows loading skeleton while fetching workflows', () => {
      vi.mocked(api.workflows.list).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<WorkflowList />);
      expect(screen.getByTestId('workflow-list-skeleton')).toBeInTheDocument();
    });
  });

  describe('Data display', () => {
    beforeEach(() => {
      vi.mocked(api.workflows.list).mockResolvedValue(mockWorkflows);
    });

    it('renders workflow list when data is available', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      expect(screen.getByText('Test Workflow 2')).toBeInTheDocument();
      expect(screen.getByText('Alpha Workflow')).toBeInTheDocument();
    });

    it('displays workflow descriptions', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('First test workflow')).toBeInTheDocument();
      });

      expect(screen.getByText('Second test workflow')).toBeInTheDocument();
    });

    it('displays workflow node counts', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText(/1 nodes/)).toBeInTheDocument();
      });

      expect(screen.getByText(/2 nodes/)).toBeInTheDocument();
    });

    it('displays formatted update dates', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText(/Jan 15/)).toBeInTheDocument();
      });

      expect(screen.getByText(/Jan 20/)).toBeInTheDocument();
    });

    it('displays user email in header', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('test@example.com')).toBeInTheDocument();
      });
    });
  });

  describe('Empty states', () => {
    it('shows empty state when no workflows exist', async () => {
      vi.mocked(api.workflows.list).mockResolvedValue([]);

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('No workflows yet')).toBeInTheDocument();
      });

      expect(
        screen.getByRole('button', { name: /create your first workflow/i })
      ).toBeInTheDocument();
    });

    it('shows no results message when search has no matches', async () => {
      vi.mocked(api.workflows.list).mockResolvedValue(mockWorkflows);
      const user = userEvent.setup();

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search workflows...');
      await user.type(searchInput, 'nonexistent');

      expect(screen.getByText(/No workflows matching "nonexistent"/)).toBeInTheDocument();
    });
  });

  describe('Search functionality', () => {
    beforeEach(() => {
      vi.mocked(api.workflows.list).mockResolvedValue(mockWorkflows);
    });

    it('filters workflows by name', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search workflows...');
      await user.type(searchInput, 'Alpha');

      expect(screen.getByText('Alpha Workflow')).toBeInTheDocument();
      expect(screen.queryByText('Test Workflow 1')).not.toBeInTheDocument();
      expect(screen.queryByText('Test Workflow 2')).not.toBeInTheDocument();
    });

    it('filters workflows by description', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search workflows...');
      await user.type(searchInput, 'Second');

      expect(screen.getByText('Test Workflow 2')).toBeInTheDocument();
      expect(screen.queryByText('Test Workflow 1')).not.toBeInTheDocument();
    });

    it('is case insensitive', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search workflows...');
      await user.type(searchInput, 'ALPHA');

      expect(screen.getByText('Alpha Workflow')).toBeInTheDocument();
    });
  });

  describe('Sort functionality', () => {
    beforeEach(() => {
      vi.mocked(api.workflows.list).mockResolvedValue(mockWorkflows);
    });

    it('sorts by name ascending', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const sortSelect = screen.getByRole('combobox');
      await user.selectOptions(sortSelect, 'name-asc');

      const workflows = screen.getAllByRole('heading', { level: 3 });
      expect(workflows[0]).toHaveTextContent('Alpha Workflow');
      expect(workflows[1]).toHaveTextContent('Test Workflow 1');
      expect(workflows[2]).toHaveTextContent('Test Workflow 2');
    });

    it('sorts by name descending', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const sortSelect = screen.getByRole('combobox');
      await user.selectOptions(sortSelect, 'name-desc');

      const workflows = screen.getAllByRole('heading', { level: 3 });
      expect(workflows[0]).toHaveTextContent('Test Workflow 2');
      expect(workflows[1]).toHaveTextContent('Test Workflow 1');
      expect(workflows[2]).toHaveTextContent('Alpha Workflow');
    });

    it('sorts by date newest first (default)', async () => {
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const workflows = screen.getAllByRole('heading', { level: 3 });
      expect(workflows[0]).toHaveTextContent('Test Workflow 2'); // Jan 20
      expect(workflows[1]).toHaveTextContent('Test Workflow 1'); // Jan 15
      expect(workflows[2]).toHaveTextContent('Alpha Workflow'); // Jan 10
    });

    it('sorts by date oldest first', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const sortSelect = screen.getByRole('combobox');
      await user.selectOptions(sortSelect, 'date-old');

      const workflows = screen.getAllByRole('heading', { level: 3 });
      expect(workflows[0]).toHaveTextContent('Alpha Workflow'); // Jan 10
      expect(workflows[1]).toHaveTextContent('Test Workflow 1'); // Jan 15
      expect(workflows[2]).toHaveTextContent('Test Workflow 2'); // Jan 20
    });

    it('sorts by node count', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const sortSelect = screen.getByRole('combobox');
      await user.selectOptions(sortSelect, 'nodes');

      const workflows = screen.getAllByRole('heading', { level: 3 });
      expect(workflows[0]).toHaveTextContent('Test Workflow 2'); // 2 nodes
    });
  });

  describe('Actions', () => {
    beforeEach(() => {
      vi.mocked(api.workflows.list).mockResolvedValue(mockWorkflows);
    });

    it('navigates to workflow editor on click', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const workflowCard = screen.getByText('Test Workflow 1').closest('div');
      if (workflowCard) {
        await user.click(workflowCard);
      }

      expect(mockNavigate).toHaveBeenCalledWith('/workflows/wf-1');
    });

    it('navigates to new workflow on create button click', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /new workflow/i })).toBeInTheDocument();
      });

      const newButton = screen.getByRole('button', { name: /new workflow/i });
      await user.click(newButton);

      expect(mockClearWorkflow).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/workflows/new');
    });

    it('creates workflow from empty state button', async () => {
      vi.mocked(api.workflows.list).mockResolvedValue([]);
      const user = userEvent.setup();

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('No workflows yet')).toBeInTheDocument();
      });

      const createButton = screen.getByRole('button', {
        name: /create your first workflow/i,
      });
      await user.click(createButton);

      expect(mockClearWorkflow).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/workflows/new');
    });

    it('clones workflow successfully', async () => {
      const user = userEvent.setup();
      vi.mocked(api.workflows.get).mockResolvedValue(mockWorkflows[0]);
      vi.mocked(api.workflows.create).mockResolvedValue({ id: 'new-wf' } as any);

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      // Find first workflow card and click the clone button within it
      const firstWorkflowCard = screen.getByText('Test Workflow 1').closest('div[class*="border"]');
      const cloneButton = firstWorkflowCard?.querySelector('button[title="Duplicate workflow"]');

      if (cloneButton) {
        await user.click(cloneButton as HTMLElement);
      }

      await waitFor(() => {
        expect(api.workflows.get).toHaveBeenCalledWith('wf-1');
      });

      expect(api.workflows.create).toHaveBeenCalledWith({
        name: 'Test Workflow 1 (Copy)',
        nodes: mockWorkflows[0].nodes,
        edges: mockWorkflows[0].edges,
      });

      expect(toast.success).toHaveBeenCalledWith('Workflow duplicated');
    });

    it('shows error toast on clone failure', async () => {
      const user = userEvent.setup();
      vi.mocked(api.workflows.get).mockRejectedValue(new Error('Failed'));

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const firstWorkflowCard = screen.getByText('Test Workflow 1').closest('div[class*="border"]');
      const cloneButton = firstWorkflowCard?.querySelector('button[title="Duplicate workflow"]');

      if (cloneButton) {
        await user.click(cloneButton as HTMLElement);
      }

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to duplicate workflow');
      });
    });

    it('deletes workflow after confirmation', async () => {
      const user = userEvent.setup();
      mockConfirm.mockResolvedValue(true);
      vi.mocked(api.workflows.delete).mockResolvedValue(undefined as any);

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const firstWorkflowCard = screen.getByText('Test Workflow 1').closest('div[class*="border"]');
      const deleteButton = firstWorkflowCard?.querySelectorAll('button')[1]; // Second button is delete

      if (deleteButton) {
        await user.click(deleteButton as HTMLElement);
      }

      await waitFor(() => {
        expect(mockConfirm).toHaveBeenCalledWith({
          title: 'Delete Workflow',
          description: 'Are you sure you want to delete "Test Workflow 1"? This action cannot be undone.',
          confirmText: 'Delete',
          variant: 'destructive',
        });
      });

      expect(api.workflows.delete).toHaveBeenCalledWith('wf-1');
      expect(toast.success).toHaveBeenCalledWith('Workflow deleted');
    });

    it('does not delete workflow when confirmation cancelled', async () => {
      const user = userEvent.setup();
      mockConfirm.mockResolvedValue(false);

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const firstWorkflowCard = screen.getByText('Test Workflow 1').closest('div[class*="border"]');
      const deleteButton = firstWorkflowCard?.querySelectorAll('button')[1];

      if (deleteButton) {
        await user.click(deleteButton as HTMLElement);
      }

      await waitFor(() => {
        expect(mockConfirm).toHaveBeenCalled();
      });

      expect(api.workflows.delete).not.toHaveBeenCalled();
    });

    it('shows error toast on delete failure', async () => {
      const user = userEvent.setup();
      mockConfirm.mockResolvedValue(true);
      vi.mocked(api.workflows.delete).mockRejectedValue(new Error('Failed'));

      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      });

      const firstWorkflowCard = screen.getByText('Test Workflow 1').closest('div[class*="border"]');
      const deleteButton = firstWorkflowCard?.querySelectorAll('button')[1];

      if (deleteButton) {
        await user.click(deleteButton as HTMLElement);
      }

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to delete workflow');
      });
    });

    it('calls logout when logout button clicked', async () => {
      const user = userEvent.setup();
      render(<WorkflowList />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
      });

      const logoutButton = screen.getByRole('button', { name: /logout/i });
      await user.click(logoutButton);

      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('Error handling', () => {
    it('shows error toast when API fails', async () => {
      vi.mocked(api.workflows.list).mockRejectedValue(new Error('Network error'));

      render(<WorkflowList />);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to load workflows');
      });
    });

    it('stops loading after error', async () => {
      vi.mocked(api.workflows.list).mockRejectedValue(new Error('Network error'));

      render(<WorkflowList />);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled();
      });

      expect(screen.queryByTestId('workflow-list-skeleton')).not.toBeInTheDocument();
    });
  });
});
