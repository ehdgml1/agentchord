import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BlockItem } from './BlockItem';
import type { BlockDefinition } from '../../types/blocks';

const mockDefinition: BlockDefinition = {
  type: 'agent',
  label: 'Agent',
  description: 'AI agent that processes inputs',
  icon: 'Bot',
  color: '#3B82F6',
  defaultData: { name: '', role: '', model: 'gpt-4o-mini', temperature: 0.7, maxTokens: 4096 },
};

const mockMCPToolDefinition: BlockDefinition = {
  type: 'mcp_tool',
  label: 'MCP Tool',
  description: 'External tool integration',
  icon: 'Wrench',
  color: '#10B981',
  defaultData: { serverId: '', serverName: '', toolName: '', description: '', parameters: {} },
};

const mockConditionDefinition: BlockDefinition = {
  type: 'condition',
  label: 'Condition',
  description: 'Branch based on condition',
  icon: 'GitBranch',
  color: '#F59E0B',
  defaultData: { condition: '', trueLabel: 'Yes', falseLabel: 'No' },
};

describe('BlockItem', () => {
  it('renders block label', () => {
    render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('renders block description', () => {
    render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    expect(screen.getByText('AI agent that processes inputs')).toBeInTheDocument();
  });

  it('has draggable attribute', () => {
    render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = screen.getByText('Agent').closest('[draggable]');
    expect(item).toHaveAttribute('draggable', 'true');
  });

  it('calls onDragStart with correct type on drag', () => {
    const mockOnDragStart = vi.fn();
    render(<BlockItem definition={mockDefinition} onDragStart={mockOnDragStart} />);
    const item = screen.getByText('Agent').closest('[draggable]')!;
    fireEvent.dragStart(item);
    expect(mockOnDragStart).toHaveBeenCalled();
    expect(mockOnDragStart).toHaveBeenCalledWith(expect.any(Object), 'agent');
  });

  it('renders with correct color styling', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const iconContainer = container.querySelector('[style*="color"]');
    expect(iconContainer).toHaveStyle({ color: '#3B82F6' });
  });

  it('renders icon container', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const iconContainer = container.querySelector('.p-2.rounded-md');
    expect(iconContainer).toBeInTheDocument();
  });

  it('renders mcp_tool block type correctly', () => {
    render(<BlockItem definition={mockMCPToolDefinition} onDragStart={vi.fn()} />);
    expect(screen.getByText('MCP Tool')).toBeInTheDocument();
    expect(screen.getByText('External tool integration')).toBeInTheDocument();
  });

  it('renders condition block type correctly', () => {
    render(<BlockItem definition={mockConditionDefinition} onDragStart={vi.fn()} />);
    expect(screen.getByText('Condition')).toBeInTheDocument();
    expect(screen.getByText('Branch based on condition')).toBeInTheDocument();
  });

  it('applies hover styles classes', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = container.querySelector('.hover\\:bg-accent');
    expect(item).toBeInTheDocument();
    expect(item).toHaveClass('hover:bg-accent');
  });

  it('has cursor-grab class', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = container.querySelector('.cursor-grab');
    expect(item).toBeInTheDocument();
  });

  it('has active:cursor-grabbing class', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = container.querySelector('.active\\:cursor-grabbing');
    expect(item).toBeInTheDocument();
  });

  it('renders with border class', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = container.querySelector('.border');
    expect(item).toBeInTheDocument();
  });

  it('renders with rounded-lg class', () => {
    const { container } = render(<BlockItem definition={mockDefinition} onDragStart={vi.fn()} />);
    const item = container.querySelector('.rounded-lg');
    expect(item).toBeInTheDocument();
  });

  it('passes correct drag event to onDragStart', () => {
    const mockOnDragStart = vi.fn();
    render(<BlockItem definition={mockDefinition} onDragStart={mockOnDragStart} />);
    const item = screen.getByText('Agent').closest('[draggable]')!;
    fireEvent.dragStart(item);
    expect(mockOnDragStart).toHaveBeenCalledTimes(1);
  });
});
