/**
 * Shared execution utilities
 *
 * Common helpers for formatting and displaying execution data.
 */

import type { ExecutionStatus } from '../types/execution';

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Get badge variant for execution status
 */
export function getStatusBadgeVariant(
  status: ExecutionStatus
): 'default' | 'secondary' | 'destructive' | 'success' | 'warning' {
  switch (status) {
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
}

/**
 * Get CSS color class for execution status
 */
export function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case 'completed':
      return 'text-green-500';
    case 'failed':
      return 'text-red-500';
    case 'running':
      return 'text-blue-500';
    case 'paused':
    case 'retrying':
      return 'text-yellow-500';
    case 'timed_out':
      return 'text-orange-500';
    default:
      return 'text-gray-400';
  }
}

/**
 * Status icon configuration for execution visualization
 */
export const STATUS_ICON_CONFIG: Record<ExecutionStatus, {
  color: string;
  bgColor: string;
  animate?: boolean;
}> = {
  pending: { color: 'text-gray-400', bgColor: 'border-gray-200 bg-gray-50' },
  queued: { color: 'text-gray-400', bgColor: 'border-gray-200 bg-gray-50' },
  running: { color: 'text-blue-500', bgColor: 'border-blue-200 bg-blue-50', animate: true },
  paused: { color: 'text-yellow-500', bgColor: 'border-yellow-200 bg-yellow-50' },
  completed: { color: 'text-green-500', bgColor: 'border-green-200 bg-green-50' },
  failed: { color: 'text-red-500', bgColor: 'border-red-200 bg-red-50' },
  cancelled: { color: 'text-gray-500', bgColor: 'border-gray-200 bg-gray-50' },
  retrying: { color: 'text-orange-500', bgColor: 'border-orange-200 bg-orange-50' },
  timed_out: { color: 'text-orange-500', bgColor: 'border-orange-200 bg-orange-50' },
};
