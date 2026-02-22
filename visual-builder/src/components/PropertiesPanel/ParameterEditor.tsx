import { memo, useCallback, useId, useMemo } from 'react';
import { X } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { TemplateVarSelector } from './TemplateVarSelector';

export interface ParameterEditorProps {
  schema: Record<string, any>;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  templateVars?: { label: string; value: string }[];
}

interface FieldProps {
  name: string;
  schema: Record<string, any>;
  value: unknown;
  onChange: (value: unknown) => void;
  required?: boolean;
  templateVars?: { label: string; value: string }[];
}

interface ArrayItemProps {
  index: number;
  itemSchema: Record<string, any>;
  value: unknown;
  onChange: (value: unknown) => void;
  onRemove: () => void;
  templateVars?: { label: string; value: string }[];
}

const ArrayItem = memo(function ArrayItem({
  index,
  itemSchema,
  value,
  onChange,
  onRemove,
  templateVars,
}: ArrayItemProps) {
  const renderItemField = useCallback(() => {
    const itemType = itemSchema.type;

    if (itemType === 'object' && itemSchema.properties) {
      return (
        <div className="space-y-2">
          {Object.entries(itemSchema.properties).map(([propName, propSchema]: [string, any]) => {
            const propValue = (value as Record<string, unknown>)?.[propName];
            const isRequired = itemSchema.required?.includes(propName);

            return (
              <Field
                key={propName}
                name={propName}
                schema={propSchema}
                value={propValue}
                onChange={(newVal) => {
                  onChange({
                    ...(value as Record<string, unknown> || {}),
                    [propName]: newVal,
                  });
                }}
                required={isRequired}
                templateVars={templateVars}
              />
            );
          })}
        </div>
      );
    }

    if (itemType === 'string') {
      const resolvedLabel = templateVars?.find(v => v.value === value)?.label ?? null;

      if (resolvedLabel) {
        return (
          <div className="space-y-1">
            <div className="flex gap-1 items-center">
              <div className="flex-1 min-w-0 flex items-center gap-1 h-8 px-2 rounded-md border bg-blue-50 border-blue-200 overflow-hidden">
                <span className="text-sm font-mono text-blue-700 dark:text-blue-300 truncate">{resolvedLabel}</span>
                <button
                  type="button"
                  onClick={() => onChange('')}
                  className="ml-auto text-blue-400 hover:text-blue-600 shrink-0"
                  aria-label="변수 제거"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
              {templateVars && templateVars.length > 0 && (
                <TemplateVarSelector
                  templateVars={templateVars}
                  onSelect={(v) => onChange(v)}
                />
              )}
            </div>
          </div>
        );
      }

      const hasTemplate = typeof value === 'string' && value.includes('{{');
      return (
        <div className="space-y-2">
          <div className="flex gap-1">
            <Input
              type="text"
              value={(value as string) || ''}
              onChange={(e) => onChange(e.target.value)}
              className={`flex-1 ${hasTemplate ? 'font-mono' : ''}`}
            />
            {templateVars && templateVars.length > 0 && (
              <TemplateVarSelector
                templateVars={templateVars}
                onSelect={(v) => onChange(v)}
              />
            )}
          </div>
          {hasTemplate && (
            <p className="text-xs text-muted-foreground">
              템플릿 사용 가능: {'{{'} 노드ID.필드 {'}}'}
            </p>
          )}
        </div>
      );
    }

    if (itemType === 'number' || itemType === 'integer') {
      return (
        <Input
          type="number"
          step={itemType === 'integer' ? 1 : 'any'}
          value={(value as number) || 0}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      );
    }

    return (
      <Input
        type="text"
        value={String(value || '')}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }, [itemSchema, value, onChange, templateVars]);

  return (
    <div className="rounded border bg-muted/30 p-3 mb-2">
      <div className="flex items-start justify-between gap-2 mb-2">
        <Badge variant="outline">[{index + 1}]</Badge>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRemove}
          className="text-red-500 hover:text-red-700 h-6 px-2"
        >
          삭제
        </Button>
      </div>
      {renderItemField()}
    </div>
  );
});

