import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { Bot, Wrench } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { AgentBlockData } from '../../types/blocks';
import { MODELS } from '../../constants/models';

type AgentNodeProps = NodeProps & {
  data: AgentBlockData & { label?: string };
};

export const AgentNode = memo(function AgentNode({ id, data, selected }: AgentNodeProps) {
  const modelInfo = MODELS[data.model];
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#3B82F6" selected={selected} executionStatus={executionStatus}>
      <div className="p-3" aria-label={`Agent node: ${data.name || 'Unnamed Agent'}`}>
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-blue-100">
            <Bot className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm truncate">
              {data.name || 'Unnamed Agent'}
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {modelInfo?.name || data.model}
            </div>
          </div>
        </div>
        {data.role && (
          <div className="text-xs text-muted-foreground line-clamp-2">
            {data.role}
          </div>
        )}
        {data.mcpTools && data.mcpTools.length > 0 && (
          <div className="flex items-center gap-1 text-xs text-blue-600">
            <Wrench className="w-3 h-3" />
            <span>{data.mcpTools.length} tool{data.mcpTools.length > 1 ? 's' : ''}</span>
          </div>
        )}
      </div>
    </BaseNode>
  );
});
