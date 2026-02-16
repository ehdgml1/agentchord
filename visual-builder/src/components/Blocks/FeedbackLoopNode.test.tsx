import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FeedbackLoopNode } from './FeedbackLoopNode';

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: any) => <div data-testid={`handle-${type}`} />,
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock BaseNode
vi.mock('./BaseNode', () => ({
  BaseNode: ({ children, selected, color }: any) => (
    <div data-testid="base-node" data-selected={selected} data-color={color}>
      {children}
    </div>
  ),
}));

describe('FeedbackLoopNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'feedbackLoop',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      maxIterations: 5,
      stopCondition: 'output.success === true',
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders "Feedback Loop" label', () => {
    render(<FeedbackLoopNode {...defaultProps} />);

    expect(screen.getByText('Feedback Loop')).toBeInTheDocument();
  });

  it('displays max iterations', () => {
    render(<FeedbackLoopNode {...defaultProps} />);

    expect(screen.getByText(/Max: 5 iterations/i)).toBeInTheDocument();
  });

  it('renders stop condition when provided', () => {
    render(<FeedbackLoopNode {...defaultProps} />);

    expect(screen.getByText('output.success === true')).toBeInTheDocument();
  });

  it('does not render stop condition when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        maxIterations: 3,
      },
    };
    const { container } = render(<FeedbackLoopNode {...props} />);

    const stopConditionElement = container.querySelector('.font-mono');
    expect(stopConditionElement).not.toBeInTheDocument();
  });

  it('passes selected prop to BaseNode', () => {
    render(<FeedbackLoopNode {...defaultProps} selected={true} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });

  it('uses correct color for BaseNode', () => {
    render(<FeedbackLoopNode {...defaultProps} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-color', '#EC4899');
  });

  it('renders RefreshCw icon', () => {
    const { container } = render(<FeedbackLoopNode {...defaultProps} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('displays different max iterations values', () => {
    const props = {
      ...defaultProps,
      data: {
        maxIterations: 10,
        stopCondition: 'test condition',
      },
    };
    render(<FeedbackLoopNode {...props} />);

    expect(screen.getByText(/Max: 10 iterations/i)).toBeInTheDocument();
  });

  it('truncates long stop conditions', () => {
    const longCondition = 'a'.repeat(100);
    const props = {
      ...defaultProps,
      data: {
        maxIterations: 5,
        stopCondition: longCondition,
      },
    };
    const { container } = render(<FeedbackLoopNode {...props} />);

    const conditionElement = container.querySelector('.truncate');
    expect(conditionElement).toBeInTheDocument();
  });
});
