import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ExecutionProgress } from './ExecutionProgress';
import type { Execution } from '../../types';

const mockExecution: Execution = {
  id: 'exec-1',
  workflowId: 'wf-1',
  status: 'running',
  startedAt: '2024-01-01T12:00:00Z',
  durationMs: null,
  nodeExecutions: [
    {
      nodeId: 'n1',
      status: 'completed',
      startedAt: '2024-01-01T12:00:00Z',
      durationMs: 200,
      retryCount: 0,
      input: null,
      output: null,
      error: null,
    },
    {
      nodeId: 'n2',
      status: 'running',
      startedAt: '2024-01-01T12:00:01Z',
      durationMs: null,
      retryCount: 0,
      input: null,
      output: null,
      error: null,
    },
  ],
};

describe('ExecutionProgress', () => {
  it('shows progress percentage', () => {
    render(<ExecutionProgress execution={mockExecution} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows node count (completed / total)', () => {
    render(<ExecutionProgress execution={mockExecution} />);
    expect(screen.getByText('1 / 2 nodes')).toBeInTheDocument();
  });

  it('renders node execution items', () => {
    render(<ExecutionProgress execution={mockExecution} />);
    expect(screen.getByText('n1')).toBeInTheDocument();
    expect(screen.getByText('n2')).toBeInTheDocument();
  });

  it('shows correct status badge text', () => {
    render(<ExecutionProgress execution={mockExecution} />);
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('shows duration for nodes with durationMs', () => {
    render(<ExecutionProgress execution={mockExecution} />);
    expect(screen.getByText('200ms')).toBeInTheDocument();
  });

  it('progress is 100% when all completed', () => {
    const completedExecution: Execution = {
      ...mockExecution,
      status: 'completed',
      nodeExecutions: [
        {
          nodeId: 'n1',
          status: 'completed',
          startedAt: '2024-01-01T12:00:00Z',
          durationMs: 200,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
        {
          nodeId: 'n2',
          status: 'completed',
          startedAt: '2024-01-01T12:00:01Z',
          durationMs: 150,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
      ],
    };

    render(<ExecutionProgress execution={completedExecution} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('2 / 2 nodes')).toBeInTheDocument();
  });

  it('progress is 0% when none completed', () => {
    const pendingExecution: Execution = {
      ...mockExecution,
      status: 'pending',
      nodeExecutions: [
        {
          nodeId: 'n1',
          status: 'pending',
          startedAt: '2024-01-01T12:00:00Z',
          durationMs: null,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
      ],
    };

    render(<ExecutionProgress execution={pendingExecution} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('0 / 1 nodes')).toBeInTheDocument();
  });

  it('empty node executions shows 0/0', () => {
    const emptyExecution: Execution = {
      ...mockExecution,
      nodeExecutions: [],
    };

    render(<ExecutionProgress execution={emptyExecution} />);
    expect(screen.getByText('0 / 0 nodes')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('counts failed nodes as completed for progress', () => {
    const failedExecution: Execution = {
      ...mockExecution,
      status: 'failed',
      nodeExecutions: [
        {
          nodeId: 'n1',
          status: 'failed',
          startedAt: '2024-01-01T12:00:00Z',
          durationMs: 100,
          retryCount: 0,
          input: null,
          output: null,
          error: 'Test error',
        },
        {
          nodeId: 'n2',
          status: 'pending',
          startedAt: '2024-01-01T12:00:01Z',
          durationMs: null,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
      ],
    };

    render(<ExecutionProgress execution={failedExecution} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('1 / 2 nodes')).toBeInTheDocument();
  });

  it('shows all status badge variants correctly', () => {
    const multiStatusExecution: Execution = {
      ...mockExecution,
      nodeExecutions: [
        {
          nodeId: 'n1',
          status: 'completed',
          startedAt: '2024-01-01T12:00:00Z',
          durationMs: 100,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
        {
          nodeId: 'n2',
          status: 'failed',
          startedAt: '2024-01-01T12:00:01Z',
          durationMs: 50,
          retryCount: 0,
          input: null,
          output: null,
          error: 'Error',
        },
        {
          nodeId: 'n3',
          status: 'running',
          startedAt: '2024-01-01T12:00:02Z',
          durationMs: null,
          retryCount: 0,
          input: null,
          output: null,
          error: null,
        },
      ],
    };

    render(<ExecutionProgress execution={multiStatusExecution} />);
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });
});
