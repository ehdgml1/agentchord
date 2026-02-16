/**
 * Execution type definitions for Visual Builder
 *
 * This module defines execution states, modes, and result structures
 * for workflow runtime operations.
 */

/**
 * Execution status lifecycle states
 */
export type ExecutionStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'retrying'
  | 'timed_out';

/**
 * Execution mode options
 */
export type ExecutionMode = 'full' | 'mock' | 'debug';

/**
 * Workflow trigger types
 */
export type TriggerType = 'manual' | 'cron' | 'webhook';

/**
 * Individual node execution result
 *
 * Tracks the execution state and result of a single node
 * within a workflow execution.
 */
export interface NodeExecution {
  /** ID of the node that was executed */
  nodeId: string;
  /** Current status of this node's execution */
  status: ExecutionStatus;
  /** Input data passed to the node */
  input: unknown;
  /** Output data produced by the node, null if not completed */
  output: unknown | null;
  /** Error message if execution failed, null otherwise */
  error: string | null;
  /** ISO timestamp when node execution started */
  startedAt: string;
  /** ISO timestamp when node execution completed, null if still running */
  completedAt: string | null;
  /** Duration of execution in milliseconds, null if not completed */
  durationMs: number | null;
  /** Number of retry attempts for this node */
  retryCount: number;
}

/**
 * Complete workflow execution record
 *
 * Contains all information about a workflow execution run including
 * metadata, results, and individual node execution states.
 */
export interface Execution {
  /** Unique execution ID */
  id: string;
  /** ID of the workflow that was executed */
  workflowId: string;
  /** Current overall execution status */
  status: ExecutionStatus;
  /** Execution mode used */
  mode: ExecutionMode;
  /** Type of trigger that initiated this execution */
  triggerType: TriggerType;
  /** ID of the trigger if applicable, null for manual triggers */
  triggerId: string | null;
  /** Input data provided to the workflow */
  input: string;
  /** Final output data from the workflow, null if not completed */
  output: unknown | null;
  /** Error message if execution failed, null otherwise */
  error: string | null;
  /** Array of individual node executions */
  nodeExecutions: NodeExecution[];
  /** ISO timestamp when workflow execution started */
  startedAt: string;
  /** ISO timestamp when workflow execution completed, null if still running */
  completedAt: string | null;
  /** Total duration of execution in milliseconds, null if not completed */
  durationMs: number | null;
  /** Total LLM tokens used */
  totalTokens: number | null;
  /** Prompt/input tokens used */
  promptTokens: number | null;
  /** Completion/output tokens used */
  completionTokens: number | null;
  /** Estimated cost in USD */
  estimatedCost: number | null;
  /** LLM model used for execution */
  modelUsed: string | null;
}
