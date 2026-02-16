/**
 * Schedule type definitions for Visual Builder
 *
 * This module defines schedule structures for workflow automation
 * including cron-based schedules and their management.
 */

/**
 * Complete schedule definition
 *
 * Represents a scheduled trigger for a workflow execution.
 */
export interface Schedule {
  /** Unique identifier for this schedule */
  id: string;
  /** ID of the workflow this schedule triggers */
  workflowId: string;
  /** Schedule type - currently only cron is supported */
  type: 'cron';
  /** Cron expression (e.g., "0 9 * * *") */
  expression: string;
  /** Input data to pass to the workflow */
  input: Record<string, unknown>;
  /** Timezone for the schedule (e.g., "America/New_York") */
  timezone: string;
  /** Whether the schedule is currently active */
  enabled: boolean;
  /** ISO timestamp of last execution, null if never run */
  lastRunAt: string | null;
  /** ISO timestamp of next scheduled execution, null if disabled */
  nextRunAt: string | null;
  /** ISO timestamp of schedule creation */
  createdAt: string;
}

/**
 * Data for creating a new schedule
 */
export interface CreateScheduleData {
  /** ID of the workflow to schedule */
  workflowId: string;
  /** Cron expression */
  expression: string;
  /** Optional input data for the workflow */
  input?: string;
  /** Optional timezone (defaults to user's local timezone) */
  timezone?: string;
}

/**
 * Request payload for creating a schedule via API
 */
export interface ScheduleCreateRequest {
  workflowId: string;
  expression: string;
  input?: string;
  timezone?: string;
}

/**
 * Data for updating an existing schedule
 */
export interface UpdateScheduleData {
  /** New cron expression */
  expression?: string;
  /** New input data */
  input?: string;
  /** New timezone */
  timezone?: string;
  /** Enable/disable the schedule */
  enabled?: boolean;
}
