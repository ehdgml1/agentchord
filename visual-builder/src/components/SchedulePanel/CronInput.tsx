/**
 * CronInput component for Visual Builder
 *
 * An interactive cron expression input with live preview,
 * validation feedback, and common presets dropdown.
 */

import { useMemo, useCallback } from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  CRON_PRESETS,
  cronToHuman,
  validateCron,
  getNextRuns,
  formatNextRun,
} from '../../lib/cronUtils';

interface CronInputProps {
  /** Current cron expression value */
  value: string;
  /** Callback when expression changes */
  onChange: (value: string) => void;
  /** Timezone for calculating next runs */
  timezone?: string;
  /** Whether the input is disabled */
  disabled?: boolean;
}

export function CronInput({
  value,
  onChange,
  timezone,
  disabled = false,
}: CronInputProps) {
  // Validate the current expression
  const validation = useMemo(() => validateCron(value), [value]);

  // Get human-readable format
  const humanReadable = useMemo(() => {
    if (!validation.valid) return null;
    return cronToHuman(value);
  }, [value, validation.valid]);

  // Get next 5 run times
  const nextRuns = useMemo(() => {
    if (!validation.valid) return [];
    return getNextRuns(value, 5, timezone);
  }, [value, validation.valid, timezone]);

  // Handle preset selection
  const handlePresetSelect = useCallback(
    (preset: string) => {
      const found = CRON_PRESETS.find((p) => p.expression === preset);
      if (found) {
        onChange(found.expression);
      }
    },
    [onChange]
  );

  return (
    <div className="space-y-3">
      {/* Expression Input */}
      <div className="space-y-1.5">
        <Label htmlFor="cron-expression">Cron Expression</Label>
        <div className="flex gap-2">
          <Input
            id="cron-expression"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="* * * * *"
            className="font-mono"
            disabled={disabled}
          />
          <Select
            value=""
            onValueChange={handlePresetSelect}
            disabled={disabled}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Presets" />
            </SelectTrigger>
            <SelectContent>
              {CRON_PRESETS.map((preset) => (
                <SelectItem key={preset.expression} value={preset.expression}>
                  {preset.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          Format: minute hour day month weekday
        </p>
      </div>

      {/* Validation Status */}
      <div className="flex items-center gap-2 text-sm">
        {validation.valid ? (
          <>
            <CheckCircle className="w-4 h-4 text-green-600" />
            <span className="text-green-600">{humanReadable}</span>
          </>
        ) : (
          <>
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-red-500">{validation.error}</span>
          </>
        )}
      </div>

      {/* Next Run Times Preview */}
      {validation.valid && nextRuns.length > 0 && (
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground">
            Next 5 executions
          </Label>
          <div className="bg-gray-50 rounded-md p-2 space-y-1">
            {nextRuns.map((date, index) => (
              <div
                key={index}
                className="text-xs text-muted-foreground font-mono"
              >
                {formatNextRun(date, timezone)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
