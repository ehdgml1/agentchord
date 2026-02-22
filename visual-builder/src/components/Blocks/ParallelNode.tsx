import { memo } from 'react';
import { type NodeProps, Handle, Position } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { ParallelBlockData } from '../../types/blocks';

type ParallelNodeProps = NodeProps & {
  data: ParallelBlockData & { label?: string };
};

export const ParallelNode = memo(function ParallelNode({ id, data, selected }: ParallelNodeProps) {
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#10B981" selected={selected} hasOutput={false} executionStatus={executionStatus}>
      <div className="p-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-emerald-100">
            <GitBranch className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-sm">Parallel</div>
            <div className="text-xs text-muted-foreground">
              Merge: {data.mergeStrategy}
            </div>
          </div>
        </div>
      </div>
      {/* Multiple output handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="out-1"
        style={{ top: '30%' }}
        className="!bg-emerald-500 !border-white"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="out-2"
        style={{ top: '70%' }}
        className="!bg-emerald-500 !border-white"
      />
    </BaseNode>
  );
});
