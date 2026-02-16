import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentNode } from './AgentNode';

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

describe('AgentNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'agent',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      name: 'Test Agent',
      model: 'gpt-4o' as const,
      role: 'You are a helpful assistant',
      temperature: 0.7,
      maxTokens: 2000,
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders agent name', () => {
    render(<AgentNode {...defaultProps} />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  it('renders model name from MODELS constant', () => {
    render(<AgentNode {...defaultProps} />);
    expect(screen.getByText('GPT-4o')).toBeInTheDocument();
  });

  it('renders role when provided', () => {
    render(<AgentNode {...defaultProps} />);
    expect(screen.getByText('You are a helpful assistant')).toBeInTheDocument();
  });

  it('shows "Unnamed Agent" when name is missing', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        name: '',
      },
    };
    render(<AgentNode {...props} />);
    expect(screen.getByText('Unnamed Agent')).toBeInTheDocument();
  });

  it('renders Bot icon', () => {
    const { container } = render(<AgentNode {...defaultProps} />);
    // Lucide-react renders SVG icons
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('passes selected prop to BaseNode', () => {
    render(<AgentNode {...defaultProps} selected={true} />);
    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });

  it('does not render role when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        role: undefined,
      },
    };
    const { container } = render(<AgentNode {...props} />);
    const roleElement = container.querySelector('.line-clamp-2');
    expect(roleElement).not.toBeInTheDocument();
  });

  it('displays fallback model name when model not in MODELS', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        model: 'unknown-model' as any,
      },
    };
    render(<AgentNode {...props} />);
    expect(screen.getByText('unknown-model')).toBeInTheDocument();
  });
});
