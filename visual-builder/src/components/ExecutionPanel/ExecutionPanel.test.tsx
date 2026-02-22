import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutionPanel } from './ExecutionPanel';
import type { Execution } from '../../types/execution';

const mockFetchExecutions = vi.fn();
const mockFetchExecution = vi.fn();

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector) => {
    const state = { workflowId: 'wf-1' };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

vi.mock('../../stores/executionStore', () => ({
  useExecutionStore: vi.fn(() => ({
    executions: [],
    currentExecution: null,
    isLoading: false,
    fetchExecutions: mockFetchExecutions,
    fetchExecution: mockFetchExecution,
  })),
}));

vi.mock('./LogViewer', () => ({
  LogViewer: ({ nodeExecutions }: any) => <div data-testid="log-viewer">{nodeExecutions.length} logs</div>,
}));

const { useExecutionStore } = await import('../../stores/executionStore');

describe('ExecutionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "Execution History" heading', () => {
    render(<ExecutionPanel />);
    expect(screen.getByText('Execution History')).toBeInTheDocument();
  });

  it('shows "No executions yet" when empty', () => {
    render(<ExecutionPanel />);
    expect(screen.getByText('No executions yet')).toBeInTheDocument();
  });

  it('calls fetchExecutions on mount', () => {
    render(<ExecutionPanel />);
    expect(mockFetchExecutions).toHaveBeenCalledWith('wf-1');
  });

  it('renders execution items when present', () => {
    const mockExecutions: Execution[] = [
      {
        id: 'exec-1',
        workflowId: 'wf-1',
        status: 'completed',
        startedAt: '2024-01-01T12:00:00Z',
        durationMs: 1500,
        nodeExecutions: [],
      },
    ];

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: mockExecutions,
      currentExecution: null,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  it('shows "Select an execution to view logs" when no selection', () => {
    render(<ExecutionPanel />);
    expect(screen.getByText('Select an execution to view logs')).toBeInTheDocument();
  });

  it('clicking execution calls fetchExecution', async () => {
    const user = userEvent.setup();
    const mockExecutions: Execution[] = [
      {
        id: 'exec-1',
        workflowId: 'wf-1',
        status: 'completed',
        startedAt: '2024-01-01T12:00:00Z',
        durationMs: 1500,
        nodeExecutions: [],
      },
    ];

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: mockExecutions,
      currentExecution: null,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    const executionButton = screen.getByRole('button', { name: /completed/i });
    await user.click(executionButton);

    expect(mockFetchExecution).toHaveBeenCalledWith('exec-1');
  });

  it('refresh button exists', () => {
    render(<ExecutionPanel />);
    const refreshButton = screen.getAllByRole('button')[0];
    expect(refreshButton).toBeInTheDocument();
  });

  it('shows "Node Logs" heading', () => {
    render(<ExecutionPanel />);
    expect(screen.getByText('Node Logs')).toBeInTheDocument();
  });

  it('renders LogViewer when execution is selected', () => {
    const mockExecution: Execution = {
      id: 'exec-1',
      workflowId: 'wf-1',
      status: 'completed',
      startedAt: '2024-01-01T12:00:00Z',
      durationMs: 1500,
      nodeExecutions: [
        {
          nodeId: 'node-1',
          status: 'completed',
          startedAt: '2024-01-01T12:00:00Z',
          durationMs: 500,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
      ],
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: [],
      currentExecution: mockExecution,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    expect(screen.getByTestId('log-viewer')).toBeInTheDocument();
  });

  it('displays execution duration in correct format', () => {
    const mockExecutions: Execution[] = [
      {
        id: 'exec-1',
        workflowId: 'wf-1',
        status: 'completed',
        startedAt: '2024-01-01T12:00:00Z',
        durationMs: 1500,
        nodeExecutions: [],
      },
    ];

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: mockExecutions,
      currentExecution: null,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    expect(screen.getByText('1.50s')).toBeInTheDocument();
  });

  it('shows status icons for different execution statuses', () => {
    const mockExecutions: Execution[] = [
      {
        id: 'exec-1',
        workflowId: 'wf-1',
        status: 'completed',
        startedAt: '2024-01-01T12:00:00Z',
        durationMs: 1500,
        nodeExecutions: [],
      },
      {
        id: 'exec-2',
        workflowId: 'wf-1',
        status: 'failed',
        startedAt: '2024-01-01T12:01:00Z',
        durationMs: 800,
        nodeExecutions: [],
      },
    ];

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: mockExecutions,
      currentExecution: null,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('calls fetchExecutions when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<ExecutionPanel />);

    const refreshButton = screen.getAllByRole('button')[1];
    await user.click(refreshButton);

    await waitFor(() => {
      expect(mockFetchExecutions).toHaveBeenCalledTimes(2);
    });
  });

  it('displays token usage when execution has token data', () => {
    const mockExecution: Execution = {
      id: 'exec-1',
      workflowId: 'wf-1',
      status: 'completed',
      mode: 'full',
      triggerType: 'manual',
      triggerId: null,
      input: '{}',
      output: null,
      error: null,
      startedAt: '2024-01-01T12:00:00Z',
      completedAt: '2024-01-01T12:00:01Z',
      durationMs: 1500,
      nodeExecutions: [],
      totalTokens: 2500,
      promptTokens: 1800,
      completionTokens: 700,
      estimatedCost: 0.0035,
      modelUsed: 'gpt-4o',
    };

    vi.mocked(useExecutionStore).mockReturnValue({
      executions: [],
      currentExecution: mockExecution,
      isLoading: false,
      fetchExecutions: mockFetchExecutions,
      fetchExecution: mockFetchExecution,
    });

    render(<ExecutionPanel />);
    expect(screen.getByText('Token Usage')).toBeInTheDocument();
    expect(screen.getByText('2.5k')).toBeInTheDocument();
    expect(screen.getByText('1.8k')).toBeInTheDocument();
    expect(screen.getByText('700')).toBeInTheDocument();
  });
});
