/**
 * Properties editor for Feedback Loop blocks
 *
 * Provides form controls for configuring loop iterations
 * and stop conditions.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import type { FeedbackLoopBlockData } from '../../types/blocks';

interface FeedbackLoopPropertiesProps {
  data: FeedbackLoopBlockData;
  onChange: (data: Partial<FeedbackLoopBlockData>) => void;
}

export const FeedbackLoopProperties = memo(function FeedbackLoopProperties({
  data,
  onChange,
}: FeedbackLoopPropertiesProps) {
  const handleMaxIterationsChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value)) {
        onChange({ maxIterations: value });
      }
    },
    [onChange]
  );

  const handleStopConditionChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange({ stopCondition: e.target.value });
    },
    [onChange]
  );

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="maxIterations">Max Iterations</Label>
        <Input
          id="maxIterations"
          type="number"
          min={1}
          max={1000}
          value={data.maxIterations || 10}
          onChange={handleMaxIterationsChange}
          placeholder="10"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="stopCondition">Stop Condition</Label>
        <Textarea
          id="stopCondition"
          value={data.stopCondition || ''}
          onChange={handleStopConditionChange}
          placeholder="iteration > 5 or result == 'done'"
          rows={4}
          className="font-mono text-sm"
        />
        <p className="text-xs text-muted-foreground">
          Available variables: iteration (current count), result (previous output)
        </p>
      </div>
    </div>
  );
});
