/**
 * InputTemplateEditor - Editable input template with upstream field discovery.
 *
 * Shows a textarea for {{nodeId.field}} template expressions.
 * Discovers upstream nodes' outputFields and displays them as clickable badges.
 * Only visible when the node has incoming edges.
 */

import { memo, useCallback, useMemo, useRef } from 'react';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useShallow } from 'zustand/react/shallow';
import type { OutputFieldConfig } from '../../types/blocks';

interface UpstreamField {
  /** Template expression, e.g. "agent-classifier.query" */
  expression: string;
  /** Display label, e.g. "query (classifier)" */
  label: string;
  /** Field type from outputFields */
  type: string;
  /** Node name for display grouping */
  nodeName: string;
  /** Badge style variant: 'input' (green), 'direct' (blue), 'ancestor' (purple) */
  variant?: 'input' | 'direct' | 'ancestor';
}

interface InputTemplateEditorProps {
  /** Current node's ID */
  nodeId: string;
  /** Current inputTemplate value */
  value: string;
  /** Called when template value changes */
  onChange: (value: string) => void;
}

export const InputTemplateEditor = memo(function InputTemplateEditor({
  nodeId,
  value,
  onChange,
}: InputTemplateEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Get nodes and edges from store
  const { nodes, edges } = useWorkflowStore(
    useShallow((s) => ({ nodes: s.nodes, edges: s.edges }))
  );

  // Check if this node has incoming edges
  const hasIncomingEdges = useMemo(
    () => edges.some((e) => e.target === nodeId),
    [edges, nodeId]
  );

  // Discover upstream nodes' output fields (all ancestors via BFS)
  const upstreamFields = useMemo<UpstreamField[]>(() => {
    const fields: UpstreamField[] = [];

    // Add {{input}} badge for original workflow input
    if (edges.some((e) => e.target === nodeId)) {
      fields.push({
        expression: 'input',
        label: '원본 입력 (사용자 질문)',
        type: 'text',
        nodeName: 'Workflow',
        variant: 'input',
      });
    }

    // Find direct parents (1-hop)
    const directParentIds = new Set(
      edges.filter((e) => e.target === nodeId).map((e) => e.source)
    );

    // BFS to discover ALL upstream nodes (ancestors), not just direct parents
    const allUpstreamIds: string[] = [];
    const visited = new Set<string>();
    const queue: string[] = edges
      .filter((e) => e.target === nodeId)
      .map((e) => e.source);

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (visited.has(current)) continue;
      visited.add(current);
      allUpstreamIds.push(current);

      // Add parents of current node
      edges
        .filter((e) => e.target === current)
        .forEach((e) => {
          if (!visited.has(e.source)) {
            queue.push(e.source);
          }
        });
    }

    // Process all discovered upstream nodes
    for (const upstreamId of allUpstreamIds) {
      const upstreamNode = nodes.find((n) => n.id === upstreamId);
      if (!upstreamNode?.data) continue;

      const data = upstreamNode.data as Record<string, unknown>;
      const outputFields = data.outputFields as OutputFieldConfig[] | undefined;
      const nodeName = (data.name as string) || upstreamId;
      const variant = directParentIds.has(upstreamId) ? 'direct' : 'ancestor';

      if (outputFields && outputFields.length > 0) {
        // Show individual field badges when outputFields is defined
        for (const f of outputFields) {
          if (!f.name) continue;
          fields.push({
            expression: `${upstreamId}.${f.name}`,
            label: `${f.name} (${nodeName})`,
            type: f.type,
            nodeName,
            variant,
          });
        }
      } else {
        // Only show generic .output reference when no outputFields
        fields.push({
          expression: `${upstreamId}.output`,
          label: `output (${nodeName})`,
          type: 'text',
          nodeName,
          variant,
        });
      }
    }

    return fields;
  }, [nodeId, nodes, edges]);

  // Insert template expression at cursor position
  const handleFieldClick = useCallback(
    (expression: string) => {
      const template = `{{${expression}}}`;
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const before = value.slice(0, start);
        const after = value.slice(end);
        const newValue = before + template + after;
        onChange(newValue);
        // Restore cursor position after the inserted template
        requestAnimationFrame(() => {
          textarea.focus();
          const newPos = start + template.length;
          textarea.setSelectionRange(newPos, newPos);
        });
      } else {
        // Fallback: append
        onChange(value ? `${value} ${template}` : template);
      }
    },
    [value, onChange]
  );

  const handleTextareaChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
    },
    [onChange]
  );

  // Badge style helper
  const getBadgeStyle = (variant: UpstreamField['variant']) => {
    switch (variant) {
      case 'input':
        return 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800 dark:hover:bg-green-900';
      case 'direct':
        return 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800 dark:hover:bg-blue-900';
      case 'ancestor':
        return 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800 dark:hover:bg-purple-900';
      default:
        return 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800 dark:hover:bg-blue-900';
    }
  };

  // Don't render if no incoming edges
  if (!hasIncomingEdges) return null;

  return (
    <div className="space-y-2 border-t pt-4">
      <Label htmlFor="inputTemplate">입력 템플릿</Label>

      {/* Upstream field badges */}
      {upstreamFields.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">
            사용 가능한 필드:
          </p>
          <div className="flex flex-wrap gap-1">
            {upstreamFields.map((field) => (
              <button
                key={field.expression}
                type="button"
                onClick={() => handleFieldClick(field.expression)}
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono transition-colors ${getBadgeStyle(field.variant)}`}
                title={`{{${field.expression}}}`}
              >
                {field.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <Textarea
        ref={textareaRef}
        id="inputTemplate"
        value={value}
        onChange={handleTextareaChange}
        placeholder="예: {{agent-classifier.query}} 에 대해 검색하세요"
        rows={3}
        className="font-mono text-xs"
      />
      <p className="text-xs text-muted-foreground">
        상위 노드의 출력 필드를 참조할 수 있습니다
      </p>
    </div>
  );
});
