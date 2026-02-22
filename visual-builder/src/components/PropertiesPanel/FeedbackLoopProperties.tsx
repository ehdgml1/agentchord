/**
 * Properties editor for Feedback Loop blocks
 *
 * Provides form controls for configuring loop iterations
 * and stop conditions with a visual condition builder.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ConditionBuilder } from './ConditionBuilder';
import type { FeedbackLoopBlockData } from '../../types/blocks';

interface FeedbackLoopPropertiesProps {
  nodeId: string;
  data: FeedbackLoopBlockData;
  onChange: (data: Partial<FeedbackLoopBlockData>) => void;
}

export const FeedbackLoopProperties = memo(function FeedbackLoopProperties({
  nodeId,
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
    (condition: string) => {
      onChange({ stopCondition: condition });
    },
    [onChange]
  );

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="maxIterations">최대 반복 횟수</Label>
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

      <ConditionBuilder
        nodeId={nodeId}
        value={data.stopCondition || ''}
        onChange={handleStopConditionChange}
      />
    </div>
  );
});
