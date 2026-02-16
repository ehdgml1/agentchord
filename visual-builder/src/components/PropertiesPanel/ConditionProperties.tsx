/**
 * Properties editor for Condition blocks
 *
 * Provides form controls for configuring condition expressions
 * and branch labels.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import type { ConditionBlockData } from '../../types/blocks';

interface ConditionPropertiesProps {
  data: ConditionBlockData;
  onChange: (data: Partial<ConditionBlockData>) => void;
}

export const ConditionProperties = memo(function ConditionProperties({
  data,
  onChange,
}: ConditionPropertiesProps) {
  const handleConditionChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange({ condition: e.target.value });
    },
    [onChange]
  );

  const handleTrueLabelChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ trueLabel: e.target.value });
    },
    [onChange]
  );

  const handleFalseLabelChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ falseLabel: e.target.value });
    },
    [onChange]
  );

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="condition">Condition Expression</Label>
        <Textarea
          id="condition"
          value={data.condition || ''}
          onChange={handleConditionChange}
          placeholder="len(input) > 5 and status == 'active'"
          rows={4}
          className="font-mono text-sm"
        />
        <p className="text-xs text-muted-foreground">
          Safe functions: len, str, int, float, bool, abs, min, max, any, all
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="trueLabel">True Branch Label</Label>
        <Input
          id="trueLabel"
          value={data.trueLabel || 'Yes'}
          onChange={handleTrueLabelChange}
          placeholder="Yes"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="falseLabel">False Branch Label</Label>
        <Input
          id="falseLabel"
          value={data.falseLabel || 'No'}
          onChange={handleFalseLabelChange}
          placeholder="No"
        />
      </div>
    </div>
  );
});
