import { memo, useCallback, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useShallow } from 'zustand/react/shallow';
import { useWorkflowStore } from '../../stores/workflowStore';
import { nodeTypes } from '../Blocks';
import { BlockType } from '../../types/blocks';
import type { WorkflowNode, WorkflowEdge } from '../../types/workflow';
import { LabeledEdge } from './LabeledEdge';
import { useUndoRedo } from '../../hooks/useUndoRedo';

const getNodeColor = (node: { type?: string }) => {
  switch (node.type) {
    case BlockType.TRIGGER: return '#EF4444';
    case BlockType.AGENT: return '#3B82F6';
    case BlockType.MCP_TOOL: return '#8B5CF6';
    case BlockType.PARALLEL: return '#10B981';
    case BlockType.CONDITION: return '#F59E0B';
    case BlockType.FEEDBACK_LOOP: return '#EC4899';
    default: return '#6B7280';
  }
};

export const Canvas = memo(function Canvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<ReactFlowInstance<WorkflowNode, WorkflowEdge> | null>(null);

  // Enable undo/redo keyboard shortcuts
  useUndoRedo();

  // Selective subscriptions to prevent unnecessary re-renders
  const nodes = useWorkflowStore(s => s.nodes);
  const edges = useWorkflowStore(s => s.edges);
  const { onNodesChange, onEdgesChange, onConnect, addNode, selectNode } = useWorkflowStore(
    useShallow(s => ({
      onNodesChange: s.onNodesChange,
      onEdgesChange: s.onEdgesChange,
      onConnect: s.onConnect,
      addNode: s.addNode,
      selectNode: s.selectNode,
    }))
  );

  const edgeTypes = useMemo(() => ({ labeled: LabeledEdge }), []);

  const onInit = useCallback((instance: ReactFlowInstance<WorkflowNode, WorkflowEdge>) => {
    reactFlowInstance.current = instance;
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !reactFlowInstance.current) return;

      const position = reactFlowInstance.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      addNode(type as BlockType, position);
    },
    [addNode]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full" aria-label="Workflow canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={onInit}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: true,
        }}
      >
        <Background gap={15} />
        <Controls />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  );
});
