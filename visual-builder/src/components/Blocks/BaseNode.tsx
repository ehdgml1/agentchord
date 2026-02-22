import { memo, type ReactNode } from 'react';
import { Handle, Position } from '@xyflow/react';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export type NodeExecutionStatus = 'idle' | 'running' | 'completed' | 'failed';

interface BaseNodeProps {
  children: ReactNode;
  color: string;
  selected?: boolean;
  hasInput?: boolean;
  hasOutput?: boolean;
  executionStatus?: NodeExecutionStatus;
}

export const BaseNode = memo(function BaseNode({
  children,
  color,
  selected = false,
  hasInput = true,
  hasOutput = true,
  executionStatus,
}: BaseNodeProps) {
  const borderColor = executionStatus === 'running'
    ? '#3B82F6'
    : executionStatus === 'completed'
    ? '#22C55E'
    : executionStatus === 'failed'
    ? '#EF4444'
    : color;

  return (
    <div
      role="group"
      aria-selected={selected}
      className={cn(
        'relative min-w-[180px] rounded-lg border-2 bg-card shadow-md transition-all duration-300',
        selected && 'ring-2 ring-primary ring-offset-2',
        executionStatus === 'running' && 'animate-pulse shadow-blue-200 shadow-lg',
        executionStatus === 'completed' && 'shadow-green-200 shadow-lg',
        executionStatus === 'failed' && 'shadow-red-200 shadow-lg',
      )}
      style={{ borderColor }}
    >
      {hasInput && (
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-gray-400 !border-white"
        />
      )}
      {children}
      {executionStatus && executionStatus !== 'idle' && (
        <div className={cn(
          'absolute -top-2 -right-2 rounded-full p-0.5',
          executionStatus === 'running' && 'bg-blue-500',
          executionStatus === 'completed' && 'bg-green-500',
          executionStatus === 'failed' && 'bg-red-500',
        )}>
          {executionStatus === 'running' && (
            <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
          )}
          {executionStatus === 'completed' && (
            <CheckCircle2 className="w-3.5 h-3.5 text-white" />
          )}
          {executionStatus === 'failed' && (
            <XCircle className="w-3.5 h-3.5 text-white" />
          )}
        </div>
      )}
      {hasOutput && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-gray-400 !border-white"
        />
      )}
    </div>
  );
});
