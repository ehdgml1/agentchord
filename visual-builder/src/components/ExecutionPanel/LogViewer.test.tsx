import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LogViewer } from './LogViewer';
import type { NodeExecution } from '../../types/execution';

const mockNodeExec: NodeExecution = {
  nodeId: 'node-1',
  status: 'completed',
  startedAt: '2024-01-01T12:00:00Z',
  durationMs: 500,
  retryCount: 0,
  input: 'test input',
  output: 'test output',
  error: null,
};

describe('LogViewer', () => {
  it('shows "No execution logs available" when empty', () => {
    render(<LogViewer nodeExecutions={[]} />);
    expect(screen.getByText('No execution logs available')).toBeInTheDocument();
  });

  it('renders node executions', () => {
    render(<LogViewer nodeExecutions={[mockNodeExec]} />);
    expect(screen.getByText('node-1')).toBeInTheDocument();
  });

  it('shows node ID for each execution', () => {
    const nodeExecs: NodeExecution[] = [
      { ...mockNodeExec, nodeId: 'node-1' },
      { ...mockNodeExec, nodeId: 'node-2' },
    ];
    render(<LogViewer nodeExecutions={nodeExecs} />);
    expect(screen.getByText('node-1')).toBeInTheDocument();
    expect(screen.getByText('node-2')).toBeInTheDocument();
  });

  it('shows duration', () => {
    render(<LogViewer nodeExecutions={[mockNodeExec]} />);
    expect(screen.getByText('(500ms)')).toBeInTheDocument();
  });

  it('shows input text', () => {
    render(<LogViewer nodeExecutions={[mockNodeExec]} />);
    expect(screen.getByText('Input:')).toBeInTheDocument();
    expect(screen.getByText('test input')).toBeInTheDocument();
  });

  it('shows output text', () => {
    render(<LogViewer nodeExecutions={[mockNodeExec]} />);
    expect(screen.getByText('Output:')).toBeInTheDocument();
    expect(screen.getByText('test output')).toBeInTheDocument();
  });

  it('shows error for failed nodes', () => {
    const failedExec: NodeExecution = {
      ...mockNodeExec,
      status: 'failed',
      error: 'Test error message',
    };
    render(<LogViewer nodeExecutions={[failedExec]} />);
    expect(screen.getByText('Error:')).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('shows retry count when > 0', () => {
    const retryExec: NodeExecution = {
      ...mockNodeExec,
      retryCount: 2,
    };
    render(<LogViewer nodeExecutions={[retryExec]} />);
    expect(screen.getByText('Retry 2')).toBeInTheDocument();
  });

  it('has role="log" attribute', () => {
    render(<LogViewer nodeExecutions={[mockNodeExec]} />);
    expect(screen.getByRole('log')).toBeInTheDocument();
  });

  it('sorts by startedAt', () => {
    const nodeExecs: NodeExecution[] = [
      { ...mockNodeExec, nodeId: 'node-2', startedAt: '2024-01-01T12:01:00Z' },
      { ...mockNodeExec, nodeId: 'node-1', startedAt: '2024-01-01T12:00:00Z' },
    ];
    render(<LogViewer nodeExecutions={nodeExecs} />);
    const nodeIds = screen.getAllByText(/node-/);
    expect(nodeIds[0]).toHaveTextContent('node-1');
    expect(nodeIds[1]).toHaveTextContent('node-2');
  });

  it('handles JSON input objects', () => {
    const jsonExec: NodeExecution = {
      ...mockNodeExec,
      input: { key: 'value' },
    };
    render(<LogViewer nodeExecutions={[jsonExec]} />);
    expect(screen.getByText(/"key":/)).toBeInTheDocument();
  });

  it('handles JSON output objects', () => {
    const jsonExec: NodeExecution = {
      ...mockNodeExec,
      output: { result: 'success' },
    };
    render(<LogViewer nodeExecutions={[jsonExec]} />);
    expect(screen.getByText(/"result":/)).toBeInTheDocument();
  });

  it('does not show retry count when 0', () => {
    const zeroRetryExec: NodeExecution = {
      ...mockNodeExec,
      retryCount: 0,
    };
    render(<LogViewer nodeExecutions={[zeroRetryExec]} />);
    expect(screen.queryByText(/Retry/)).not.toBeInTheDocument();
  });

  it('handles undefined input gracefully', () => {
    const noInputExec: NodeExecution = {
      ...mockNodeExec,
      input: undefined,
    };
    render(<LogViewer nodeExecutions={[noInputExec]} />);
    expect(screen.queryByText('Input:')).not.toBeInTheDocument();
  });
});
