import { memo, useCallback, useEffect, useState } from 'react';
import { RefreshCw, ChevronRight, ChevronDown, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';
import { useExecutionStore } from '../../stores/executionStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useExecutionProgress } from '../../hooks/useExecutionProgress';
import { LogViewer } from './LogViewer';
import type { ExecutionStatus } from '../../types/execution';

interface ExecutionPanelProps {
  className?: string;
}

const getStatusIcon = (status: ExecutionStatus) => {
  switch (status) {
    case 'completed':
      return '✓';
    case 'failed':
      return '✗';
    case 'running':
      return '●';
    case 'pending':
    case 'queued':
      return '○';
    default:
      return '○';
  }
};

const getStatusColor = (status: ExecutionStatus) => {
  switch (status) {
    case 'completed':
      return 'text-green-600';
    case 'failed':
      return 'text-red-600';
    case 'running':
      return 'text-blue-600';
    default:
      return 'text-gray-400';
  }
};

const formatTime = (isoString: string) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', { hour12: false });
};

const formatDuration = (ms: number | null) => {
  if (ms === null) return '...';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

const formatCost = (cost: number | null) => {
  if (cost === null) return '-';
  return `$${cost.toFixed(4)}`;
};

const formatTokens = (tokens: number | null) => {
  if (tokens === null) return '-';
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return String(tokens);
};

export const ExecutionPanel = memo(function ExecutionPanel({ className }: ExecutionPanelProps) {
  const workflowId = useWorkflowStore((state) => state.workflowId);
  const { executions, currentExecution, isLoading, fetchExecutions, fetchExecution } =
    useExecutionStore();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  const displayExecution = selectedId
    ? (currentExecution?.id === selectedId ? currentExecution : executions.find((e) => e.id === selectedId)) ?? null
    : currentExecution;

  const { events, isStreaming } = useExecutionProgress(
    displayExecution?.status === 'running' ? displayExecution.id : null
  );

  useEffect(() => {
    fetchExecutions(workflowId);
  }, [workflowId, fetchExecutions]);

  // Auto-select new execution when it becomes current
  useEffect(() => {
    if (currentExecution?.status === 'running' && !selectedId) {
      setSelectedId(currentExecution.id);
    }
  }, [currentExecution, selectedId]);

  const handleSelectExecution = useCallback(
    (id: string) => {
      setSelectedId(id);
      fetchExecution(id);
    },
    [fetchExecution]
  );

  const handleRefresh = useCallback(() => {
    fetchExecutions(workflowId);
  }, [workflowId, fetchExecutions]);

  return (
    <div className={cn('flex flex-col shrink-0', className)} aria-label="Execution history panel">
      <div className="border-t">
        <div className="flex items-center justify-between px-4 py-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            Execution History
          </button>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleRefresh}>
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className="flex flex-col max-h-[50vh] overflow-hidden shrink-0">
          <div className="border-t px-4 py-3">
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {executions.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">No executions yet</p>
              ) : (
                executions.map((execution) => (
                  <button
                    key={execution.id}
                    onClick={() => handleSelectExecution(execution.id)}
                    aria-label={`Execution ${execution.status} at ${formatTime(execution.startedAt)}`}
                    aria-current={selectedId === execution.id ? 'true' : undefined}
                    className={cn(
                      'w-full text-left px-2 py-1.5 rounded text-xs hover:bg-accent transition-colors',
                      selectedId === execution.id && 'bg-accent'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span className={cn('font-bold', getStatusColor(execution.status))}>
                        {getStatusIcon(execution.status)}
                      </span>
                      <span className="flex-1 font-mono">{formatTime(execution.startedAt)}</span>
                      <span className={cn('font-medium', getStatusColor(execution.status))}>
                        {execution.status}
                      </span>
                      <span className="text-muted-foreground">
                        {formatDuration(execution.durationMs)}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {displayExecution && displayExecution.totalTokens != null && (
            <div className="border-t px-4 py-3">
              <div className="flex items-center gap-1.5 mb-2">
                <Zap className="w-3.5 h-3.5 text-yellow-500" />
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Token Usage
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Model:</span>{' '}
                  <span className="font-medium">{displayExecution.modelUsed || '-'}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Cost:</span>{' '}
                  <span className="font-medium">{formatCost(displayExecution.estimatedCost)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Prompt:</span>{' '}
                  <span className="font-medium">{formatTokens(displayExecution.promptTokens)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Completion:</span>{' '}
                  <span className="font-medium">{formatTokens(displayExecution.completionTokens)}</span>
                </div>
                <div className="col-span-2">
                  <span className="text-muted-foreground">Total:</span>{' '}
                  <span className="font-medium">{formatTokens(displayExecution.totalTokens)}</span>
                </div>
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 py-3 border-t">
            <div className="mb-3 flex items-center gap-2">
              <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
                Node Logs
              </h3>
              {isStreaming && (
                <span className="flex items-center gap-1 text-xs text-blue-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                  Live
                </span>
              )}
              {displayExecution && (
                <ChevronRight className="w-3 h-3 text-muted-foreground" />
              )}
              {displayExecution && (
                <span className="text-xs font-medium">
                  {displayExecution.nodeExecutions?.length ?? 0} node
                  {(displayExecution.nodeExecutions?.length ?? 0) !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            {displayExecution ? (
              <LogViewer nodeExecutions={displayExecution.nodeExecutions ?? []} />
            ) : (
              <div className="text-sm text-muted-foreground text-center py-8">
                Select an execution to view logs
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
});
