/**
 * OutputFieldsEditor - Visual editor for defining agent output fields.
 * Allows non-technical users to specify structured output without writing JSON schemas.
 */
import { memo, useCallback } from 'react';
import { Plus, Trash2, ListChecks } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { cn } from '../../lib/utils';
import type { OutputFieldConfig } from '../../types/blocks';

interface OutputFieldsEditorProps {
  fields: OutputFieldConfig[];
  onChange: (fields: OutputFieldConfig[]) => void;
}

const FIELD_TYPES: { value: OutputFieldConfig['type']; label: string; hint: string }[] = [
  { value: 'text', label: '텍스트', hint: '문장, 문단, 설명 등' },
  { value: 'number', label: '숫자', hint: '점수, 횟수, 금액 등' },
  { value: 'boolean', label: '예/아니오', hint: '판단 결과' },
  { value: 'list', label: '목록', hint: '여러 항목의 배열' },
];

export const OutputFieldsEditor = memo(function OutputFieldsEditor({
  fields,
  onChange,
}: OutputFieldsEditorProps) {
  const handleAdd = useCallback(() => {
    onChange([...fields, { name: '', type: 'text' }]);
  }, [fields, onChange]);

  const handleRemove = useCallback(
    (index: number) => {
      onChange(fields.filter((_, i) => i !== index));
    },
    [fields, onChange]
  );

  const handleFieldChange = useCallback(
    (index: number, updates: Partial<OutputFieldConfig>) => {
      onChange(
        fields.map((f, i) => (i === index ? { ...f, ...updates } : f))
      );
    },
    [fields, onChange]
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium flex items-center gap-1.5">
          <ListChecks className="w-3.5 h-3.5" />
          출력 형식
        </label>
        <Button
          variant="outline"
          size="sm"
          onClick={handleAdd}
          className="h-6 text-xs"
          aria-label="Add output field"
        >
          <Plus className="w-3 h-3 mr-1" />
          필드 추가
        </Button>
      </div>

      {fields.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          출력 필드를 정의하면 Agent가 구조화된 JSON으로 응답합니다.
          텍스트 필드는 문장이나 문단도 지원합니다.
          다운스트림 노드에서 각 필드를 개별적으로 활용할 수 있습니다.
        </p>
      ) : (
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div
              key={index}
              className="space-y-1"
              data-testid={`output-field-${index}`}
            >
              <div className="flex items-center gap-1.5">
                <Input
                  value={field.name}
                  onChange={(e) =>
                    handleFieldChange(index, { name: e.target.value })
                  }
                  placeholder="필드명 (예: 평가근거, score)"
                  className="h-7 text-xs flex-1"
                  aria-label="Field name"
                />
                <Select
                  value={field.type}
                  onValueChange={(v) =>
                    handleFieldChange(index, {
                      type: v as OutputFieldConfig['type'],
                    })
                  }
                >
                  <SelectTrigger className="h-7 text-xs w-24" aria-label="Field type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FIELD_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value} title={t.hint}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={() => handleRemove(index)}
                  aria-label="Remove field"
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
              <Input
                value={field.description || ''}
                onChange={(e) => handleFieldChange(index, { description: e.target.value })}
                placeholder="설명 (선택, 예: 1-10 사이의 평가 점수)"
                className="h-6 text-[11px] text-muted-foreground"
                aria-label="Field description"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
