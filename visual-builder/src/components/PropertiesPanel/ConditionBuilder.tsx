/**
 * ConditionBuilder - Visual stop condition builder for Feedback Loop blocks.
 * Allows non-technical users to define loop exit conditions via dropdowns.
 */
import { memo, useCallback, useMemo, useState } from 'react';
import { Code2, Wand2 } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useShallow } from 'zustand/react/shallow';
import type { OutputFieldConfig } from '../../types/blocks';

interface ConditionBuilderProps {
  nodeId: string;
  value: string;
  onChange: (condition: string) => void;
}

interface FieldOption {
  value: string;       // The expression variable (e.g., "iteration", "input.score")
  label: string;       // Korean display label
  type: 'number' | 'text' | 'boolean';
}

const NUMBER_OPERATORS = [
  { value: '>=', label: '≥ (이상)' },
  { value: '<=', label: '≤ (이하)' },
  { value: '==', label: '= (같음)' },
  { value: '!=', label: '≠ (다름)' },
  { value: '>', label: '> (초과)' },
  { value: '<', label: '< (미만)' },
];

const TEXT_OPERATORS = [
  { value: '==', label: '= (같음)' },
  { value: '!=', label: '≠ (다름)' },
];

const BOOLEAN_OPERATORS = [
  { value: '==', label: '= (같음)' },
];

function getOperatorsForType(type: string) {
  if (type === 'number') return NUMBER_OPERATORS;
  if (type === 'boolean') return BOOLEAN_OPERATORS;
  return TEXT_OPERATORS;
}

function buildExpression(field: string, operator: string, value: string, fieldType: string): string {
  if (!field || !value) return '';
  if (fieldType === 'text') {
    return `${field} ${operator} '${value}'`;
  }
  if (fieldType === 'boolean') {
    return `${field} ${operator} ${value}`;
  }
  return `${field} ${operator} ${value}`;
}

export const ConditionBuilder = memo(function ConditionBuilder({
  nodeId,
  value,
  onChange,
}: ConditionBuilderProps) {
  const [isAdvanced, setIsAdvanced] = useState(false);
  const [selectedField, setSelectedField] = useState('iteration');
  const [selectedOperator, setSelectedOperator] = useState('>=');
  const [conditionValue, setConditionValue] = useState('3');

  // Get connected upstream nodes' output fields from store
  const { nodes, edges } = useWorkflowStore(
    useShallow((s) => ({ nodes: s.nodes, edges: s.edges }))
  );

  // Find upstream Agent nodes that connect TO this feedback loop node
  // We look for nodes that eventually lead to this node via incoming edges
  const availableFields = useMemo<FieldOption[]>(() => {
    const fields: FieldOption[] = [
      { value: 'iteration', label: '반복 횟수', type: 'number' },
    ];

    // Find incoming edges to this feedback loop node
    const incomingNodeIds = edges
      .filter((e) => e.target === nodeId)
      .map((e) => e.source);

    // Get output fields from upstream nodes
    for (const upstreamId of incomingNodeIds) {
      const upstreamNode = nodes.find((n) => n.id === upstreamId);
      if (!upstreamNode?.data) continue;

      const outputFields = (upstreamNode.data as Record<string, unknown>).outputFields as OutputFieldConfig[] | undefined;
      if (outputFields && outputFields.length > 0) {
        const nodeName = (upstreamNode.data as Record<string, unknown>).name as string || '';
        for (const f of outputFields) {
          if (!f.name) continue;
          const fieldType = f.type === 'number' ? 'number' : f.type === 'boolean' ? 'boolean' : 'text';
          const displayLabel = nodeName ? `input.${f.name} (${nodeName})` : `input.${f.name}`;
          fields.push({
            value: `input.${f.name}`,
            label: displayLabel,
            type: fieldType,
          });
        }
      }
    }

    return fields;
  }, [nodeId, nodes, edges]);

  const currentFieldDef = availableFields.find((f) => f.value === selectedField) || availableFields[0];
  const operators = getOperatorsForType(currentFieldDef.type);

  const handleFieldChange = useCallback(
    (field: string) => {
      setSelectedField(field);
      const fieldDef = availableFields.find((f) => f.value === field);
      const ops = getOperatorsForType(fieldDef?.type || 'number');
      setSelectedOperator(ops[0].value);
      // Reset value based on type
      if (fieldDef?.type === 'boolean') {
        setConditionValue('true');
      } else if (fieldDef?.type === 'number') {
        setConditionValue('3');
      } else {
        setConditionValue('');
      }
    },
    [availableFields]
  );

  const handleApply = useCallback(() => {
    const expr = buildExpression(selectedField, selectedOperator, conditionValue, currentFieldDef.type);
    if (expr) {
      onChange(expr);
    }
  }, [selectedField, selectedOperator, conditionValue, currentFieldDef.type, onChange]);

  if (isAdvanced) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="stopCondition">종료 조건</Label>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs gap-1"
            onClick={() => setIsAdvanced(false)}
          >
            <Wand2 className="w-3 h-3" />
            간편 모드
          </Button>
        </div>
        <Textarea
          id="stopCondition"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="iteration >= 3 or input.score >= 80"
          rows={3}
          className="font-mono text-xs"
        />
        <p className="text-xs text-muted-foreground">
          사용 가능 변수: iteration (반복 횟수), input (이전 노드 출력)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>종료 조건</Label>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs gap-1"
          onClick={() => setIsAdvanced(true)}
        >
          <Code2 className="w-3 h-3" />
          고급 모드
        </Button>
      </div>

      <div className="space-y-2 p-3 border rounded-md bg-muted/30">
        <p className="text-xs text-muted-foreground mb-2">
          아래 조건이 충족되면 루프가 종료됩니다
        </p>

        {/* Field selector */}
        <Select value={selectedField} onValueChange={handleFieldChange}>
          <SelectTrigger className="h-8 text-xs" aria-label="Condition field">
            <SelectValue placeholder="필드 선택" />
          </SelectTrigger>
          <SelectContent>
            {availableFields.map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {f.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Operator selector */}
        <Select value={selectedOperator} onValueChange={setSelectedOperator}>
          <SelectTrigger className="h-8 text-xs" aria-label="Condition operator">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {operators.map((op) => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Value input */}
        {currentFieldDef.type === 'boolean' ? (
          <Select value={conditionValue} onValueChange={setConditionValue}>
            <SelectTrigger className="h-8 text-xs" aria-label="Condition value">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">예 (True)</SelectItem>
              <SelectItem value="false">아니오 (False)</SelectItem>
            </SelectContent>
          </Select>
        ) : (
          <Input
            value={conditionValue}
            onChange={(e) => setConditionValue(e.target.value)}
            placeholder={currentFieldDef.type === 'number' ? '값 입력 (예: 80)' : '값 입력'}
            className="h-8 text-xs"
            type={currentFieldDef.type === 'number' ? 'number' : 'text'}
            aria-label="Condition value"
          />
        )}

        {/* Apply button */}
        <Button
          size="sm"
          className="w-full h-8 text-xs"
          onClick={handleApply}
          disabled={!selectedField || !conditionValue}
        >
          조건 적용
        </Button>

        {/* Current condition display */}
        {value && (
          <div className="mt-2 px-2 py-1.5 bg-background rounded text-xs font-mono border">
            {value}
          </div>
        )}
      </div>
    </div>
  );
});
