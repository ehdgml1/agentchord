import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MCPToolNode } from './MCPToolNode';

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

describe('MCPToolNode', () => {
  const defaultProps = {
    id: 'test-node',
    type: 'mcpTool',
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    data: {
      toolName: 'list_files',
      serverName: 'filesystem',
      description: 'List files in a directory',
    },
    dragging: false,
    zIndex: 0,
  };

  it('renders tool name', () => {
    render(<MCPToolNode {...defaultProps} />);

    expect(screen.getByText('list_files')).toBeInTheDocument();
  });

  it('renders server name', () => {
    render(<MCPToolNode {...defaultProps} />);

    expect(screen.getByText('filesystem')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(<MCPToolNode {...defaultProps} />);

    expect(screen.getByText('List files in a directory')).toBeInTheDocument();
  });

  it('shows default tool name when toolName is missing', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        toolName: '',
      },
    };
    render(<MCPToolNode {...props} />);

    expect(screen.getByText('MCP Tool')).toBeInTheDocument();
  });

  it('shows "Unknown Server" when serverName is missing', () => {
    const props = {
      ...defaultProps,
      data: {
        ...defaultProps.data,
        serverName: '',
      },
    };
    render(<MCPToolNode {...props} />);

    expect(screen.getByText('Unknown Server')).toBeInTheDocument();
  });

  it('does not render description when not provided', () => {
    const props = {
      ...defaultProps,
      data: {
        toolName: 'test_tool',
        serverName: 'test_server',
      },
    };
    const { container } = render(<MCPToolNode {...props} />);

    const descriptionElement = container.querySelector('.line-clamp-2');
    expect(descriptionElement).not.toBeInTheDocument();
  });

  it('passes selected prop to BaseNode', () => {
    render(<MCPToolNode {...defaultProps} selected={true} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-selected', 'true');
  });

  it('uses correct color for BaseNode', () => {
    render(<MCPToolNode {...defaultProps} />);

    const baseNode = screen.getByTestId('base-node');
    expect(baseNode).toHaveAttribute('data-color', '#8B5CF6');
  });

  it('renders Wrench icon', () => {
    const { container } = render(<MCPToolNode {...defaultProps} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
