import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { Users, Wrench } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { useNodeExecutionStatus } from '../../hooks/useNodeExecutionStatus';
import type { MultiAgentBlockData } from '../../types/blocks';

type MultiAgentNodeProps = NodeProps & {
  data: MultiAgentBlockData & { label?: string };
};

const STRATEGY_LABELS: Record<MultiAgentBlockData['strategy'], string> = {
  coordinator: 'Coordinator',
  round_robin: 'Round Robin',
  debate: 'Debate',
  map_reduce: 'Map-Reduce',
};

export const MultiAgentNode = memo(function MultiAgentNode({ id, data, selected }: MultiAgentNodeProps) {
  const memberCount = data.members?.length || 0;
  const strategyLabel = STRATEGY_LABELS[data.strategy] || data.strategy;
  const executionStatus = useNodeExecutionStatus(id);

  return (
    <BaseNode color="#6366F1" selected={selected} executionStatus={executionStatus}>
      <div className="p-3" aria-label={`Multi-Agent node: ${data.name || 'Unnamed Team'}`}>
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-indigo-100">
            <Users className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm truncate">
              {data.name || 'Unnamed Team'}
            </div>
            <div className="text-xs text-muted-foreground">
              {strategyLabel} &middot; {memberCount} member{memberCount !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
        {data.maxRounds > 0 && (
          <div className="text-xs text-muted-foreground line-clamp-2">
            Max {data.maxRounds} round{data.maxRounds !== 1 ? 's' : ''}
          </div>
        )}
        {(() => {
          const toolCount = (data.members || []).reduce(
            (acc: number, m: any) => acc + (m.mcpTools?.length || 0),
            0
          );
          return toolCount > 0 ? (
            <div className="flex items-center gap-1 text-xs text-blue-600">
              <Wrench className="w-3 h-3" />
              <span>{toolCount} tool{toolCount > 1 ? 's' : ''}</span>
            </div>
          ) : null;
        })()}
      </div>
    </BaseNode>
  );
});
