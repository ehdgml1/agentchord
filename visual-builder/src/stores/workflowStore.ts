/**
 * Zustand store for Visual Builder workflow state
 *
 * Manages the complete workflow state including nodes, edges, selection,
 * and workflow metadata with persistence.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  type Connection,
  type NodeChange,
  type EdgeChange,
} from '@xyflow/react';
import { nanoid } from 'nanoid';
import type { WorkflowNode, WorkflowEdge, Workflow } from '../types/workflow';
import { BlockType, type BlockData } from '../types/blocks';
import { getBlockDefinition } from '../constants/blocks';
import { api } from '../services/api';
import { createUndoStore } from './undoMiddleware';

/**
 * Workflow store state and actions interface
 */
interface WorkflowState {
  // Workflow metadata
  workflowId: string;
  workflowName: string;

  // React Flow state
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];

  // Selection
  selectedNodeId: string | null;

  // Backend sync state
  backendId: string | null;
  isSaving: boolean;
  isDirty: boolean;

  // React Flow callbacks
  onNodesChange: (changes: NodeChange<WorkflowNode>[]) => void;
  onEdgesChange: (changes: EdgeChange<WorkflowEdge>[]) => void;
  onConnect: (connection: Connection) => void;

  // Node operations
  addNode: (type: BlockType, position: { x: number; y: number }) => string;
  updateNodeData: (nodeId: string, data: Partial<BlockData>) => void;
  removeNode: (nodeId: string) => void;

  // Selection
  selectNode: (nodeId: string | null) => void;

  // Workflow management
  setWorkflowName: (name: string) => void;
  clearWorkflow: () => void;
  loadWorkflow: (workflow: Workflow) => void;
  getWorkflow: () => Workflow;

  // Backend sync actions
  saveWorkflow: () => Promise<void>;
  fetchWorkflows: () => Promise<Workflow[]>;
  loadFromBackend: (id: string) => Promise<void>;
  setDirty: (dirty: boolean) => void;

  // Undo/Redo
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
}

/**
 * Create initial empty workflow state
 */
const createInitialState = () => ({
  workflowId: nanoid(),
  workflowName: 'Untitled Workflow',
  nodes: [],
  edges: [],
  selectedNodeId: null,
  backendId: null,
  isSaving: false,
  isDirty: false,
});

/**
 * Undo/redo store instance
 */
const undoStore = createUndoStore();
const UNDO_KEYS = ['nodes', 'edges'];

/**
 * Main workflow store with persistence
 */
