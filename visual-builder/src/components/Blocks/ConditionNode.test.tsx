import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConditionNode } from './ConditionNode';

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position, id }: any) => (
    <div data-testid={`handle-${type}-${id || 'default'}`} />
  ),
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock BaseNode
vi.mock('./BaseNode', () => ({
  BaseNode: ({ children, selected, hasOutput }: any) => (
    <div data-testid="base-node" data-selected={selected} data-has-output={hasOutput}>
      {children}
    </div>
  ),
}));

describe('ConditionNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'condition',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      condition: 'result.success == true',
      trueLabel: 'Success',
      falseLabel: 'Failed',
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders "Condition" label', () => {
    render(<ConditionNode {...defaultProps} />);
    expect(screen.getByText('Condition')).toBeInTheDocument();
  });

  it('renders condition expression when provided', () => {
    render(<ConditionNode {...defaultProps} />);
    expect(screen.getByText('result.success == true')).toBeInTheDocument();
  });

  it('renders GitFork icon', () => {
    const { container } = render(<ConditionNode {...defaultProps} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders true and false handles', () => {
    render(<ConditionNode {...defaultProps} />);
    expect(screen.getByTestId('handle-source-true')).toBeInTheDocument();
    expect(screen.getByTestId('handle-source-false')).toBeInTheDocument();
  });

  it('renders custom true/false labels', () => {
    render(<ConditionNode {...defaultProps} />);
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('renders default labels when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        condition: 'test',
      },
    };
    render(<ConditionNode {...props} />);
    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });

  it('does not render condition expression when not provided', () => {
    const props = {
      ...defaultProps,
      data: {},
    };
    const { container } = render(<ConditionNode {...props} />);
    const conditionElement = container.querySelector('.font-mono');
    expect(conditionElement).not.toBeInTheDocument();
  });

  it('passes hasOutput=false to BaseNode', () => {
    render(<ConditionNode {...defaultProps} />);
    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-has-output', 'false');
  });

  it('passes selected prop to BaseNode', () => {
    render(<ConditionNode {...defaultProps} selected={true} />);
    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });
});
