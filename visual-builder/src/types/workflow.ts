/**
 * Workflow type definitions for Visual Builder
 *
 * This module defines the workflow structure, including nodes, edges,
 * and serialization formats.
 */

import type { Node, Edge } from '@xyflow/react';
import type { BlockType, BlockData } from './blocks';

/**
 * Workflow node extending React Flow Node
 *
 * Represents a single block in the workflow canvas with its
 * configuration data and visual properties.
 */
export interface WorkflowNode extends Node {
  /** Block type identifier */
  type: BlockType;
  /** Block configuration and display data */
  data: BlockData & {
    /** Optional display label override */
    label?: string;
  };
}

/**
 * Workflow edge extending React Flow Edge
 *
 * Represents a connection between two nodes in the workflow,
 * with optional metadata for conditional routing.
 */
export interface WorkflowEdge extends Edge {
  /** Optional edge metadata */
  data?: {
    /** Display label for the edge */
    label?: string;
    /** For conditional edges, which branch this represents */
    condition?: 'true' | 'false';
  };
}

/**
 * Complete workflow definition
 *
 * Contains all information needed to save, load, and execute
 * a visual workflow.
 */
export interface Workflow {
  /** Unique identifier for this workflow */
  id: string;
  /** Human-readable workflow name */
  name: string;
  /** Optional workflow description */
  description?: string;
  /** All nodes in the workflow */
  nodes: WorkflowNode[];
  /** All edges connecting nodes */
  edges: WorkflowEdge[];
  /** ISO timestamp of workflow creation */
  createdAt: string;
  /** ISO timestamp of last modification */
  updatedAt: string;
}

