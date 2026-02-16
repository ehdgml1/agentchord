import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Canvas } from './Canvas';

// Mock @xyflow/react - it has complex DOM dependencies that don't work well in jsdom
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="react-flow-mock">{children}</div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  MiniMap: () => <div data-testid="minimap" />,
}));

// Mock the workflow store
vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: () => ({
    nodes: [],
    edges: [],
    onNodesChange: vi.fn(),
    onEdgesChange: vi.fn(),
    onConnect: vi.fn(),
    addNode: vi.fn(),
    selectNode: vi.fn(),
  }),
}));

// Mock the node types
vi.mock('../Blocks', () => ({
  nodeTypes: {},
}));

describe('Canvas', () => {
  it('renders without crashing', () => {
    const { container } = render(<Canvas />);
    expect(container).toBeInTheDocument();
  });

  it('renders ReactFlow component', () => {
    const { getByTestId } = render(<Canvas />);
    expect(getByTestId('react-flow-mock')).toBeInTheDocument();
  });

  it('renders Background, Controls, and MiniMap', () => {
    const { getByTestId } = render(<Canvas />);
    expect(getByTestId('background')).toBeInTheDocument();
    expect(getByTestId('controls')).toBeInTheDocument();
    expect(getByTestId('minimap')).toBeInTheDocument();
  });
});
