import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NodeResultPopup } from './NodeResultPopup';
import type { NodeExecution } from '../../types';

// Mock UI components
vi.mock('../ui/dialog', () => ({
  Dialog: ({ children, open, onOpenChange }: any) => (
    open ? (
      <div data-testid="dialog" onClick={() => onOpenChange(false)}>
        {children}
      </div>
    ) : null
  ),
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <div data-testid="dialog-title">{children}</div>,
  DialogDescription: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('../ui/badge', () => ({
  Badge: ({ children, variant }: any) => (
    <span data-testid="badge" data-variant={variant}>
      {children}
    </span>
  ),
}));

vi.mock('../ui/label', () => ({
  Label: ({ children }: any) => <div data-testid="label">{children}</div>,
}));

describe('NodeResultPopup', () => {
  const mockOnClose = vi.fn();

  const completedExecution: NodeExecution = {
    nodeId: 'test-node-1',
    status: 'completed',
    startedAt: '2024-01-01T00:00:00.000Z',
    completedAt: '2024-01-01T00:00:05.000Z',
    durationMs: 5000,
    retryCount: 0,
    input: { message: 'Hello' },
    output: { response: 'World' },
    error: null,
  };

  const failedExecution: NodeExecution = {
    nodeId: 'test-node-2',
    status: 'failed',
    startedAt: '2024-01-01T00:00:00.000Z',
    completedAt: '2024-01-01T00:00:03.000Z',
    durationMs: 3000,
    retryCount: 2,
    input: { message: 'Test' },
    output: null,
    error: 'Connection timeout',
  };

  it('does not render when nodeExecution is null', () => {
    render(<NodeResultPopup nodeExecution={null} onClose={mockOnClose} />);

    expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
  });

  it('renders dialog when nodeExecution is provided', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByTestId('dialog')).toBeInTheDocument();
  });

  it('displays node ID', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByText('test-node-1')).toBeInTheDocument();
  });

  it('displays completed status badge', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('completed');
    expect(badge).toHaveAttribute('data-variant', 'success');
  });

  it('displays failed status badge', () => {
    render(<NodeResultPopup nodeExecution={failedExecution} onClose={mockOnClose} />);

    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('failed');
    expect(badge).toHaveAttribute('data-variant', 'destructive');
  });

  it('displays start time', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    // The formatted timestamp will be present
    expect(screen.getByText(/Started At/i)).toBeInTheDocument();
  });

  it('displays completion time', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByText(/Completed At/i)).toBeInTheDocument();
  });

  it('displays duration', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByText(/Duration/i)).toBeInTheDocument();
    expect(screen.getByText('5000ms')).toBeInTheDocument();
  });

  it('displays retry count when present', () => {
    render(<NodeResultPopup nodeExecution={failedExecution} onClose={mockOnClose} />);

    expect(screen.getByText(/Retry Count/i)).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('displays input data', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByText('Input')).toBeInTheDocument();
    // The JSON.stringify output should be visible
    const inputSection = screen.getByText('Input').nextSibling;
    expect(inputSection).toBeInTheDocument();
  });

  it('displays output data when present', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    expect(screen.getByText('Output')).toBeInTheDocument();
  });

  it('displays error message when present', () => {
    render(<NodeResultPopup nodeExecution={failedExecution} onClose={mockOnClose} />);

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('calls onClose when dialog is closed', () => {
    render(<NodeResultPopup nodeExecution={completedExecution} onClose={mockOnClose} />);

    const dialog = screen.getByTestId('dialog');
    fireEvent.click(dialog);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('handles running status', () => {
    const runningExecution: NodeExecution = {
      ...completedExecution,
      status: 'running',
      completedAt: null,
      durationMs: null,
    };

    render(<NodeResultPopup nodeExecution={runningExecution} onClose={mockOnClose} />);

    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent('running');
    expect(badge).toHaveAttribute('data-variant', 'default');
  });

  it('formats null output correctly', () => {
    const { container } = render(
      <NodeResultPopup nodeExecution={failedExecution} onClose={mockOnClose} />
    );

    // Output section should not be present when output is null
    expect(screen.queryByText('Output')).not.toBeInTheDocument();
  });
});
