import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RunDialog } from './RunDialog';

// Mock stores
const mockSaveWorkflow = vi.fn().mockResolvedValue(undefined);
const mockRunWorkflow = vi.fn().mockResolvedValue({ id: 'exec-1', status: 'running' });

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector) => {
    const state = {
      backendId: 'test-workflow-id',
      saveWorkflow: mockSaveWorkflow,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

vi.mock('../../stores/executionStore', () => ({
  useExecutionStore: vi.fn((selector) => {
    const state = {
      runWorkflow: mockRunWorkflow,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('RunDialog', () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open', () => {
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByText('Run Workflow')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<RunDialog open={false} onOpenChange={mockOnOpenChange} />);
    expect(screen.queryByText('Run Workflow')).not.toBeInTheDocument();
  });

  it('shows execution mode options', () => {
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByText('Full Run')).toBeInTheDocument();
    expect(screen.getByText('Mock Run')).toBeInTheDocument();
    expect(screen.getByText('Debug Mode')).toBeInTheDocument();
  });

  it('shows execution mode descriptions', () => {
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByText('Execute with real APIs and services')).toBeInTheDocument();
    expect(screen.getByText('Use mock responses for testing')).toBeInTheDocument();
    expect(screen.getByText('Step through nodes with detailed logging')).toBeInTheDocument();
  });

  it('has input textarea', () => {
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);
    expect(screen.getByPlaceholderText(/enter your workflow input here/i)).toBeInTheDocument();
  });

  it('shows error when input is empty', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const runButton = screen.getByRole('button', { name: /run/i });
    await user.click(runButton);

    expect(toast.error).toHaveBeenCalledWith('Please provide input for the workflow');
  });

  it('allows typing in input textarea', async () => {
    const user = userEvent.setup();
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const textarea = screen.getByPlaceholderText(/enter your workflow input here/i) as HTMLTextAreaElement;
    await user.type(textarea, 'test input');

    expect(textarea.value).toBe('test input');
  });

  it('has cancel and run buttons', () => {
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument();
  });

  it('calls onOpenChange when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('runs workflow with valid input', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const textarea = screen.getByPlaceholderText(/enter your workflow input here/i);
    await user.type(textarea, 'test input');

    const runButton = screen.getByRole('button', { name: /run/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(mockRunWorkflow).toHaveBeenCalledWith('test-workflow-id', 'test input', 'full');
      expect(toast.success).toHaveBeenCalledWith('Workflow execution started');
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('can select different execution modes', async () => {
    const user = userEvent.setup();
    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const mockRadio = screen.getByRole('radio', { name: /mock run/i });
    await user.click(mockRadio);

    expect(mockRadio).toBeChecked();
  });

  it('disables buttons while running', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();

    // Make runWorkflow take some time
    mockRunWorkflow.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const textarea = screen.getByPlaceholderText(/enter your workflow input here/i);
    await user.type(textarea, 'test input');

    const runButton = screen.getByRole('button', { name: /run/i });
    const cancelButton = screen.getByRole('button', { name: /cancel/i });

    await user.click(runButton);

    // Buttons should be disabled while running
    expect(runButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
    expect(screen.getByText(/running\.\.\./i)).toBeInTheDocument();

    // Wait for completion
    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalled();
    });
  });

  it('clears input after successful run', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const textarea = screen.getByPlaceholderText(/enter your workflow input here/i) as HTMLTextAreaElement;
    await user.type(textarea, 'test input');

    const runButton = screen.getByRole('button', { name: /run/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    // Reopen dialog
    rerender(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const newTextarea = screen.getByPlaceholderText(/enter your workflow input here/i) as HTMLTextAreaElement;
    expect(newTextarea.value).toBe('');
  });

  it('handles run workflow error', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();

    mockRunWorkflow.mockRejectedValueOnce(new Error('Network error'));

    render(<RunDialog open={true} onOpenChange={mockOnOpenChange} />);

    const textarea = screen.getByPlaceholderText(/enter your workflow input here/i);
    await user.type(textarea, 'test input');

    const runButton = screen.getByRole('button', { name: /run/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Network error');
    });
  });
});
