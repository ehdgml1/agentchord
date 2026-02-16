/**
 * Main properties panel component
 *
 * Displays configuration UI for the currently selected node,
 * routing to the appropriate properties editor based on node type.
 */

import { memo, useCallback } from 'react';
import { X } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { Button } from '../ui/button';
import { AgentProperties } from './AgentProperties';
import { MCPToolProperties } from './MCPToolProperties';
import { ConditionProperties } from './ConditionProperties';
import { ParallelProperties } from './ParallelProperties';
import { FeedbackLoopProperties } from './FeedbackLoopProperties';
import { RAGProperties } from './RAGProperties';
import { MultiAgentProperties } from './MultiAgentProperties';
import { useWorkflowStore, useSelectedNode } from '../../stores/workflowStore';
import {
  BlockType,
  type AgentBlockData,
  type MCPToolBlockData,
  type ConditionBlockData,
  type ParallelBlockData,
  type FeedbackLoopBlockData,
  type TriggerBlockData,
  type RAGBlockData,
  type MultiAgentBlockData,
} from '../../types/blocks';
import { getBlockDefinition } from '../../constants/blocks';

export const PropertiesPanel = memo(function PropertiesPanel() {
  const selectedNode = useSelectedNode();
  const { updateNodeData, selectNode, removeNode } = useWorkflowStore(
    useShallow(s => ({
      updateNodeData: s.updateNodeData,
      selectNode: s.selectNode,
      removeNode: s.removeNode,
    }))
  );

  const handleClose = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const handleDelete = useCallback(() => {
    if (selectedNode) {
      removeNode(selectedNode.id);
    }
  }, [selectedNode, removeNode]);

  const handleDataChange = useCallback(
    (data: Record<string, unknown>) => {
      if (selectedNode) {
        updateNodeData(selectedNode.id, data);
      }
    },
    [selectedNode, updateNodeData]
  );

  if (!selectedNode) {
    return (
      <aside className="w-72 border-l bg-background p-4">
        <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
          Select a block to edit
        </div>
      </aside>
    );
  }

  const definition = getBlockDefinition(selectedNode.type as BlockType);

  return (
    <aside className="w-72 border-l bg-background p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold">{definition?.label || 'Properties'}</h2>
        <Button variant="ghost" size="icon" onClick={handleClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {selectedNode.type === BlockType.TRIGGER && (
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            <p className="font-medium mb-2">Trigger Configuration</p>
            <p>Trigger type: {(selectedNode.data as TriggerBlockData).triggerType || 'Not configured'}</p>
            {(selectedNode.data as TriggerBlockData).triggerType === 'cron' && (
              <p className="mt-1">Cron: {(selectedNode.data as TriggerBlockData).cronExpression || 'Not set'}</p>
            )}
            {(selectedNode.data as TriggerBlockData).triggerType === 'webhook' && (
              <p className="mt-1">Path: {(selectedNode.data as TriggerBlockData).webhookPath || 'Not set'}</p>
            )}
            <p className="mt-3 text-xs">Full trigger properties panel coming soon.</p>
          </div>
        </div>
      )}

      {selectedNode.type === BlockType.AGENT && (
        <AgentProperties
          data={selectedNode.data as AgentBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.MCP_TOOL && (
        <MCPToolProperties
          data={selectedNode.data as MCPToolBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.CONDITION && (
        <ConditionProperties
          data={selectedNode.data as ConditionBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.PARALLEL && (
        <ParallelProperties
          data={selectedNode.data as ParallelBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.FEEDBACK_LOOP && (
        <FeedbackLoopProperties
          data={selectedNode.data as FeedbackLoopBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.RAG && (
        <RAGProperties
          data={selectedNode.data as RAGBlockData}
          onChange={handleDataChange}
        />
      )}

      {selectedNode.type === BlockType.MULTI_AGENT && (
        <MultiAgentProperties
          data={selectedNode.data as MultiAgentBlockData}
          onChange={handleDataChange}
        />
      )}

      {(selectedNode.type === BlockType.START || selectedNode.type === BlockType.END) && (
        <div className="text-sm text-muted-foreground">
          <p>{selectedNode.type === BlockType.START ? 'Start' : 'End'} node - the {selectedNode.type === BlockType.START ? 'entry point' : 'exit point'} of your workflow.</p>
          <p className="mt-2 text-xs">This node cannot be configured or deleted.</p>
        </div>
      )}

      {selectedNode.type !== BlockType.START && selectedNode.type !== BlockType.END && (
        <div className="mt-6 pt-4 border-t">
          <Button
            variant="destructive"
            size="sm"
            className="w-full"
            onClick={handleDelete}
          >
            Delete Block
          </Button>
        </div>
      )}
    </aside>
  );
});
