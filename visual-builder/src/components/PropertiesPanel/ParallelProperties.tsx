/**
 * Properties editor for Parallel blocks
 *
 * Provides form controls for configuring parallel execution
 * and merge strategies.
 */

import { memo, useCallback } from 'react';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { ParallelBlockData } from '../../types/blocks';

interface ParallelPropertiesProps {
  data: ParallelBlockData;
  onChange: (data: Partial<ParallelBlockData>) => void;
}

const MERGE_STRATEGIES = [
  {
    value: 'concat',
    label: 'Collect all',
    description: 'Combine all results into an array',
  },
  {
    value: 'first',
    label: 'First result',
    description: 'Use the first completed result',
  },
  {
    value: 'last',
    label: 'Last result',
    description: 'Use the last completed result',
  },
  {
    value: 'custom',
    label: 'Custom merge',
    description: 'Define custom merge logic',
  },
] as const;

export const ParallelProperties = memo(function ParallelProperties({
  data,
  onChange,
}: ParallelPropertiesProps) {
  const handleMergeStrategyChange = useCallback(
    (value: string) => {
      onChange({ mergeStrategy: value as ParallelBlockData['mergeStrategy'] });
    },
    [onChange]
  );

  const currentStrategy = MERGE_STRATEGIES.find(
    (s) => s.value === data.mergeStrategy
  );

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="mergeStrategy">Merge Strategy</Label>
        <Select
          value={data.mergeStrategy || 'concat'}
          onValueChange={handleMergeStrategyChange}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select merge strategy" />
          </SelectTrigger>
          <SelectContent>
            {MERGE_STRATEGIES.map((strategy) => (
              <SelectItem key={strategy.value} value={strategy.value}>
                {strategy.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {currentStrategy && (
          <p className="text-xs text-muted-foreground">
            {currentStrategy.description}
          </p>
        )}
      </div>
    </div>
  );
});
