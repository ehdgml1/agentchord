import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PropertiesPanel } from './PropertiesPanel';
import { BlockType } from '../../types/blocks';

// Mock sub-property components
vi.mock('./AgentProperties', () => ({
  AgentProperties: () => <div data-testid="agent-properties">AgentProperties</div>,
}));
vi.mock('./MCPToolProperties', () => ({
  MCPToolProperties: () => <div data-testid="mcp-properties">MCPToolProperties</div>,
}));
vi.mock('./ConditionProperties', () => ({
  ConditionProperties: () => <div data-testid="condition-properties">ConditionProperties</div>,
}));
vi.mock('./ParallelProperties', () => ({
  ParallelProperties: () => <div data-testid="parallel-properties">ParallelProperties</div>,
}));
vi.mock('./FeedbackLoopProperties', () => ({
  FeedbackLoopProperties: () => <div data-testid="feedback-properties">FeedbackProperties</div>,
}));

// Mock workflowStore
const mockUpdateNodeData = vi.fn();
const mockSelectNode = vi.fn();
const mockRemoveNode = vi.fn();

vi.mock('../../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn(() => ({
    updateNodeData: mockUpdateNodeData,
    selectNode: mockSelectNode,
    removeNode: mockRemoveNode,
  })),
  useSelectedNode: vi.fn(() => undefined),
}));

// Import after mocks
import { useSelectedNode } from '../../stores/workflowStore';

describe('PropertiesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows "Select a block to edit" when no node selected', () => {
    vi.mocked(useSelectedNode).mockReturnValue(undefined);
    render(<PropertiesPanel />);
    expect(screen.getByText('Select a block to edit')).toBeInTheDocument();
  });

  it('shows "Agent" title when agent node selected', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-1',
      type: BlockType.AGENT,
      position: { x: 0, y: 0 },
      data: {
        name: 'Test Agent',
        role: 'Assistant',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        maxTokens: 4096,
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByText('Agent')).toBeInTheDocument();
  });

  it('renders AgentProperties for agent node type', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-1',
      type: BlockType.AGENT,
      position: { x: 0, y: 0 },
      data: {
        name: 'Test Agent',
        role: 'Assistant',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        maxTokens: 4096,
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByTestId('agent-properties')).toBeInTheDocument();
  });

  it('renders MCPToolProperties for mcp_tool node type', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-2',
      type: BlockType.MCP_TOOL,
      position: { x: 0, y: 0 },
      data: {
        serverId: 'server-1',
        serverName: 'Test Server',
        toolName: 'test_tool',
        description: 'Test tool',
        parameters: {},
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByTestId('mcp-properties')).toBeInTheDocument();
  });

  it('renders ConditionProperties for condition node type', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-3',
      type: BlockType.CONDITION,
      position: { x: 0, y: 0 },
      data: {
        condition: 'result.success === true',
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByTestId('condition-properties')).toBeInTheDocument();
  });

  it('renders ParallelProperties for parallel node type', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-4',
      type: BlockType.PARALLEL,
      position: { x: 0, y: 0 },
      data: {
        mergeStrategy: 'concat' as const,
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByTestId('parallel-properties')).toBeInTheDocument();
  });

  it('renders FeedbackLoopProperties for feedback_loop node type', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-5',
      type: BlockType.FEEDBACK_LOOP,
      position: { x: 0, y: 0 },
      data: {
        maxIterations: 10,
        stopCondition: 'result.complete === true',
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByTestId('feedback-properties')).toBeInTheDocument();
  });

  it('shows Delete Block button for non-start/end nodes', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-1',
      type: BlockType.AGENT,
      position: { x: 0, y: 0 },
      data: {
        name: 'Test Agent',
        role: 'Assistant',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        maxTokens: 4096,
      },
    });
    render(<PropertiesPanel />);
    expect(screen.getByRole('button', { name: /delete block/i })).toBeInTheDocument();
  });

  it('does NOT show Delete Block for start node', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'start-node',
      type: BlockType.START,
      position: { x: 0, y: 0 },
      data: {},
    });
    render(<PropertiesPanel />);
    expect(screen.queryByRole('button', { name: /delete block/i })).not.toBeInTheDocument();
  });

  it('shows info text for start node', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'start-node',
      type: BlockType.START,
      position: { x: 0, y: 0 },
      data: {},
    });
    render(<PropertiesPanel />);
    expect(screen.getByText(/entry point/i)).toBeInTheDocument();
    expect(screen.getByText(/cannot be configured or deleted/i)).toBeInTheDocument();
  });

  it('shows info text for end node', () => {
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'end-node',
      type: BlockType.END,
      position: { x: 0, y: 0 },
      data: {},
    });
    render(<PropertiesPanel />);
    expect(screen.getByText(/exit point/i)).toBeInTheDocument();
    expect(screen.getByText(/cannot be configured or deleted/i)).toBeInTheDocument();
  });

  it('close button calls selectNode(null)', async () => {
    const user = userEvent.setup();
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-1',
      type: BlockType.AGENT,
      position: { x: 0, y: 0 },
      data: {
        name: 'Test Agent',
        role: 'Assistant',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        maxTokens: 4096,
      },
    });
    render(<PropertiesPanel />);

    const closeButton = screen.getAllByRole('button')[0]; // First button is close (X)
    await user.click(closeButton);

    expect(mockSelectNode).toHaveBeenCalledWith(null);
  });

  it('delete button calls removeNode with node id', async () => {
    const user = userEvent.setup();
    vi.mocked(useSelectedNode).mockReturnValue({
      id: 'node-1',
      type: BlockType.AGENT,
      position: { x: 0, y: 0 },
      data: {
        name: 'Test Agent',
        role: 'Assistant',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        maxTokens: 4096,
      },
    });
    render(<PropertiesPanel />);

    const deleteButton = screen.getByRole('button', { name: /delete block/i });
    await user.click(deleteButton);

    expect(mockRemoveNode).toHaveBeenCalledWith('node-1');
  });
});
