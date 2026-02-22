import { useExecutionStore } from '../stores/executionStore';
import type { NodeExecutionStatus } from '../components/Blocks/BaseNode';

/**
 * Hook to get the execution status of a specific node.
 * Returns the status from the execution store, or undefined if not running.
 */
export function useNodeExecutionStatus(nodeId: string): NodeExecutionStatus | undefined {
  return useExecutionStore(s => s.nodeStatuses[nodeId]) as NodeExecutionStatus | undefined;
}
