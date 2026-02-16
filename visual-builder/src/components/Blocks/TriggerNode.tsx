/**
 * TriggerNode component for Visual Builder
 *
 * A workflow trigger node that can be either a Cron schedule
 * or Webhook trigger. This is always the starting point of
 * automated workflow executions.
 */

import { memo } from 'react';
import { type NodeProps } from '@xyflow/react';
import { Clock, Globe } from 'lucide-react';
import { BaseNode } from './BaseNode';
import { cronToHuman, formatNextRun } from '../../lib/cronUtils';

import type { TriggerBlockData } from '../../types/blocks';

type TriggerNodeProps = NodeProps & {
  data: TriggerBlockData & { label?: string; nextRunAt?: string; webhookId?: string };
};

/**
 * Color constants for trigger types
 */
const COLORS = {
  cron: '#8B5CF6', // Purple for scheduled
  webhook: '#10B981', // Green for webhook
} as const;

export const TriggerNode = memo(function TriggerNode({
  data,
  selected,
}: TriggerNodeProps) {
  const isCron = data.triggerType === 'cron';
  const color = COLORS[data.triggerType];
  const Icon = isCron ? Clock : Globe;

  // Format the cron expression for display
  const cronDisplay = isCron && data.cronExpression
    ? cronToHuman(data.cronExpression)
    : null;

  // Format next run time if available
  const nextRunDisplay = data.nextRunAt
    ? formatNextRun(new Date(data.nextRunAt))
    : null;

  // Format webhook URL for display
  const webhookUrl = !isCron && data.webhookPath
    ? `/api/webhooks/${data.webhookPath}`
    : null;

  return (
    <BaseNode color={color} selected={selected} hasInput={false} hasOutput>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <div
            className="p-1.5 rounded"
            style={{ backgroundColor: `${color}20` }}
          >
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm">
              {isCron ? 'Schedule' : 'Webhook'}
            </div>
            <div className="text-xs text-muted-foreground">
              {isCron ? 'Cron Trigger' : 'HTTP Trigger'}
            </div>
          </div>
        </div>

        {/* Cron-specific display */}
        {isCron && cronDisplay && (
          <div className="text-xs text-muted-foreground mb-1">
            {cronDisplay}
          </div>
        )}

        {/* Cron expression */}
        {isCron && data.cronExpression && (
          <code className="block text-xs bg-gray-100 rounded px-1.5 py-0.5 font-mono mb-1">
            {data.cronExpression}
          </code>
        )}

        {/* Next run time for cron */}
        {isCron && nextRunDisplay && (
          <div className="text-xs text-muted-foreground">
            Next: {nextRunDisplay}
          </div>
        )}

        {/* Webhook URL display */}
        {webhookUrl && (
          <code className="block text-xs bg-gray-100 rounded px-1.5 py-0.5 font-mono truncate">
            {webhookUrl}
          </code>
        )}
      </div>
    </BaseNode>
  );
});
