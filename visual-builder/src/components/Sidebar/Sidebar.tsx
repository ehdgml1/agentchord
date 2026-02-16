import { memo, useCallback } from 'react';
import { BLOCK_DEFINITIONS } from '../../constants/blocks';
import { BlockItem } from './BlockItem';
import { MCPHub } from './MCPHub';
import { cn } from '../../lib/utils';

interface SidebarProps {
  className?: string;
}

export const Sidebar = memo(function Sidebar({ className }: SidebarProps) {
  const onDragStart = useCallback((event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <aside className={cn('w-64 border-r bg-background p-4 overflow-y-auto', className)}>
      <div className="mb-4">
        <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
          Blocks
        </h2>
      </div>

      <div className="space-y-2">
        {BLOCK_DEFINITIONS.map((definition) => (
          <BlockItem
            key={definition.type}
            definition={definition}
            onDragStart={onDragStart}
          />
        ))}
      </div>

      <MCPHub />

      <div className="mt-6 pt-4 border-t">
        <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider mb-3">
          Tips
        </h3>
        <ul className="text-xs text-muted-foreground space-y-2">
          <li>Drag blocks to the canvas</li>
          <li>Connect blocks by dragging handles</li>
          <li>Click a block to edit properties</li>
        </ul>
      </div>
    </aside>
  );
});
