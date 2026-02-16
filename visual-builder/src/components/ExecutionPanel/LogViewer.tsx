import { memo, useMemo } from 'react';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { NodeExecution, ExecutionStatus } from '../../types/execution';
import { STATUS_ICON_CONFIG, formatDuration } from '../../utils/execution';

interface LogViewerProps {
  nodeExecutions: NodeExecution[];
  className?: string;
}

const getStatusIcon = (status: ExecutionStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-600" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-600" />;
    case 'running':
      return <Clock className="w-4 h-4 text-blue-600 animate-pulse" />;
    case 'pending':
    case 'queued':
      return <Clock className="w-4 h-4 text-gray-400" />;
    case 'retrying':
      return <AlertCircle className="w-4 h-4 text-yellow-600" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
};

const getStatusColor = (status: ExecutionStatus) => STATUS_ICON_CONFIG[status]?.bgColor || 'border-gray-200 bg-gray-50';

export const LogViewer = memo(function LogViewer({ nodeExecutions, className }: LogViewerProps) {
  const sortedExecutions = useMemo(
    () => [...nodeExecutions].sort((a, b) =>
      new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime()
    ),
    [nodeExecutions]
  );

  return (
    <div className={cn('space-y-2', className)} role="log" aria-label="Execution logs">
      {sortedExecutions.length === 0 ? (
        <div className="text-sm text-muted-foreground text-center py-8">
          No execution logs available
        </div>
      ) : (
        sortedExecutions.map((nodeExec) => (
          <div
            key={nodeExec.nodeId}
            className={cn(
              'border rounded-lg p-3 transition-colors',
              getStatusColor(nodeExec.status)
            )}
          >
            <div className="flex items-start gap-2">
              {getStatusIcon(nodeExec.status)}
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="font-medium text-sm">{nodeExec.nodeId}</span>
                  <span className="text-xs text-muted-foreground">
                    ({formatDuration(nodeExec.durationMs)})
                  </span>
                  {nodeExec.retryCount > 0 && (
                    <span className="text-xs text-yellow-600">
                      Retry {nodeExec.retryCount}
                    </span>
                  )}
                </div>

                {nodeExec.input !== undefined && (
                  <div className="mb-2">
                    <div className="text-xs font-medium text-muted-foreground mb-1">
                      Input:
                    </div>
                    <div className="text-xs font-mono bg-background border rounded p-2 overflow-x-auto">
                      {typeof nodeExec.input === 'string'
                        ? nodeExec.input
                        : JSON.stringify(nodeExec.input, null, 2)}
                    </div>
                  </div>
                )}

                {nodeExec.output !== null && nodeExec.output !== undefined && (
                  <div className="mb-2">
                    <div className="text-xs font-medium text-muted-foreground mb-1">
                      Output:
                    </div>
                    <div className="text-xs font-mono bg-background border rounded p-2 overflow-x-auto">
                      {typeof nodeExec.output === 'string'
                        ? nodeExec.output
                        : JSON.stringify(nodeExec.output, null, 2)}
                    </div>
                  </div>
                )}

                {nodeExec.error && (
                  <div>
                    <div className="text-xs font-medium text-red-600 mb-1">Error:</div>
                    <div className="text-xs font-mono bg-red-100 border border-red-200 rounded p-2 text-red-700">
                      {nodeExec.error}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
});
