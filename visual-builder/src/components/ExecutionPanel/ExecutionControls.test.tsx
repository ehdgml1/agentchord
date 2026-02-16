import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutionControls } from './ExecutionControls';
import { useExecutionStore } from '../../stores/executionStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import type { Execution } from '../../types';

// Mock the stores
vi.mock('../../stores/executionStore');
vi.mock('../../stores/workflowStore');

describe('ExecutionControls', () => {
  const mockRunWorkflow = vi.fn();
  const mockStopExecution = vi.fn();
  const mockResumeExecution = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementation
    vi.mocked(useWorkflowStore).mockImplementation((selector: any) => {
      const state = {
        workflowId: 'test-workflow-id',
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: null,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);
  });

  it('renders run button when workflow exists', () => {
    render(<ExecutionControls />);

    expect(screen.getByRole('button', { name: /run workflow/i })).toBeInTheDocument();
  });

  it('disables run button when no workflow exists', () => {
    vi.mocked(useWorkflowStore).mockImplementation((selector: any) => {
      const state = {
        workflowId: '',
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    render(<ExecutionControls />);

    const runButton = screen.getByRole('button', { name: /run workflow/i });
    expect(runButton).toBeDisabled();
  });

  it('disables run button during loading', () => {
    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: null,
      isLoading: true,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    const runButton = screen.getByRole('button', { name: /run workflow/i });
    expect(runButton).toBeDisabled();
  });

  it('disables run button when execution is running', () => {
    const runningExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'running',
      durationMs: 1000,
      output: null,
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: null,
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: runningExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    const runButton = screen.getByRole('button', { name: /run workflow/i });
    expect(runButton).toBeDisabled();
  });

  it('shows stop button when execution is running', () => {
    const runningExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'running',
      durationMs: 1000,
      output: null,
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: null,
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: runningExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByRole('button', { name: /stop workflow execution/i })).toBeInTheDocument();
  });

  it('shows resume button when execution is paused', () => {
    const pausedExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'paused',
      durationMs: 1000,
      output: null,
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: null,
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: pausedExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByRole('button', { name: /resume paused workflow/i })).toBeInTheDocument();
  });

  it('displays execution status badge', () => {
    const completedExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'completed',
      durationMs: 2500,
      output: { result: 'success' },
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: completedExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('formats and displays execution duration', () => {
    const execution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'running',
      durationMs: 3450,
      output: null,
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: null,
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: execution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    const { container } = render(<ExecutionControls />);

    expect(screen.getByText(/duration:/i)).toBeInTheDocument();
    // Check that the duration text exists in the container
    expect(container.textContent).toContain('3.45s');
  });

  it('calls runWorkflow with correct parameters', async () => {
    const user = userEvent.setup();

    render(<ExecutionControls />);

    const runButton = screen.getByRole('button', { name: /run workflow/i });
    await user.click(runButton);

    expect(mockRunWorkflow).toHaveBeenCalledWith('test-workflow-id', '{}', 'mock');
  });

  it('calls stopExecution when stop button clicked', async () => {
    const user = userEvent.setup();
    const runningExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'running',
      durationMs: 1000,
      output: null,
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: null,
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: runningExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    const stopButton = screen.getByRole('button', { name: /stop workflow execution/i });
    await user.click(stopButton);

    expect(mockStopExecution).toHaveBeenCalledWith('exec-1');
  });

  it('displays error message when present', () => {
    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: null,
      isLoading: false,
      error: 'Failed to start execution',
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByText('Failed to start execution')).toBeInTheDocument();
  });

  it('displays execution output when available', () => {
    const completedExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'completed',
      durationMs: 2500,
      output: { result: 'success', value: 42 },
      error: null,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: completedExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByText(/output/i)).toBeInTheDocument();
    expect(screen.getByText(/"result": "success"/)).toBeInTheDocument();
  });

  it('displays execution error when present', () => {
    const failedExecution: Execution = {
      id: 'exec-1',
      workflowId: 'test-workflow-id',
      status: 'failed',
      durationMs: 500,
      output: null,
      error: 'Connection timeout',
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      currentExecution: failedExecution,
      isLoading: false,
      error: null,
      runWorkflow: mockRunWorkflow,
      stopExecution: mockStopExecution,
      resumeExecution: mockResumeExecution,
    } as unknown as ReturnType<typeof useExecutionStore>);

    render(<ExecutionControls />);

    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });
});
