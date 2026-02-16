import { memo } from 'react';
import { CheckCircle2, Circle, XCircle, Clock, Loader2, AlertCircle, Ban, RotateCcw } from 'lucide-react';
import type { Execution, ExecutionStatus } from '../../types';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

interface ExecutionProgressProps {
  execution: Execution;
}

const statusConfig: Record<ExecutionStatus, { icon: typeof Circle; color: string; badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' }> = {
  pending: { icon: Circle, color: 'text-gray-400', badgeVariant: 'secondary' },
  queued: { icon: Clock, color: 'text-gray-400', badgeVariant: 'secondary' },
  running: { icon: Loader2, color: 'text-blue-500', badgeVariant: 'default' },
  paused: { icon: AlertCircle, color: 'text-yellow-500', badgeVariant: 'warning' },
  completed: { icon: CheckCircle2, color: 'text-green-500', badgeVariant: 'success' },
  failed: { icon: XCircle, color: 'text-red-500', badgeVariant: 'destructive' },
  cancelled: { icon: Ban, color: 'text-gray-500', badgeVariant: 'secondary' },
  retrying: { icon: RotateCcw, color: 'text-orange-500', badgeVariant: 'warning' },
  timed_out: { icon: AlertCircle, color: 'text-orange-500', badgeVariant: 'warning' },
};

export const ExecutionProgress = memo(function ExecutionProgress({ execution }: ExecutionProgressProps) {
  const completed = execution.nodeExecutions.filter(
    (ne) => ne.status === 'completed' || ne.status === 'failed' || ne.status === 'cancelled'
  ).length;
  const total = execution.nodeExecutions.length;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {completed} / {total} nodes
          </span>
          <span className="text-muted-foreground">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
          <div
            className={cn(
              'h-full transition-all duration-300',
              execution.status === 'completed' ? 'bg-green-500' :
              execution.status === 'failed' ? 'bg-red-500' :
              execution.status === 'running' ? 'bg-blue-500 animate-pulse' :
              'bg-gray-400'
            )}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Node list */}
      <div className="space-y-2">
        {execution.nodeExecutions.map((nodeExecution) => {
          const config = statusConfig[nodeExecution.status];
          const Icon = config.icon;

          return (
            <div
              key={nodeExecution.nodeId}
              className="flex items-center gap-2 text-sm"
            >
              <Icon
                className={cn(
                  'h-4 w-4',
                  config.color,
                  nodeExecution.status === 'running' && 'animate-spin'
                )}
              />
              <span className="flex-1 truncate font-mono text-xs">
                {nodeExecution.nodeId}
              </span>
              <Badge variant={config.badgeVariant} className="text-xs">
                {nodeExecution.status}
              </Badge>
              {nodeExecution.durationMs != null && (
                <span className="text-xs text-muted-foreground">
                  {nodeExecution.durationMs}ms
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
});
