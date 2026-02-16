/**
 * Properties editor for Agent blocks
 *
 * Provides form controls for configuring agent name, role, model selection,
 * temperature, and system prompt.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Slider } from '../ui/slider';
import { MODEL_LIST } from '../../constants/models';
import type { AgentBlockData, ModelId } from '../../types/blocks';

interface AgentPropertiesProps {
  data: AgentBlockData;
  onChange: (data: Partial<AgentBlockData>) => void;
}

export const AgentProperties = memo(function AgentProperties({
  data,
  onChange,
}: AgentPropertiesProps) {
  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ name: e.target.value });
    },
    [onChange]
  );

  const handleRoleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ role: e.target.value });
    },
    [onChange]
  );

  const handleModelChange = useCallback(
    (value: string) => {
      onChange({ model: value as ModelId });
    },
    [onChange]
  );

  const handleTemperatureChange = useCallback(
    (value: number[]) => {
      onChange({ temperature: value[0] });
    },
    [onChange]
  );

  const handleMaxTokensChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value > 0) {
        onChange({ maxTokens: value });
      }
    },
    [onChange]
  );

  const handlePromptChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange({ systemPrompt: e.target.value });
    },
    [onChange]
  );

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          value={data.name || ''}
          onChange={handleNameChange}
          placeholder="agent_name"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="role">Role</Label>
        <Input
          id="role"
          value={data.role || ''}
          onChange={handleRoleChange}
          placeholder="What does this agent do?"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="model">Model</Label>
        <Select value={data.model} onValueChange={handleModelChange}>
          <SelectTrigger id="model">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {MODEL_LIST.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center gap-2">
                  <span>{model.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({model.provider})
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between">
          <Label>Temperature</Label>
          <span className="text-sm text-muted-foreground">
            {data.temperature?.toFixed(1) || '0.7'}
          </span>
        </div>
        <Slider
          value={[data.temperature || 0.7]}
          onValueChange={handleTemperatureChange}
          min={0}
          max={2}
          step={0.1}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="maxTokens">Max Tokens</Label>
        <Input
          id="maxTokens"
          type="number"
          value={data.maxTokens || 4096}
          onChange={handleMaxTokensChange}
          min={1}
          max={200000}
          placeholder="4096"
        />
        <p className="text-xs text-muted-foreground">
          Maximum tokens the model can generate
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="systemPrompt">System Prompt</Label>
        <Textarea
          id="systemPrompt"
          value={data.systemPrompt || ''}
          onChange={handlePromptChange}
          placeholder="Optional custom instructions..."
          rows={4}
        />
      </div>
    </div>
  );
});
