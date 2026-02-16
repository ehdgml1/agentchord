import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from './Sidebar';
import { BLOCK_DEFINITIONS } from '../../constants/blocks';

vi.mock('./MCPHub', () => ({
  MCPHub: () => <div data-testid="mcp-hub">MCPHub</div>,
}));

describe('Sidebar', () => {
  it('renders sidebar container', () => {
    const { container } = render(<Sidebar />);
    const aside = container.querySelector('aside');
    expect(aside).toBeInTheDocument();
  });

  it('renders block items section', () => {
    render(<Sidebar />);
    expect(screen.getByText('Blocks')).toBeInTheDocument();
  });

  it('renders MCPHub component', () => {
    render(<Sidebar />);
    expect(screen.getByTestId('mcp-hub')).toBeInTheDocument();
  });

  it('shows Agent block type', () => {
    render(<Sidebar />);
    expect(screen.getByText('Agent')).toBeInTheDocument();
    expect(screen.getByText('AI agent that processes inputs')).toBeInTheDocument();
  });

  it('shows MCP Tool block type', () => {
    render(<Sidebar />);
    expect(screen.getByText('MCP Tool')).toBeInTheDocument();
    expect(screen.getByText('External tool via MCP protocol')).toBeInTheDocument();
  });

  it('shows Condition block type', () => {
    render(<Sidebar />);
    expect(screen.getByText('Condition')).toBeInTheDocument();
    expect(screen.getByText('Branch based on condition')).toBeInTheDocument();
  });

  it('block items are draggable', () => {
    const { container } = render(<Sidebar />);
    const draggableElements = container.querySelectorAll('[draggable="true"]');

    expect(draggableElements.length).toBe(BLOCK_DEFINITIONS.length);
  });

  it('block items have correct drag data', () => {
    const { container } = render(<Sidebar />);
    const firstDraggable = container.querySelector('[draggable="true"]');

    expect(firstDraggable).toBeInTheDocument();

    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };

    if (firstDraggable) {
      fireEvent.dragStart(firstDraggable, { dataTransfer });

      expect(dataTransfer.setData).toHaveBeenCalledWith(
        'application/reactflow',
        expect.any(String)
      );
    }
  });

  it('renders tips section', () => {
    render(<Sidebar />);
    expect(screen.getByText('Tips')).toBeInTheDocument();
    expect(screen.getByText('Drag blocks to the canvas')).toBeInTheDocument();
    expect(screen.getByText('Connect blocks by dragging handles')).toBeInTheDocument();
    expect(screen.getByText('Click a block to edit properties')).toBeInTheDocument();
  });

  it('renders all block definitions', () => {
    render(<Sidebar />);

    BLOCK_DEFINITIONS.forEach((definition) => {
      expect(screen.getByText(definition.label)).toBeInTheDocument();
      expect(screen.getByText(definition.description)).toBeInTheDocument();
    });
  });

  it('applies custom className when provided', () => {
    const { container } = render(<Sidebar className="custom-class" />);
    const aside = container.querySelector('aside');

    expect(aside).toHaveClass('custom-class');
  });
});
