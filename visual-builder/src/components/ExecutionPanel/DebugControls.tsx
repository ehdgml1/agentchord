import { Play, StepForward, Square } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

interface DebugControlsProps {
  isDebugging: boolean;
  isPaused: boolean;
  currentNode: string | null;
  isConnected: boolean;
  onContinue: () => void;
  onStep: () => void;
  onStop: () => void;
}

/**
 * Debug controls for step-through workflow execution.
 * Wired to useDebugWebSocket hook for real-time debugging.
 */
export function DebugControls({
  isDebugging,
  isPaused,
  currentNode,
  isConnected,
  onContinue,
  onStep,
  onStop,
}: DebugControlsProps) {
  if (!isDebugging) {
    return null;
  }

  return (
    <div className="space-y-2 p-3 border-b bg-muted/30">
      <div className="flex items-center gap-3">
        <Badge variant={isConnected ? 'default' : 'secondary'} className="gap-1">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-600 animate-pulse' : 'bg-gray-400'
            }`}
          />
          {isConnected ? 'Debug Active' : 'Disconnected'}
        </Badge>

        {isPaused && currentNode && (
          <div className="text-sm text-muted-foreground">
            Paused at: <span className="font-mono font-medium">{currentNode}</span>
          </div>
        )}

        <div className="flex gap-2 ml-auto">
          <Button
            size="sm"
            variant="outline"
            onClick={onContinue}
            disabled={!isPaused || !isConnected}
            title="Continue execution"
          >
            <Play className="w-4 h-4" />
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={onStep}
            disabled={!isPaused || !isConnected}
            title="Step to next node"
          >
            <StepForward className="w-4 h-4" />
          </Button>

          <Button
            size="sm"
            variant="destructive"
            onClick={onStop}
            disabled={!isConnected}
            title="Stop debugging"
          >
            <Square className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
