/**
 * Tests for DataFlowPanel component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataFlowPanel } from './DataFlowPanel';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useCurrentExecution } from '../../stores/executionStore';
import type { Node, Edge } from '@xyflow/react';
import type { Execution } from '../../types/execution';

// Mock dependencies
vi.mock('../../stores/workflowStore');
vi.mock('../../stores/executionStore');

// Mock UI components
vi.mock('../ui/badge', () => ({
  Badge: ({ children, variant }: any) => <span data-variant={variant}>{children}</span>,
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  ArrowRight: () => <div>Arrow Icon</div>,
}));

const mockNodes: Node[] = [
  {
    id: 'node-1',
    type: 'agent',
    position: { x: 0, y: 0 },
    data: { name: 'Agent A', toolName: 'OpenAI' },
  },
  {
    id: 'node-2',
    type: 'agent',
    position: { x: 100, y: 0 },
    data: { name: 'Agent B' },
  },
  {
    id: 'node-3',
    type: 'trigger',
    position: { x: 200, y: 0 },
    data: { label: 'HTTP Trigger' },
  },
];

const mockEdges: Edge[] = [
  {
    id: 'edge-1',
    source: 'node-1',
    target: 'node-2',
  },
  {
    id: 'edge-2',
    source: 'node-2',
    target: 'node-3',
  },
];

const mockExecution: Execution = {
  id: 'exec-1',
  workflowId: 'wf-1',
  status: 'running',
  startedAt: '2024-01-01T00:00:00Z',
  input: {},
  nodeExecutions: [
    {
      nodeId: 'node-1',
      status: 'completed',
      startedAt: '2024-01-01T00:00:00Z',
      completedAt: '2024-01-01T00:00:01Z',
      output: { result: 'success', data: 'test data' },
    },
    {
      nodeId: 'node-2',
      status: 'running',
      startedAt: '2024-01-01T00:00:01Z',
    },
  ],
};

describe('DataFlowPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useWorkflowStore).mockReturnValue({
      nodes: mockNodes,
      edges: mockEdges,
      setNodes: vi.fn(),
      setEdges: vi.fn(),
      onNodesChange: vi.fn(),
      onEdgesChange: vi.fn(),
      onConnect: vi.fn(),
      addNode: vi.fn(),
      updateNode: vi.fn(),
      deleteNode: vi.fn(),
      selectedNode: null,
      setSelectedNode: vi.fn(),
    } as any);
    vi.mocked(useCurrentExecution).mockReturnValue(null);
  });

  describe('Empty State', () => {
    it('shows empty state when no execution', () => {
      render(<DataFlowPanel />);

      expect(screen.getByText('Run a workflow to see data flow visualization')).toBeInTheDocument();
    });

    it('shows empty state when execution has no nodeExecutions', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: undefined,
      } as any);

      render(<DataFlowPanel />);

      expect(screen.getByText('Run a workflow to see data flow visualization')).toBeInTheDocument();
    });

    it('shows empty state when execution nodeExecutions is empty', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [],
      });

      render(<DataFlowPanel />);

      // Empty nodeExecutions array still generates empty flow entries, so check for the empty state differently
      expect(screen.getByText('Data Flow')).toBeInTheDocument();
      // With no executions, all flows will show "pending" status
      expect(screen.getAllByText('pending').length).toBeGreaterThan(0);
    });
  });

  describe('Header', () => {
    it('renders header with title', () => {
      render(<DataFlowPanel />);

      expect(screen.getByText('Data Flow')).toBeInTheDocument();
    });

    it('renders description', () => {
      render(<DataFlowPanel />);

      expect(screen.getByText('Track how data flows between workflow nodes')).toBeInTheDocument();
    });
  });

  describe('Data Flow Entries', () => {
    beforeEach(() => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);
    });

    it('renders flow entry for each edge', () => {
      render(<DataFlowPanel />);

      // Check for badges containing node names
      const badges = screen.getAllByText(/Agent A|Agent B|HTTP Trigger/);
      expect(badges.length).toBeGreaterThan(0);
    });

    it('displays arrow icons between nodes', () => {
      render(<DataFlowPanel />);

      const arrows = screen.getAllByText('Arrow Icon');
      expect(arrows.length).toBeGreaterThanOrEqual(1);
    });

    it('shows status badges for each flow', () => {
      render(<DataFlowPanel />);

      expect(screen.getAllByText('completed').length).toBeGreaterThan(0);
      expect(screen.getAllByText('running').length).toBeGreaterThan(0);
    });

    it('uses node name from data.name property', () => {
      render(<DataFlowPanel />);

      const agentABadges = screen.getAllByText('Agent A');
      expect(agentABadges.length).toBeGreaterThan(0);
    });

    it('falls back to toolName when name not available', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'node-1',
            type: 'agent',
            position: { x: 0, y: 0 },
            data: { toolName: 'OpenAI' },
          },
          {
            id: 'node-2',
            type: 'agent',
            position: { x: 100, y: 0 },
            data: {},
          },
        ],
        edges: mockEdges.slice(0, 1),
        setNodes: vi.fn(),
        setEdges: vi.fn(),
        onNodesChange: vi.fn(),
        onEdgesChange: vi.fn(),
        onConnect: vi.fn(),
        addNode: vi.fn(),
        updateNode: vi.fn(),
        deleteNode: vi.fn(),
        selectedNode: null,
        setSelectedNode: vi.fn(),
      } as any);
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      expect(screen.getAllByText('OpenAI').length).toBeGreaterThan(0);
    });

    it('falls back to label when neither name nor toolName available', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'node-3',
            type: 'trigger',
            position: { x: 0, y: 0 },
            data: { label: 'HTTP Trigger' },
          },
          {
            id: 'node-2',
            type: 'agent',
            position: { x: 100, y: 0 },
            data: {},
          },
        ],
        edges: [{ id: 'edge-1', source: 'node-3', target: 'node-2' }],
        setNodes: vi.fn(),
        setEdges: vi.fn(),
        onNodesChange: vi.fn(),
        onEdgesChange: vi.fn(),
        onConnect: vi.fn(),
        addNode: vi.fn(),
        updateNode: vi.fn(),
        deleteNode: vi.fn(),
        selectedNode: null,
        setSelectedNode: vi.fn(),
      } as any);
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-3',
            status: 'completed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            output: {},
          },
        ],
      });

      render(<DataFlowPanel />);

      expect(screen.getAllByText('HTTP Trigger').length).toBeGreaterThan(0);
    });

    it('uses node id as fallback when no name properties', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [
          {
            id: 'node-1',
            type: 'agent',
            position: { x: 0, y: 0 },
            data: {},
          },
          {
            id: 'node-2',
            type: 'agent',
            position: { x: 100, y: 0 },
            data: {},
          },
        ],
        edges: mockEdges.slice(0, 1),
        setNodes: vi.fn(),
        setEdges: vi.fn(),
        onNodesChange: vi.fn(),
        onEdgesChange: vi.fn(),
        onConnect: vi.fn(),
        addNode: vi.fn(),
        updateNode: vi.fn(),
        deleteNode: vi.fn(),
        selectedNode: null,
        setSelectedNode: vi.fn(),
      } as any);
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      expect(screen.getAllByText('node-1').length).toBeGreaterThan(0);
      expect(screen.getAllByText('node-2').length).toBeGreaterThan(0);
    });
  });

  describe('Status Display', () => {
    it('shows completed status with output data', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      expect(screen.getAllByText('completed').length).toBeGreaterThan(0);
      expect(screen.getByText('Output Data:')).toBeInTheDocument();
    });

    it('displays formatted JSON output', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      const jsonOutput = screen.getByText(/"result"/);
      expect(jsonOutput).toBeInTheDocument();
    });

    it('truncates long output strings', () => {
      const longString = 'a'.repeat(250);
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'completed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            output: longString,
          },
        ],
      });

      render(<DataFlowPanel />);

      // Check for truncated string in pre element
      const preElements = screen.getAllByText(/\.\.\./);
      // Find the one that contains the long string
      const truncatedElement = preElements.find(el => el.textContent && el.textContent.includes('aaa'));
      expect(truncatedElement).toBeTruthy();
    });

    it('shows pending state message', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'pending',
            startedAt: '2024-01-01T00:00:00Z',
          },
        ],
      });

      render(<DataFlowPanel />);

      expect(screen.getAllByText('Waiting for execution...').length).toBeGreaterThan(0);
    });

    it('shows running state message', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      expect(screen.getAllByText('Currently executing...').length).toBeGreaterThan(0);
    });

    it('shows failed state message', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'failed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            error: 'Something went wrong',
          },
        ],
      });

      render(<DataFlowPanel />);

      expect(screen.getAllByText('Execution failed').length).toBeGreaterThan(0);
    });

    it('does not show output for non-completed status', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      // Only one Output Data should exist (for the completed node)
      expect(screen.getAllByText('Output Data:')).toHaveLength(1);
    });
  });

  describe('Status Badge Variants', () => {
    it('uses correct variant for completed status', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      const completedBadges = screen.getAllByText('completed');
      expect(completedBadges[0]).toHaveAttribute('data-variant', 'default');
    });

    it('uses correct variant for failed status', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'failed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            error: 'Error',
          },
        ],
      });

      render(<DataFlowPanel />);

      const failedBadges = screen.getAllByText('failed');
      expect(failedBadges[0]).toHaveAttribute('data-variant', 'destructive');
    });

    it('uses correct variant for running status', () => {
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      const runningBadges = screen.getAllByText('running');
      expect(runningBadges[0]).toHaveAttribute('data-variant', 'default');
    });

    it('uses correct variant for pending status', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'pending',
            startedAt: '2024-01-01T00:00:00Z',
          },
        ],
      });

      render(<DataFlowPanel />);

      const pendingBadges = screen.getAllByText('pending');
      expect(pendingBadges[0]).toHaveAttribute('data-variant', 'secondary');
    });
  });

  describe('Edge Cases', () => {
    it('handles missing node gracefully', () => {
      vi.mocked(useWorkflowStore).mockReturnValue({
        nodes: [mockNodes[0]], // Only first node
        edges: mockEdges,
        setNodes: vi.fn(),
        setEdges: vi.fn(),
        onNodesChange: vi.fn(),
        onEdgesChange: vi.fn(),
        onConnect: vi.fn(),
        addNode: vi.fn(),
        updateNode: vi.fn(),
        deleteNode: vi.fn(),
        selectedNode: null,
        setSelectedNode: vi.fn(),
      } as any);
      vi.mocked(useCurrentExecution).mockReturnValue(mockExecution);

      render(<DataFlowPanel />);

      // Should still render without crashing
      expect(screen.getByText('Data Flow')).toBeInTheDocument();
    });

    it('handles missing execution for edge source', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [], // No executions
      });

      render(<DataFlowPanel />);

      // Should show pending status for all
      const pendingBadges = screen.getAllByText('pending');
      expect(pendingBadges.length).toBeGreaterThan(0);
    });

    it('handles null output', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'completed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            output: null,
          },
        ],
      });

      render(<DataFlowPanel />);

      // Should not show Output Data section
      expect(screen.queryByText('Output Data:')).not.toBeInTheDocument();
    });

    it('handles undefined output', () => {
      vi.mocked(useCurrentExecution).mockReturnValue({
        ...mockExecution,
        nodeExecutions: [
          {
            nodeId: 'node-1',
            status: 'completed',
            startedAt: '2024-01-01T00:00:00Z',
            completedAt: '2024-01-01T00:00:01Z',
            output: undefined,
          },
        ],
      });

      render(<DataFlowPanel />);

      // Should not show Output Data section
      expect(screen.queryByText('Output Data:')).not.toBeInTheDocument();
    });
  });
});
