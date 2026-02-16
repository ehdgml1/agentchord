import { describe, it, expect } from 'vitest';
import {
  formatDuration,
  getStatusBadgeVariant,
  getStatusColor,
  STATUS_ICON_CONFIG,
} from './execution';
import type { ExecutionStatus } from '../types/execution';

describe('formatDuration', () => {
  it('returns "-" for null', () => {
    expect(formatDuration(null)).toBe('-');
  });

  it('returns "-" for undefined', () => {
    expect(formatDuration(undefined)).toBe('-');
  });

  it('formats milliseconds when less than 1000', () => {
    expect(formatDuration(500)).toBe('500ms');
    expect(formatDuration(0)).toBe('0ms');
    expect(formatDuration(999)).toBe('999ms');
  });

  it('formats seconds with 2 decimal places', () => {
    expect(formatDuration(1000)).toBe('1.00s');
    expect(formatDuration(1500)).toBe('1.50s');
    expect(formatDuration(5432)).toBe('5.43s');
  });
});

describe('getStatusBadgeVariant', () => {
  it('returns "success" for completed status', () => {
    expect(getStatusBadgeVariant('completed')).toBe('success');
  });

  it('returns "destructive" for failed status', () => {
    expect(getStatusBadgeVariant('failed')).toBe('destructive');
  });

  it('returns "default" for running status', () => {
    expect(getStatusBadgeVariant('running')).toBe('default');
  });

  it('returns "warning" for timed_out status', () => {
    expect(getStatusBadgeVariant('timed_out')).toBe('warning');
  });

  it('returns "warning" for retrying status', () => {
    expect(getStatusBadgeVariant('retrying')).toBe('warning');
  });

  it('returns "secondary" for pending status', () => {
    expect(getStatusBadgeVariant('pending')).toBe('secondary');
  });

  it('returns "secondary" for unknown status', () => {
    expect(getStatusBadgeVariant('unknown' as ExecutionStatus)).toBe('secondary');
  });
});

describe('getStatusColor', () => {
  it('returns green for completed status', () => {
    expect(getStatusColor('completed')).toBe('text-green-500');
  });

  it('returns red for failed status', () => {
    expect(getStatusColor('failed')).toBe('text-red-500');
  });

  it('returns blue for running status', () => {
    expect(getStatusColor('running')).toBe('text-blue-500');
  });

  it('returns yellow for paused status', () => {
    expect(getStatusColor('paused')).toBe('text-yellow-500');
  });

  it('returns yellow for retrying status', () => {
    expect(getStatusColor('retrying')).toBe('text-yellow-500');
  });

  it('returns orange for timed_out status', () => {
    expect(getStatusColor('timed_out')).toBe('text-orange-500');
  });

  it('returns gray for unknown status', () => {
    expect(getStatusColor('unknown' as ExecutionStatus)).toBe('text-gray-400');
  });
});

describe('STATUS_ICON_CONFIG', () => {
  it('has configuration for all status types', () => {
    const statuses: ExecutionStatus[] = [
      'pending',
      'queued',
      'running',
      'paused',
      'completed',
      'failed',
      'cancelled',
      'retrying',
      'timed_out',
    ];

    statuses.forEach((status) => {
      expect(STATUS_ICON_CONFIG[status]).toBeDefined();
      expect(STATUS_ICON_CONFIG[status]).toHaveProperty('color');
      expect(STATUS_ICON_CONFIG[status]).toHaveProperty('bgColor');
    });
  });

  it('marks running status as animated', () => {
    expect(STATUS_ICON_CONFIG.running.animate).toBe(true);
  });

  it('does not mark completed status as animated', () => {
    expect(STATUS_ICON_CONFIG.completed.animate).toBeUndefined();
  });

  it('uses consistent color scheme patterns', () => {
    expect(STATUS_ICON_CONFIG.completed.color).toContain('green');
    expect(STATUS_ICON_CONFIG.failed.color).toContain('red');
    expect(STATUS_ICON_CONFIG.running.color).toContain('blue');
  });
});
