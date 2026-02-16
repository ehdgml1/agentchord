/**
 * Data Flow Panel Component
 *
 * Visualizes data flow between workflow nodes during execution,
 * showing how data passes through edges and transforms between steps.
 */

import { memo, useMemo } from 'react';
import { ArrowRight } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useCurrentExecution } from '../../stores/executionStore';
import { Badge } from '../ui/badge';

/**
 * Data flow entry representing one edge's data transfer
 */
interface DataFlowEntry {
  edgeId: string;
  sourceName: string;
  targetName: string;
  output: unknown;
  status: string;
}

/**
 * Get status badge variant based on execution status
 */
function getStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'completed':
      return 'default';
    case 'failed':
      return 'destructive';
    case 'running':
      return 'default';
    default:
      return 'secondary';
  }
}

/**
 * Format output data for display
 */
function formatOutput(output: unknown): string {
  if (!output) return '';

  if (typeof output === 'string') {
    return output.length > 200 ? output.substring(0, 200) + '...' : output;
  }

  const jsonString = JSON.stringify(output, null, 2);
  return jsonString.length > 200 ? jsonString.substring(0, 200) + '...' : jsonString;
}

/**
 * Data Flow Panel Component
 */
export const DataFlowPanel = memo(function DataFlowPanel() {
  const { nodes, edges } = useWorkflowStore(
    useShallow(s => ({
      nodes: s.nodes,
      edges: s.edges,
    }))
  );
  const currentExecution = useCurrentExecution();

  /**
   * Build data flow entries from current execution
   */
  const dataFlowEntries = useMemo<DataFlowEntry[]>(() => {
    if (!currentExecution?.nodeExecutions) return [];

    // Pre-build maps for O(1) lookups
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const execMap = new Map(currentExecution.nodeExecutions.map((ne) => [ne.nodeId, ne]));

    return edges.map((edge) => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      const sourceExec = execMap.get(edge.source);

      // Get node name from various possible data properties
      // Using type-safe property access with fallbacks
      const getNodeName = (node: typeof sourceNode): string => {
        if (!node) return '';
        const data = node.data as Record<string, unknown>;
        return String(data.name || data.toolName || data.label || '');
      };

      const sourceName = getNodeName(sourceNode) || edge.source;
      const targetName = getNodeName(targetNode) || edge.target;

      return {
        edgeId: edge.id,
        sourceName: String(sourceName),
        targetName: String(targetName),
        output: sourceExec?.output,
        status: (sourceExec?.status || 'pending') as string,
      };
    });
  }, [nodes, edges, currentExecution]);

  return (
    <div className="p-4 space-y-3 h-full overflow-y-auto">
      <div className="space-y-1">
        <h3 className="font-semibold text-sm">Data Flow</h3>
        <p className="text-xs text-muted-foreground">
          Track how data flows between workflow nodes
        </p>
      </div>

      {dataFlowEntries.length === 0 ? (
        <div className="flex items-center justify-center py-8">
          <p className="text-xs text-muted-foreground text-center">
            Run a workflow to see data flow visualization
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {dataFlowEntries.map((entry) => (
            <div
              key={entry.edgeId}
              className="border rounded-lg p-3 space-y-2 bg-card"
            >
              {/* Flow header */}
              <div className="flex items-center gap-2 text-xs">
                <Badge variant="outline" className="font-mono text-xs">
                  {entry.sourceName}
                </Badge>
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                <Badge variant="outline" className="font-mono text-xs">
                  {entry.targetName}
                </Badge>
                <Badge
                  variant={getStatusVariant(entry.status)}
                  className="ml-auto text-xs"
                >
                  {entry.status}
                </Badge>
              </div>

              {/* Output data */}
              {entry.output && entry.status === 'completed' && (
                <div className="space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">
                    Output Data:
                  </div>
                  <pre className="bg-muted p-2 rounded text-xs overflow-auto max-h-24 font-mono">
                    {formatOutput(entry.output)}
                  </pre>
                </div>
              )}

              {/* Pending state */}
              {entry.status === 'pending' && (
                <div className="text-xs text-muted-foreground italic">
                  Waiting for execution...
                </div>
              )}

              {/* Running state */}
              {entry.status === 'running' && (
                <div className="text-xs text-muted-foreground italic">
                  Currently executing...
                </div>
              )}

              {/* Failed state */}
              {entry.status === 'failed' && (
                <div className="text-xs text-destructive italic">
                  Execution failed
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