export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, get) => ({
      ...createInitialState(),

      onNodesChange: (changes) => {
        // Only save snapshot for non-position changes (avoid undo history pollution from dragging)
        const hasNonPositionChange = changes.some(
          (change) => change.type !== 'position'
        );

        if (hasNonPositionChange) {
          undoStore.saveSnapshot(get(), UNDO_KEYS);
        }

        set({
          nodes: applyNodeChanges(changes, get().nodes) as WorkflowNode[],
          isDirty: true,
        });
      },

      onEdgesChange: (changes) => {
        // Save snapshot before edge changes
        undoStore.saveSnapshot(get(), UNDO_KEYS);
        set({
          edges: applyEdgeChanges(changes, get().edges) as WorkflowEdge[],
          isDirty: true,
        });
      },

      onConnect: (connection) => {
        // Save snapshot before connecting
        undoStore.saveSnapshot(get(), UNDO_KEYS);
        const nodes = get().nodes;
        const sourceNode = nodes.find(n => n.id === connection.source);

        let edgeData: Record<string, unknown> = {};
        let edgeType: string | undefined;

        if (sourceNode?.type === BlockType.CONDITION) {
          const handle = connection.sourceHandle;
          if (handle === 'true') {
            edgeData = { label: sourceNode.data.trueLabel || 'Yes', edgeColor: '#22c55e' };
            edgeType = 'labeled';
          } else if (handle === 'false') {
            edgeData = { label: sourceNode.data.falseLabel || 'No', edgeColor: '#ef4444' };
            edgeType = 'labeled';
          }
        }

        set({
          edges: addEdge(
            { ...connection, id: nanoid(), data: edgeData, type: edgeType },
            get().edges
          ) as WorkflowEdge[],
          isDirty: true,
        });
      },

      addNode: (type, position) => {
        // Save snapshot before adding node
        undoStore.saveSnapshot(get(), UNDO_KEYS);
        const definition = getBlockDefinition(type);
        if (!definition) return '';

        const id = nanoid();
        const typeCount = get().nodes.filter((n) => n.type === type).length;

        const newNode: WorkflowNode = {
          id,
          type,
          position,
          data: {
            ...definition.defaultData,
            label: `${definition.label} ${typeCount + 1}`,
          },
        };

        set({ nodes: [...get().nodes, newNode], isDirty: true });
        return id;
      },

      updateNodeData: (nodeId, data) => {
        // Save snapshot before updating node data
        undoStore.saveSnapshot(get(), UNDO_KEYS);
        set({
          nodes: get().nodes.map((node) =>
            node.id === nodeId
              ? { ...node, data: { ...node.data, ...data } }
              : node
          ),
          isDirty: true,
        });
      },

      removeNode: (nodeId) => {
        // Save snapshot before removing node
        undoStore.saveSnapshot(get(), UNDO_KEYS);
        const currentSelectedId = get().selectedNodeId;

        set({
          nodes: get().nodes.filter((node) => node.id !== nodeId),
          edges: get().edges.filter(
            (edge) => edge.source !== nodeId && edge.target !== nodeId
          ),
          selectedNodeId: currentSelectedId === nodeId ? null : currentSelectedId,
          isDirty: true,
        });
      },

      selectNode: (nodeId) => {
        set({ selectedNodeId: nodeId });
      },

      setWorkflowName: (name) => {
        set({ workflowName: name, isDirty: true });
      },

      clearWorkflow: () => {
        undoStore.clear();
        set(createInitialState());
      },

      loadWorkflow: (workflow) => {
        set({
          workflowId: workflow.id,
          workflowName: workflow.name,
          nodes: workflow.nodes,
          edges: workflow.edges,
          selectedNodeId: null,
        });
      },

      getWorkflow: () => {
        const state = get();
        const now = new Date().toISOString();

        return {
          id: state.backendId || state.workflowId,
          name: state.workflowName,
          nodes: state.nodes,
          edges: state.edges,
          createdAt: now,
          updatedAt: now,
        };
      },

      saveWorkflow: async () => {
        const state = get();
        set({ isSaving: true });

        try {
          const workflow = state.getWorkflow();

          if (state.backendId) {
            // Update existing workflow
            await api.workflows.update(state.backendId, {
              name: workflow.name,
              nodes: workflow.nodes,
              edges: workflow.edges,
            });
          } else {
            // Create new workflow
            const created = await api.workflows.create({
              name: workflow.name,
              nodes: workflow.nodes,
              edges: workflow.edges,
            });
            set({ backendId: created.id });
          }

          set({ isDirty: false });
        } catch (error) {
          if (import.meta.env.DEV) console.error('Failed to save workflow:', error);
          throw error;
        } finally {
          set({ isSaving: false });
        }
      },

      fetchWorkflows: async () => {
        return await api.workflows.list();
      },

      loadFromBackend: async (id: string) => {
        try {
          const workflow = await api.workflows.get(id);
          get().loadWorkflow(workflow);
          set({ backendId: id, isDirty: false });
        } catch (error) {
          if (import.meta.env.DEV) console.error('Failed to load workflow:', error);
          throw error;
        }
      },

      setDirty: (dirty: boolean) => {
        set({ isDirty: dirty });
      },

      // Undo/Redo actions
      undo: () => {
        undoStore.undo(get, set, UNDO_KEYS);
      },

      redo: () => {
        undoStore.redo(get, set, UNDO_KEYS);
      },

      canUndo: () => {
        return undoStore.canUndo();
      },

      canRedo: () => {
        return undoStore.canRedo();
      },
    }),
    {
      name: 'agentchord-workflow',
      partialize: (state) => ({
        workflowId: state.workflowId,
        workflowName: state.workflowName,
        nodes: state.nodes,
        edges: state.edges,
        backendId: state.backendId,
      }),
    }
  )
);

/**
 * Selector hook for nodes array
 */
export const useNodes = () => useWorkflowStore((state) => state.nodes);

/**
 * Selector hook for edges array
 */
export const useEdges = () => useWorkflowStore((state) => state.edges);

/**
 * Selector hook for currently selected node
 */
export const useSelectedNode = () =>
  useWorkflowStore(
    (state) =>
      state.selectedNodeId
        ? state.nodes.find((n) => n.id === state.selectedNodeId)
        : undefined,
    (a, b) => {
      if (a === b) return true;
      if (!a || !b) return false;
      if (a.id !== b.id) return false;
      const aData = a.data as Record<string, unknown> | undefined;
      const bData = b.data as Record<string, unknown> | undefined;
      if (aData === bData) return true;
      if (!aData || !bData) return false;
      const aKeys = Object.keys(aData);
      const bKeys = Object.keys(bData);
      if (aKeys.length !== bKeys.length) return false;
      return aKeys.every(key => aData[key] === bData[key]);
    }
  );
