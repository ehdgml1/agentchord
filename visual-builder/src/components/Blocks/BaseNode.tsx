import { memo, type ReactNode } from 'react';
import { Handle, Position } from '@xyflow/react';
import { cn } from '../../lib/utils';

interface BaseNodeProps {
  children: ReactNode;
  color: string;
  selected?: boolean;
  hasInput?: boolean;
  hasOutput?: boolean;
}

export const BaseNode = memo(function BaseNode({
  children,
  color,
  selected = false,
  hasInput = true,
  hasOutput = true,
}: BaseNodeProps) {
  return (
    <div
      role="group"
      aria-selected={selected}
      className={cn(
        'min-w-[180px] rounded-lg border-2 bg-card shadow-md transition-shadow',
        selected && 'ring-2 ring-primary ring-offset-2'
      )}
      style={{ borderColor: color }}
    >
      {hasInput && (
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-gray-400 !border-white"
        />
      )}
      {children}
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
