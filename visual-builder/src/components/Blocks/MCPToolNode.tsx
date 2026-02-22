import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { Wrench } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { MCPToolBlockData } from '../../types/blocks';

type MCPToolNodeProps = NodeProps & {
  data: MCPToolBlockData & { label?: string };
};

export const MCPToolNode = memo(function MCPToolNode({ id, data, selected }: MCPToolNodeProps) {
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#8B5CF6" selected={selected} executionStatus={executionStatus}>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-violet-100">
            <Wrench className="w-4 h-4 text-violet-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm truncate">
              {data.toolName || 'MCP Tool'}
            </div>
            <div className="text-xs text-muted-foreground truncate">
              {data.serverName || 'Unknown Server'}
            </div>
          </div>
        </div>
        {data.description && (
          <div className="text-xs text-muted-foreground line-clamp-2">
            {data.description}
          </div>
        )}
      </div>
    </BaseNode>
  );
});
