import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useWorkflowStore } from './workflowStore';
import { BlockType } from '../types/blocks';

// Mock nanoid to return predictable IDs
vi.mock('nanoid', () => ({
  nanoid: (() => {
    let counter = 0;
    return () => `test-id-${counter++}`;
  })(),
}));

// Mock getBlockDefinition
vi.mock('../constants/blocks', () => ({
  getBlockDefinition: (type: BlockType) => {
    const definitions = {
      trigger: { label: 'Trigger', defaultData: { type: 'trigger' } },
      http: { label: 'HTTP', defaultData: { type: 'http' } },
      transform: { label: 'Transform', defaultData: { type: 'transform' } },
    };
    return definitions[type as keyof typeof definitions];
  },
}));

describe('workflowStore', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();

    // Reset store to initial state
    useWorkflowStore.setState({
      workflowId: 'test-workflow',
      workflowName: 'Test Workflow',
      nodes: [],
      edges: [],
      selectedNodeId: null,
    });
  });

  describe('addNode', () => {
    it('adds a new node with correct data', () => {
      const { addNode } = useWorkflowStore.getState();
      const nodeId = addNode('http', { x: 100, y: 200 });

      const state = useWorkflowStore.getState();
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0]).toMatchObject({
        id: nodeId,
        type: 'http',
        position: { x: 100, y: 200 },
      });
      expect(state.nodes[0].data.label).toBe('HTTP 1');
    });

    it('increments node label counter for same type', () => {
      const { addNode } = useWorkflowStore.getState();

      addNode('http', { x: 0, y: 0 });
      addNode('http', { x: 100, y: 100 });

      const state = useWorkflowStore.getState();
      expect(state.nodes[0].data.label).toBe('HTTP 1');
      expect(state.nodes[1].data.label).toBe('HTTP 2');
    });

    it('returns empty string for unknown block type', () => {
      const { addNode } = useWorkflowStore.getState();
      const nodeId = addNode('unknown' as BlockType, { x: 0, y: 0 });

      expect(nodeId).toBe('');
      expect(useWorkflowStore.getState().nodes).toHaveLength(0);
    });
  });

  describe('updateNodeData', () => {
    it('updates node data correctly', () => {
      const { addNode, updateNodeData } = useWorkflowStore.getState();
      const nodeId = addNode('http', { x: 0, y: 0 });

      updateNodeData(nodeId, { label: 'Updated Label' });

      const state = useWorkflowStore.getState();
      expect(state.nodes[0].data.label).toBe('Updated Label');
    });

    it('does not affect other nodes', () => {
      const { addNode, updateNodeData } = useWorkflowStore.getState();
      const node1 = addNode('http', { x: 0, y: 0 });
      const node2 = addNode('transform', { x: 100, y: 100 });

      updateNodeData(node1, { label: 'Node 1' });

      const state = useWorkflowStore.getState();
      expect(state.nodes[0].data.label).toBe('Node 1');
      expect(state.nodes[1].data.label).toBe('Transform 1');
    });
  });

  describe('removeNode', () => {
    it('removes node and associated edges', () => {
      const { addNode, removeNode, onConnect } = useWorkflowStore.getState();
      const node1 = addNode('http', { x: 0, y: 0 });
      const node2 = addNode('transform', { x: 100, y: 100 });

      // Add edge between nodes
      onConnect({ source: node1, target: node2 });

      removeNode(node1);

      const state = useWorkflowStore.getState();
      expect(state.nodes).toHaveLength(1);
      expect(state.edges).toHaveLength(0);
    });

    it('clears selection when removing selected node', () => {
      const { addNode, removeNode, selectNode } = useWorkflowStore.getState();
      const nodeId = addNode('http', { x: 0, y: 0 });

      selectNode(nodeId);
      expect(useWorkflowStore.getState().selectedNodeId).toBe(nodeId);

      removeNode(nodeId);
      expect(useWorkflowStore.getState().selectedNodeId).toBeNull();
    });

    it('preserves selection when removing different node', () => {
      const { addNode, removeNode, selectNode } = useWorkflowStore.getState();
      const node1 = addNode('http', { x: 0, y: 0 });
      const node2 = addNode('transform', { x: 100, y: 100 });

      selectNode(node1);
      removeNode(node2);

      expect(useWorkflowStore.getState().selectedNodeId).toBe(node1);
    });
  });

  describe('selectNode', () => {
    it('sets selected node ID', () => {
      const { addNode, selectNode } = useWorkflowStore.getState();
      const nodeId = addNode('http', { x: 0, y: 0 });

      selectNode(nodeId);
      expect(useWorkflowStore.getState().selectedNodeId).toBe(nodeId);
    });

    it('can clear selection with null', () => {
      const { addNode, selectNode } = useWorkflowStore.getState();
      const nodeId = addNode('http', { x: 0, y: 0 });

      selectNode(nodeId);
      selectNode(null);
      expect(useWorkflowStore.getState().selectedNodeId).toBeNull();
    });
  });

  describe('setWorkflowName', () => {
    it('updates workflow name', () => {
      const { setWorkflowName } = useWorkflowStore.getState();

      setWorkflowName('My Custom Workflow');
      expect(useWorkflowStore.getState().workflowName).toBe('My Custom Workflow');
    });
  });

  describe('clearWorkflow', () => {
    it('resets to initial state', () => {
      const { addNode, selectNode, setWorkflowName, clearWorkflow } = useWorkflowStore.getState();

      // Modify state
      addNode('http', { x: 0, y: 0 });
      setWorkflowName('Custom Name');
      selectNode('some-id');

      clearWorkflow();

      const state = useWorkflowStore.getState();
      expect(state.nodes).toHaveLength(0);
      expect(state.edges).toHaveLength(0);
      expect(state.selectedNodeId).toBeNull();
      expect(state.workflowName).toBe('Untitled Workflow');
    });
  });

  describe('getWorkflow', () => {
    it('returns workflow with current state', () => {
      const { addNode, setWorkflowName, getWorkflow } = useWorkflowStore.getState();

      setWorkflowName('Test Workflow');
      addNode('http', { x: 0, y: 0 });

      const workflow = getWorkflow();

      expect(workflow.name).toBe('Test Workflow');
      expect(workflow.nodes).toHaveLength(1);
      expect(workflow.edges).toHaveLength(0);
      expect(workflow.createdAt).toBeDefined();
      expect(workflow.updatedAt).toBeDefined();
    });
  });
});
