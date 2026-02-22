/**
 * Properties editor for Trigger blocks
 *
 * Provides form controls for configuring trigger type (cron/webhook),
 * cron expressions with presets, and webhook paths.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { TriggerBlockData } from '../../types/blocks';

interface TriggerPropertiesProps {
  data: TriggerBlockData;
  onChange: (data: Partial<TriggerBlockData>) => void;
}

const CRON_PRESETS = [
  { label: 'Every minute', value: '* * * * *' },
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Daily 9AM', value: '0 9 * * *' },
  { label: 'Weekly Mon', value: '0 9 * * 1' },
];

export const TriggerProperties = memo(function TriggerProperties({
  data,
  onChange,
}: TriggerPropertiesProps) {
  const handleTriggerTypeChange = useCallback(
    (value: string) => {
      onChange({ triggerType: value as 'cron' | 'webhook' });
    },
    [onChange]
  );

  const handleCronExpressionChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ cronExpression: e.target.value });
    },
    [onChange]
  );

  const handleWebhookPathChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ webhookPath: e.target.value });
    },
    [onChange]
  );

  const handlePresetClick = useCallback(
    (value: string) => {
      onChange({ cronExpression: value });
    },
    [onChange]
  );

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Label htmlFor="triggerType">Trigger Type</Label>
        <Select value={data.triggerType} onValueChange={handleTriggerTypeChange}>
          <SelectTrigger id="triggerType">
            <SelectValue placeholder="Select trigger type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="cron">Schedule (Cron)</SelectItem>
            <SelectItem value="webhook">Webhook (HTTP)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {data.triggerType === 'cron' && (
        <>
          <div className="space-y-2">
            <Label htmlFor="cronExpression">Cron Expression</Label>
            <Input
              id="cronExpression"
              value={data.cronExpression || ''}
              onChange={handleCronExpressionChange}
              placeholder="0 9 * * *"
            />
            <div className="flex flex-wrap gap-1 mt-1">
              {CRON_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => handlePresetClick(preset.value)}
                  className="text-xs text-muted-foreground hover:text-foreground underline"
                >
                  {preset.label}: {preset.value}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {data.triggerType === 'webhook' && (
        <div className="space-y-2">
          <Label htmlFor="webhookPath">Webhook Path</Label>
          <Input
            id="webhookPath"
            value={data.webhookPath || ''}
            onChange={handleWebhookPathChange}
            placeholder="/my-webhook"
          />
        </div>
      )}
    </div>
  );
});