const ArrayFieldEditor = memo(function ArrayFieldEditor({
  name,
  schema,
  value,
  onChange,
  required,
  templateVars,
}: FieldProps) {
  const arrayValue = Array.isArray(value) ? value : [];
  const itemSchema = schema.items || { type: 'string' };

  const handleAddItem = useCallback(() => {
    const newItem = itemSchema.type === 'object' ? {} : '';
    onChange([...arrayValue, newItem]);
  }, [arrayValue, itemSchema, onChange]);

  const handleRemoveItem = useCallback((index: number) => {
    onChange(arrayValue.filter((_, i) => i !== index));
  }, [arrayValue, onChange]);

  const handleUpdateItem = useCallback((index: number, newValue: unknown) => {
    const updated = [...arrayValue];
    updated[index] = newValue;
    onChange(updated);
  }, [arrayValue, onChange]);

  return (
    <div className="space-y-2">
      <Label className="font-medium text-sm">
        {schema.title || name}
        {required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      {schema.description && (
        <p className="text-xs text-muted-foreground">{schema.description}</p>
      )}
      <div className="border rounded p-3">
        {arrayValue.map((item, index) => (
          <ArrayItem
            key={index}
            index={index}
            itemSchema={itemSchema}
            value={item}
            onChange={(newVal) => handleUpdateItem(index, newVal)}
            onRemove={() => handleRemoveItem(index)}
            templateVars={templateVars}
          />
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddItem}
          className="w-full border-dashed text-muted-foreground hover:text-foreground"
        >
          + 항목 추가
        </Button>
      </div>
    </div>
  );
});

const ObjectFieldEditor = memo(function ObjectFieldEditor({
  name,
  schema,
  value,
  onChange,
  required,
  templateVars,
}: FieldProps) {
  const objectValue = (value as Record<string, unknown>) || {};
  const properties = schema.properties || {};

  return (
    <div className="space-y-3">
      <Label className="font-medium text-sm">
        {schema.title || name}
        {required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      {schema.description && (
        <p className="text-xs text-muted-foreground">{schema.description}</p>
      )}
      <div className="border rounded p-3 space-y-3">
        {Object.entries(properties).map(([propName, propSchema]: [string, any]) => {
          const propValue = objectValue[propName];
          const isRequired = schema.required?.includes(propName);

          return (
            <Field
              key={propName}
              name={propName}
              schema={propSchema}
              value={propValue}
              onChange={(newVal) => {
                onChange({
                  ...objectValue,
                  [propName]: newVal,
                });
              }}
              required={isRequired}
              templateVars={templateVars}
            />
          );
        })}
      </div>
    </div>
  );
});

const Field = memo(function Field({
  name,
  schema,
  value,
  onChange,
  required,
  templateVars,
}: FieldProps) {
  const fieldId = useId();
  const fieldType = schema.type;
  const hasEnum = Array.isArray(schema.enum) && schema.enum.length > 0;

  if (fieldType === 'array') {
    return (
      <ArrayFieldEditor
        name={name}
        schema={schema}
        value={value}
        onChange={onChange}
        required={required}
        templateVars={templateVars}
      />
    );
  }

  if (fieldType === 'object') {
    return (
      <ObjectFieldEditor
        name={name}
        schema={schema}
        value={value}
        onChange={onChange}
        required={required}
        templateVars={templateVars}
      />
    );
  }

  if (fieldType === 'boolean') {
    return (
      <div className="flex items-center justify-between">
        <Label className="font-medium text-sm">
          {schema.title || name}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
        />
      </div>
    );
  }

  if (hasEnum) {
    return (
      <div className="space-y-2">
        <Label className="font-medium text-sm">
          {schema.title || name}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        {schema.description && (
          <p className="text-xs text-muted-foreground">{schema.description}</p>
        )}
        <Select
          value={String(value || '')}
          onValueChange={onChange}
        >
          <SelectTrigger>
            <SelectValue placeholder="선택하세요" />
          </SelectTrigger>
          <SelectContent>
            {schema.enum.map((option: string) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (fieldType === 'number' || fieldType === 'integer') {
    return (
      <div className="space-y-2">
        <Label htmlFor={fieldId} className="font-medium text-sm">
          {schema.title || name}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        {schema.description && (
          <p className="text-xs text-muted-foreground">{schema.description}</p>
        )}
        <Input
          id={fieldId}
          type="number"
          step={fieldType === 'integer' ? 1 : 'any'}
          value={(value as number) || 0}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </div>
    );
  }

  const resolvedLabel = useMemo(() => {
    if (!templateVars || typeof value !== 'string') return null;
    const match = templateVars.find(v => v.value === value);
    return match ? match.label : null;
  }, [value, templateVars]);

  if (resolvedLabel) {
    return (
      <div className="space-y-1">
        <Label htmlFor={fieldId} className="font-medium text-sm">
          {schema.title || name}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        {schema.description && (
          <p className="text-xs text-muted-foreground">{schema.description}</p>
        )}
        <div className="flex gap-1 items-center">
          <div className="flex-1 min-w-0 flex items-center gap-1 h-8 px-2 rounded-md border bg-blue-50 border-blue-200 overflow-hidden">
            <span className="text-sm font-mono text-blue-700 dark:text-blue-300 truncate">{resolvedLabel}</span>
            <button
              type="button"
              onClick={() => onChange('')}
              className="ml-auto text-blue-400 hover:text-blue-600 shrink-0"
              aria-label="변수 제거"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          {templateVars && templateVars.length > 0 && (
            <TemplateVarSelector
              templateVars={templateVars}
              onSelect={(v) => onChange(v)}
            />
          )}
        </div>
      </div>
    );
  }

  const hasTemplate = typeof value === 'string' && value.includes('{{');

  return (
    <div className="space-y-2">
      <Label htmlFor={fieldId} className="font-medium text-sm">
        {schema.title || name}
        {required && <span className="text-red-500 ml-1">*</span>}
      </Label>
      {schema.description && (
        <p className="text-xs text-muted-foreground">{schema.description}</p>
      )}
      <div className="flex gap-1">
        <Input
          id={fieldId}
          type="text"
          value={(value as string) || ''}
          onChange={(e) => onChange(e.target.value)}
          className={`flex-1 ${hasTemplate ? 'font-mono' : ''}`}
        />
        {templateVars && templateVars.length > 0 && (
          <TemplateVarSelector
            templateVars={templateVars}
            onSelect={(v) => onChange(v)}
          />
        )}
      </div>
      {hasTemplate && (
        <p className="text-xs text-muted-foreground">
          템플릿 사용 가능: {'{{'} 노드ID.필드 {'}}'}
        </p>
      )}
    </div>
  );
});

export const ParameterEditor = memo(function ParameterEditor({
  schema,
  value,
  onChange,
  templateVars,
}: ParameterEditorProps) {
  const properties = schema.properties || {};
  const required = schema.required || [];

  if (Object.keys(properties).length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4">
        이 도구는 매개변수가 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(properties).map(([name, fieldSchema]: [string, any]) => (
        <Field
          key={name}
          name={name}
          schema={fieldSchema}
          value={value[name]}
          onChange={(newVal) => {
            onChange({
              ...value,
              [name]: newVal,
            });
          }}
          required={required.includes(name)}
          templateVars={templateVars}
        />
      ))}
    </div>
  );
});

export type { ParameterEditorProps };
