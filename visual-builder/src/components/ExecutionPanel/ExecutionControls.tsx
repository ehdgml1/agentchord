import { memo, useState, useCallback } from 'react';
import { Play, Square, RotateCcw } from 'lucide-react';
import { useExecutionStore } from '../../stores/executionStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import type { ExecutionMode } from '../../types';
import { cn } from '../../lib/utils';
import { formatDuration, getStatusBadgeVariant } from '../../utils/execution';

interface ExecutionControlsProps {
  className?: string;
}

export const ExecutionControls = memo(function ExecutionControls({ className }: ExecutionControlsProps) {
  const workflowId = useWorkflowStore(s => s.workflowId);
  const {
    currentExecution,
    isLoading,
    error,
    runWorkflow,
    stopExecution,
    resumeExecution,
  } = useExecutionStore();

  const [input, setInput] = useState('{}');
  const [mode, setMode] = useState<ExecutionMode>('mock');

  const handleRun = useCallback(async () => {
    try {
      await runWorkflow(workflowId, input, mode);
    } catch {
      // Error handled by execution store
    }
  }, [workflowId, input, mode, runWorkflow]);

  const handleStop = useCallback(async () => {
    if (currentExecution) {
      await stopExecution(currentExecution.id);
    }
  }, [currentExecution, stopExecution]);

  const handleResume = useCallback(async () => {
    if (currentExecution) {
      await resumeExecution(currentExecution.id);
    }
  }, [currentExecution, resumeExecution]);

  const canRun = !!workflowId && !isLoading && (!currentExecution || ['completed', 'failed', 'cancelled', 'timed_out'].includes(currentExecution.status));
  const canStop = currentExecution && currentExecution.status === 'running';
  const canResume = currentExecution && currentExecution.status === 'paused';

  return (
    <div className={cn('p-4 border-b space-y-4', className)}>
      {/* Error display */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-950/20 p-3 text-sm text-red-700 dark:text-red-400 border border-red-200">
          {error}
        </div>
      )}

      {/* Current execution status */}
      {currentExecution && (
        <div className="flex items-center justify-between" role="status" aria-live="polite">
          <div className="flex items-center gap-2">
            <Badge variant={getStatusBadgeVariant(currentExecution.status)} className="text-xs">
              {currentExecution.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              Duration: {formatDuration(currentExecution.durationMs)}
            </span>
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            {currentExecution.id}
          </span>
        </div>
      )}

      {/* Run controls */}
      <div className="space-y-3">
        <div className="grid grid-cols-[1fr,auto] gap-2 items-end">
          <div>
            <Label htmlFor="mode" className="text-xs text-muted-foreground">
              Mode
            </Label>
            <Select value={mode} onValueChange={(v) => setMode(v as ExecutionMode)}>
              <SelectTrigger id="mode" className="mt-1 h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mock">Mock - Simulate execution</SelectItem>
                <SelectItem value="full">Full - Real execution</SelectItem>
                <SelectItem value="debug">Debug - Step through</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleRun}
              disabled={!canRun}
              size="sm"
              className="gap-2"
              aria-label="Run workflow"
            >
              <Play className="h-4 w-4" />
              Run
            </Button>
            {canStop && (
              <Button
                onClick={handleStop}
                variant="destructive"
                size="sm"
                className="gap-2"
                aria-label="Stop workflow execution"
              >
                <Square className="h-4 w-4" />
                Stop
              </Button>
            )}
            {canResume && (
              <Button
                onClick={handleResume}
                variant="secondary"
                size="sm"
                className="gap-2"
                aria-label="Resume paused workflow"
              >
                <RotateCcw className="h-4 w-4" />
                Resume
              </Button>
            )}
          </div>
        </div>

        <div>
          <Label htmlFor="input" className="text-xs text-muted-foreground">
            Input (JSON)
          </Label>
          <Textarea
            id="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='{"key": "value"}'
            className="mt-1 font-mono text-xs"
            rows={3}
            disabled={!canRun}
          />
        </div>
      </div>

      {/* Output */}
      {currentExecution && currentExecution.output != null && (
        <div>
          <Label className="text-xs text-muted-foreground">Output</Label>
          <pre className="mt-2 rounded-md border bg-muted p-3 text-xs overflow-x-auto max-h-32 overflow-y-auto">
            {JSON.stringify(currentExecution.output, null, 2)}
          </pre>
        </div>
      )}

      {/* Error */}
      {currentExecution?.error && (
        <div>
          <Label className="text-xs text-red-500">Error</Label>
          <pre className="mt-2 rounded-md border border-red-200 bg-red-50 dark:bg-red-950/20 p-3 text-xs text-red-700 dark:text-red-400 overflow-x-auto max-h-32 overflow-y-auto">
            {currentExecution.error}
          </pre>
        </div>
      )}
    </div>
  );
});
