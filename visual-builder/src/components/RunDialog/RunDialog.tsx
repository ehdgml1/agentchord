import { memo, useState, useCallback } from 'react';
import { Play } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useExecutionStore } from '../../stores/executionStore';
import type { ExecutionMode } from '../../types/execution';
import { toast } from 'sonner';

interface RunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const EXECUTION_MODES = [
  {
    value: 'full' as ExecutionMode,
    label: 'Full Run',
    description: 'Execute with real APIs and services',
  },
  {
    value: 'mock' as ExecutionMode,
    label: 'Mock Run',
    description: 'Use mock responses for testing',
  },
  {
    value: 'debug' as ExecutionMode,
    label: 'Debug Mode',
    description: 'Step through nodes with detailed logging',
  },
] as const;

export const RunDialog = memo(function RunDialog({ open, onOpenChange }: RunDialogProps) {
  const [mode, setMode] = useState<ExecutionMode>('full');
  const [input, setInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);

  const backendId = useWorkflowStore((state) => state.backendId);
  const saveWorkflow = useWorkflowStore((state) => state.saveWorkflow);
  const runWorkflow = useExecutionStore((state) => state.runWorkflow);

  const handleRun = useCallback(async () => {
    if (!input.trim()) {
      toast.error('Please provide input for the workflow');
      return;
    }

    setIsRunning(true);

    try {
      // Auto-save to backend if not yet saved
      let effectiveId = backendId;
      if (!effectiveId) {
        await saveWorkflow();
        // After save, the store now has backendId
        effectiveId = useWorkflowStore.getState().backendId;
      }

      if (!effectiveId) {
        toast.error('Failed to save workflow to server');
        return;
      }

      await runWorkflow(effectiveId, input, mode);
      toast.success('Workflow execution started');
      onOpenChange(false);
      setInput('');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to run workflow');
    } finally {
      setIsRunning(false);
    }
  }, [input, mode, backendId, saveWorkflow, runWorkflow, onOpenChange]);

  const handleCancel = useCallback(() => {
    onOpenChange(false);
    setInput('');
    setMode('full');
  }, [onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Run Workflow</DialogTitle>
          <DialogDescription>
            Choose an execution mode and provide input to run your workflow.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="space-y-3">
            <Label className="text-base font-semibold">Execution Mode</Label>
            <RadioGroup value={mode} onValueChange={(value) => setMode(value as ExecutionMode)}>
              {EXECUTION_MODES.map((modeOption) => (
                <div key={modeOption.value} className="flex items-start space-x-3 space-y-0">
                  <RadioGroupItem value={modeOption.value} id={modeOption.value} />
                  <div className="flex-1">
                    <Label
                      htmlFor={modeOption.value}
                      className="font-medium cursor-pointer"
                    >
                      {modeOption.label}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {modeOption.description}
                    </p>
                  </div>
                </div>
              ))}
            </RadioGroup>
          </div>

          <div className="space-y-2">
            <Label htmlFor="input" className="text-base font-semibold">
              Input
            </Label>
            <Textarea
              id="input"
              placeholder="Enter your workflow input here..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={6}
              className="resize-none"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isRunning}>
            Cancel
          </Button>
          <Button onClick={handleRun} disabled={isRunning}>
            <Play className="w-4 h-4 mr-2" />
            {isRunning ? 'Running...' : 'Run'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});
