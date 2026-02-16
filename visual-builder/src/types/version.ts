/**
 * Version history and workflow export type definitions
 *
 * This module defines version tracking for workflows and
 * the export/import format for workflow portability.
 */

/**
 * Workflow version snapshot
 *
 * Represents a saved version of a workflow at a point in time.
 * The actual workflow data is loaded separately when restoring.
 */
export interface WorkflowVersion {
  /** Unique version identifier */
  id: string;
  /** Parent workflow ID */
  workflowId: string;
  /** Sequential version number */
  versionNumber: number;
  /** User-provided description of changes */
  message: string;
  /** ISO timestamp of version creation */
  createdAt: string;
}

/**
 * Workflow export format
 *
 * Used for serializing workflows to JSON files with
 * version information for schema evolution.
 */
export interface WorkflowExport {
  /** Export format version for compatibility */
  version: string;
  /** ISO timestamp of export */
  exportedAt: string;
  /** Complete workflow data */
  workflow: {
    name: string;
    description?: string;
    nodes: unknown[];
    edges: unknown[];
  };
}
