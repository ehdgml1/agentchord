import { memo } from 'react';
import { Bot, Wrench, GitBranch, GitFork, RefreshCw, Zap, BookOpen, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { BlockDefinition } from '../../types/blocks';

const ICON_MAP: Record<string, LucideIcon> = {
  Bot,
  Wrench,
  GitBranch,
  GitFork,
  RefreshCw,
  Zap,
  BookOpen,
  Users,
};

interface BlockItemProps {
  definition: BlockDefinition;
  onDragStart: (event: React.DragEvent, type: string) => void;
}

export const BlockItem = memo(function BlockItem({ definition, onDragStart }: BlockItemProps) {
  const IconComponent = ICON_MAP[definition.icon];

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border cursor-grab',
        'hover:bg-accent hover:border-accent transition-colors',
        'active:cursor-grabbing'
      )}
      draggable
      onDragStart={(e) => onDragStart(e, definition.type)}
    >
      <div
        className="p-2 rounded-md"
        style={{ backgroundColor: `${definition.color}20`, color: definition.color }}
      >
        {IconComponent && (
          <IconComponent className="w-4 h-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{definition.label}</div>
        <div className="text-xs text-muted-foreground truncate">
          {definition.description}
        </div>
      </div>
    </div>
  );
});
