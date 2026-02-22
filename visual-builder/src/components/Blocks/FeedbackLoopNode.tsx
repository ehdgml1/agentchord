import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { RefreshCw } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { FeedbackLoopBlockData } from '../../types/blocks';

type FeedbackLoopNodeProps = NodeProps & {
  data: FeedbackLoopBlockData & { label?: string };
};

export const FeedbackLoopNode = memo(function FeedbackLoopNode({ id, data, selected }: FeedbackLoopNodeProps) {
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#EC4899" selected={selected} executionStatus={executionStatus}>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-pink-100">
            <RefreshCw className="w-4 h-4 text-pink-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm">Feedback Loop</div>
            <div className="text-xs text-muted-foreground">
              Max: {data.maxIterations} iterations
            </div>
          </div>
        </div>
        {data.stopCondition && (
          <div className="text-xs text-muted-foreground font-mono bg-muted p-1 rounded truncate">
            {data.stopCondition}
          </div>
        )}
      </div>
    </BaseNode>
  );
});
