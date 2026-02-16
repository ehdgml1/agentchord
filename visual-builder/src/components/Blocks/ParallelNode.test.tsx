import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ParallelNode } from './ParallelNode';

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position, id, style }: any) => (
    <div
      data-testid={`handle-${type}-${id}`}
      data-position={position}
      style={style}
    />
  ),
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock BaseNode
vi.mock('./BaseNode', () => ({
  BaseNode: ({ children, selected, color, hasOutput }: any) => (
    <div
      data-testid="base-node"
      data-selected={selected}
      data-color={color}
      data-has-output={hasOutput}
    >
      {children}
    </div>
  ),
}));

describe('ParallelNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'parallel',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      mergeStrategy: 'all' as const,
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders "Parallel" label', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText('Parallel')).toBeInTheDocument();
  });

  it('displays merge strategy', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByText(/Merge: all/i)).toBeInTheDocument();
  });

  it('renders multiple output handles', () => {
    render(<ParallelNode {...defaultProps} />);

    expect(screen.getByTestId('handle-source-out-1')).toBeInTheDocument();
    expect(screen.getByTestId('handle-source-out-2')).toBeInTheDocument();
  });

  it('positions output handles correctly', () => {
    const { getByTestId } = render(<ParallelNode {...defaultProps} />);

    const handle1 = getByTestId('handle-source-out-1');
    const handle2 = getByTestId('handle-source-out-2');

    expect(handle1).toHaveAttribute('data-position', 'right');
    expect(handle2).toHaveAttribute('data-position', 'right');
  });

  it('passes selected prop to BaseNode', () => {
    render(<ParallelNode {...defaultProps} selected={true} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });

  it('uses correct color for BaseNode', () => {
    render(<ParallelNode {...defaultProps} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-color', '#10B981');
  });

  it('sets hasOutput to false on BaseNode', () => {
    render(<ParallelNode {...defaultProps} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-has-output', 'false');
  });

  it('renders GitBranch icon', () => {
    const { container } = render(<ParallelNode {...defaultProps} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('displays different merge strategies', () => {
    const props = {
      ...defaultProps,
      data: {
        mergeStrategy: 'first' as const,
      },
    };
    render(<ParallelNode {...props} />);

    expect(screen.getByText(/Merge: first/i)).toBeInTheDocument();
  });
});
