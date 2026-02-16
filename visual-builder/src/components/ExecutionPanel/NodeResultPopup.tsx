import { memo } from 'react';
import { CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import type { NodeExecution } from '../../types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Label } from '../ui/label';
import { cn } from '../../lib/utils';

interface NodeResultPopupProps {
  nodeExecution: NodeExecution | null;
  onClose: () => void;
}

export const NodeResultPopup = memo(function NodeResultPopup({ nodeExecution, onClose }: NodeResultPopupProps) {
  if (!nodeExecution) return null;

  const getStatusIcon = () => {
    switch (nodeExecution.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'running':
        return <Clock className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusVariant = (): 'default' | 'secondary' | 'destructive' | 'success' | 'warning' => {
    switch (nodeExecution.status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'destructive';
      case 'running':
        return 'default';
      case 'timed_out':
      case 'retrying':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatJSON = (data: unknown) => {
    if (data === null || data === undefined) return 'null';
    return JSON.stringify(data, null, 2);
  };

  return (
    <Dialog open={!!nodeExecution} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div className="flex-1">
              <DialogTitle className="font-mono">{nodeExecution.nodeId}</DialogTitle>
              <DialogDescription>Node execution details</DialogDescription>
            </div>
            <Badge variant={getStatusVariant()}>{nodeExecution.status}</Badge>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <Label className="text-muted-foreground">Started At</Label>
              <p className="mt-1">{formatTimestamp(nodeExecution.startedAt)}</p>
            </div>
            {nodeExecution.completedAt && (
              <div>
                <Label className="text-muted-foreground">Completed At</Label>
                <p className="mt-1">{formatTimestamp(nodeExecution.completedAt)}</p>
              </div>
            )}
            {nodeExecution.durationMs !== null && (
              <div>
                <Label className="text-muted-foreground">Duration</Label>
                <p className="mt-1">{nodeExecution.durationMs}ms</p>
              </div>
            )}
            {nodeExecution.retryCount > 0 && (
              <div>
                <Label className="text-muted-foreground">Retry Count</Label>
                <p className="mt-1">{nodeExecution.retryCount}</p>
              </div>
            )}
          </div>

          {/* Input */}
          <div>
            <Label className="text-muted-foreground">Input</Label>
            <pre className={cn(
              "mt-2 rounded-md border bg-muted p-4 text-xs overflow-x-auto",
              "max-h-48 overflow-y-auto"
            )}>
              {formatJSON(nodeExecution.input)}
            </pre>
          </div>

          {/* Output */}
          {nodeExecution.output != null && (
            <div>
              <Label className="text-muted-foreground">Output</Label>
              <pre className={cn(
                "mt-2 rounded-md border bg-muted p-4 text-xs overflow-x-auto",
                "max-h-48 overflow-y-auto"
              )}>
                {formatJSON(nodeExecution.output)}
              </pre>
            </div>
          )}

          {/* Error */}
          {nodeExecution.error && (
            <div>
              <Label className="text-red-500">Error</Label>
              <pre className={cn(
                "mt-2 rounded-md border border-red-200 bg-red-50 dark:bg-red-950/20 p-4 text-xs overflow-x-auto",
                "text-red-700 dark:text-red-400",
                "max-h-48 overflow-y-auto"
              )}>
                {nodeExecution.error}
              </pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
});
