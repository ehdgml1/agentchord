import { memo } from 'react';
import { type NodeProps, Handle, Position } from '@xyflow/react';
import { GitFork } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { ConditionBlockData } from '../../types/blocks';

type ConditionNodeProps = NodeProps & {
  data: ConditionBlockData & { label?: string };
};

export const ConditionNode = memo(function ConditionNode({ id, data, selected }: ConditionNodeProps) {
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#F59E0B" selected={selected} hasOutput={false} executionStatus={executionStatus}>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-amber-100">
            <GitFork className="w-4 h-4 text-amber-600" />
          </div>
          <div className="font-medium text-sm">Condition</div>
        </div>
        {data.condition && (
          <div className="text-xs text-muted-foreground font-mono bg-muted p-1 rounded truncate">
            {data.condition}
          </div>
        )}
      </div>
      {/* True/False handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="true"
        style={{ top: '30%' }}
        className="!bg-green-500 !border-white"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="false"
        style={{ top: '70%' }}
        className="!bg-red-500 !border-white"
      />
      <div className="absolute right-[-40px] top-[20%] text-xs text-green-600">
        {data.trueLabel || 'Yes'}
      </div>
      <div className="absolute right-[-35px] top-[60%] text-xs text-red-600">
        {data.falseLabel || 'No'}
      </div>
    </BaseNode>
  );
});
