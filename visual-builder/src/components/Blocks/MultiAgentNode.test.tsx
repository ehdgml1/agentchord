import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MultiAgentNode } from './MultiAgentNode';

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: any) => <div data-testid={`handle-${type}`} />,
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock BaseNode to simplify testing
vi.mock('./BaseNode', () => ({
  BaseNode: ({ children, selected }: any) => (
    <div data-testid="base-node" data-selected={selected}>
      {children}
    </div>
  ),
}));

describe('MultiAgentNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'multi_agent',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      name: 'Research Team',
      strategy: 'coordinator' as const,
      members: [
        {
          id: 'member_1',
          name: 'Researcher',
          role: 'worker' as const,
          model: 'gpt-4o',
          systemPrompt: 'You are a researcher',
          capabilities: ['search'],
          temperature: 0.7,
        },
        {
          id: 'member_2',
          name: 'Reviewer',
          role: 'reviewer' as const,
          model: 'gpt-4o-mini',
          systemPrompt: 'You review research',
          capabilities: ['review'],
          temperature: 0.3,
        },
      ],
      maxRounds: 5,
      costBudget: 1.0,
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders team name', () => {
    render(<MultiAgentNode {...defaultProps} />);
    expect(screen.getByText('Research Team')).toBeInTheDocument();
  });

  it('renders strategy label', () => {
    render(<MultiAgentNode {...defaultProps} />);
    // Strategy is rendered with member count in the same element
    expect(screen.getByText(/Coordinator/)).toBeInTheDocument();
  });

  it('renders member count', () => {
    render(<MultiAgentNode {...defaultProps} />);
    expect(screen.getByText(/2 members/)).toBeInTheDocument();
  });

  it('renders singular member count for 1 member', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        members: [defaultProps.data.members[0]],
      },
    };
    render(<MultiAgentNode {...props} />);
    expect(screen.getByText(/1 member(?!s)/)).toBeInTheDocument();
  });

  it('shows "Unnamed Team" when name is missing', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        name: '',
      },
    };
    render(<MultiAgentNode {...props} />);
    expect(screen.getByText('Unnamed Team')).toBeInTheDocument();
  });

  it('renders Users icon', () => {
    const { container } = render(<MultiAgentNode {...defaultProps} />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('passes selected prop to BaseNode', () => {
    render(<MultiAgentNode {...defaultProps} selected={true} />);
    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });

  it('renders max rounds when greater than 0', () => {
    render(<MultiAgentNode {...defaultProps} />);
    expect(screen.getByText('Max 5 rounds')).toBeInTheDocument();
  });

  it('renders 0 members when members array is empty', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        members: [],
      },
    };
    render(<MultiAgentNode {...props} />);
    expect(screen.getByText(/0 members/)).toBeInTheDocument();
  });

  it('renders correct strategy labels', () => {
    const strategies = [
      { strategy: 'round_robin' as const, label: 'Round Robin' },
      { strategy: 'debate' as const, label: 'Debate' },
      { strategy: 'map_reduce' as const, label: 'Map-Reduce' },
    ];

    for (const { strategy, label } of strategies) {
      const props = {
        ...defaultProps,
        data: {
          ...defaultProps.data,
          strategy,
        },
      };
      const { unmount } = render(<MultiAgentNode {...props} />);
      expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
      unmount();
    }
  });

  it('has correct aria-label', () => {
    render(<MultiAgentNode {...defaultProps} />);
    expect(screen.getByLabelText('Multi-Agent node: Research Team')).toBeInTheDocument();
  });
});
