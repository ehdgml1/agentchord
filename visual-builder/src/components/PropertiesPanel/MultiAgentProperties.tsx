/**
 * Properties editor for Multi-Agent Team blocks
 *
 * Provides form controls for configuring team name, strategy, max rounds,
 * cost budget, and individual team member agents.
 */

import { memo, useCallback, useMemo } from 'react';
import { Plus, Trash2, ChevronDown, ChevronRight, Sparkles, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { Slider } from '../ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { MODEL_LIST } from '../../constants/models';
import { MCPToolSelector } from './MCPToolSelector';
import { useLLMKeyStatus } from '../../hooks/useLLMKeyStatus';
import type { MultiAgentBlockData, AgentMemberConfig } from '../../types/blocks';
import { TeamTemplateSelector } from './TeamTemplateSelector';
import type { TeamTemplate } from '../../data/teamTemplates';

function getProviderFromModel(modelId: string): string {
  if (modelId.startsWith('gpt-') || modelId.startsWith('o1')) {
    return 'openai';
  } else if (modelId.startsWith('claude-')) {
    return 'anthropic';
  } else if (modelId.startsWith('gemini-')) {
    return 'google';
  } else {
    return 'ollama';
  }
}

interface MultiAgentPropertiesProps {
  data: MultiAgentBlockData;
  onChange: (data: Partial<MultiAgentBlockData>) => void;
}

const STRATEGY_OPTIONS: { value: MultiAgentBlockData['strategy']; label: string }[] = [
  { value: 'coordinator', label: 'Coordinator' },
  { value: 'round_robin', label: 'Round Robin' },
  { value: 'debate', label: 'Debate' },
  { value: 'map_reduce', label: 'Map-Reduce' },
];

const ROLE_OPTIONS: { value: AgentMemberConfig['role']; label: string }[] = [
  { value: 'coordinator', label: 'Coordinator' },
  { value: 'worker', label: 'Worker' },
  { value: 'reviewer', label: 'Reviewer' },
  { value: 'specialist', label: 'Specialist' },
];

function generateMemberId(): string {
  return `member_${crypto.randomUUID()}`;
}

interface ProviderStatusProps {
  modelId: string;
  isProviderConfigured: (provider: string) => boolean;
}

const ProviderStatus = memo(function ProviderStatus({
  modelId,
  isProviderConfigured,
}: ProviderStatusProps) {
  const provider = useMemo(() => getProviderFromModel(modelId), [modelId]);
  const providerConfigured = useMemo(
    () => isProviderConfigured(provider),
    [isProviderConfigured, provider]
  );

  if (providerConfigured) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600">
        <CheckCircle2 className="h-3 w-3" />
        <span>Provider configured</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-yellow-600">
      <AlertTriangle className="h-3 w-3" />
      <span>No API key for {provider}. Set in LLM Settings.</span>
    </div>
  );
});

export const MultiAgentProperties = memo(function MultiAgentProperties({
  data,
  onChange,
}: MultiAgentPropertiesProps) {
  const [expandedMembers, setExpandedMembers] = useState<Set<string>>(new Set());
  const { isProviderConfigured } = useLLMKeyStatus();

  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ name: e.target.value });
    },
    [onChange]
  );

  const handleStrategyChange = useCallback(
    (value: string) => {
      onChange({ strategy: value as MultiAgentBlockData['strategy'] });
    },
    [onChange]
  );

  const handleMaxRoundsChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value > 0) {
        onChange({ maxRounds: value });
      }
    },
    [onChange]
  );

  const handleCostBudgetChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      if (!isNaN(value) && value >= 0) {
        onChange({ costBudget: value });
      }
    },
    [onChange]
  );

  const handleAddMember = useCallback(() => {
    const newMember: AgentMemberConfig = {
      id: generateMemberId(),
      name: '',
      role: 'worker',
      model: 'gpt-4o-mini',
      systemPrompt: '',
      capabilities: [],
      temperature: 0.7,
    };
    onChange({ members: [...(data.members || []), newMember] });
  }, [data.members, onChange]);

  const handleRemoveMember = useCallback(
    (memberId: string) => {
      onChange({
        members: (data.members || []).filter((m) => m.id !== memberId),
      });
      setExpandedMembers((prev) => {
        const next = new Set(prev);
        next.delete(memberId);
        return next;
      });
    },
    [data.members, onChange]
  );

  const handleMemberChange = useCallback(
    (memberId: string, updates: Partial<AgentMemberConfig>) => {
      onChange({
        members: (data.members || []).map((m) =>
          m.id === memberId ? { ...m, ...updates } : m
        ),
      });
    },
    [data.members, onChange]
  );

  const handleApplyTemplate = useCallback(
    (template: TeamTemplate) => {
      onChange({
        name: template.config.name,
        strategy: template.config.strategy,
        maxRounds: template.config.maxRounds,
        costBudget: template.config.costBudget,
        members: template.config.members,
        coordinatorId: undefined, // Reset on template change
      });
    },
    [onChange]
  );

  const toggleMemberExpanded = useCallback((memberId: string) => {
    setExpandedMembers((prev) => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    });
  }, []);

  const members = data.members || [];

  return (
    <div className="space-y-4">
      {/* Team Settings */}
      <div className="space-y-2">
        <Label htmlFor="team-name">Team Name</Label>
        <Input
          id="team-name"
          value={data.name || ''}
          onChange={handleNameChange}
          placeholder="my_team"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="strategy">Strategy</Label>
        <Select value={data.strategy || 'coordinator'} onValueChange={handleStrategyChange}>
          <SelectTrigger id="strategy">
            <SelectValue placeholder="Select strategy" />
          </SelectTrigger>
          <SelectContent>
            {STRATEGY_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Coordinator Selection - only visible for coordinator strategy */}
      {data.strategy === 'coordinator' && members.length > 0 && (
        <div className="space-y-2">
          <Label htmlFor="coordinatorId">Coordinator</Label>
          <Select
            value={data.coordinatorId || '__auto__'}
            onValueChange={(v) => onChange({ coordinatorId: v === '__auto__' ? undefined : v })}
          >
            <SelectTrigger id="coordinatorId">
              <SelectValue placeholder="Auto (first member)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__auto__">Auto (first member)</SelectItem>
              {members.map((m) => (
                <SelectItem key={m.id} value={m.name || m.id}>
                  {m.name || `Unnamed (${m.id.slice(0, 8)})`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            The coordinator delegates tasks to other members
          </p>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="maxRounds">Max Rounds</Label>
        <Input
          id="maxRounds"
          type="number"
          value={data.maxRounds || 10}
          onChange={handleMaxRoundsChange}
          min={1}
          max={100}
          placeholder="10"
        />
        <p className="text-xs text-muted-foreground">
          Maximum collaboration rounds
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="costBudget">Cost Budget (USD)</Label>
        <Input
          id="costBudget"
          type="number"
          value={data.costBudget || 0}
          onChange={handleCostBudgetChange}
          min={0}
          step={0.01}
          placeholder="0"
        />
        <p className="text-xs text-muted-foreground">
          0 for unlimited
        </p>
      </div>

      {/* Consult Toggle */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={data.enableConsult ?? false}
            onChange={(e) => onChange({ enableConsult: e.target.checked })}
            className="rounded border-gray-300"
          />
          Worker 간 Consult 허용
        </label>
        {data.enableConsult && (
          <p className="text-xs text-gray-400 ml-6">
            각 Worker가 실행 중 다른 Worker에게 질문할 수 있습니다
          </p>
        )}
      </div>

      {/* Team Members */}
      <div className="border-t pt-4">
        {members.length === 0 ? (
          <TeamTemplateSelector onSelect={handleApplyTemplate} />
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <Label>Team Members ({members.length})</Label>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAddMember}
                  aria-label="Add member"
                >
                  <Plus className="w-3 h-3 mr-1" />
                  Add
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              {members.map((member) => {
                const isExpanded = expandedMembers.has(member.id);

                return (
                  <div
                    key={member.id}
                    className="border rounded-md p-2"
                    data-testid={`member-${member.id}`}
                  >
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="p-0.5 hover:bg-muted rounded"
                        onClick={() => toggleMemberExpanded(member.id)}
                        aria-label={isExpanded ? 'Collapse member' : 'Expand member'}
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-3 h-3" />
                        ) : (
                          <ChevronRight className="w-3 h-3" />
                        )}
                      </button>
                      <Input
                        value={member.name || ''}
                        onChange={(e) =>
                          handleMemberChange(member.id, { name: e.target.value })
                        }
                        placeholder="Member name"
                        className="h-7 text-xs flex-1"
                        aria-label="Member name"
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleRemoveMember(member.id)}
                        aria-label="Remove member"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>

                    {isExpanded && (
                      <div className="mt-2 space-y-2 pl-5">
                        <div className="space-y-1">
                          <Label className="text-xs" htmlFor={`role-${member.id}`}>Role</Label>
                          <Select
                            value={member.role || 'worker'}
                            onValueChange={(v) =>
                              handleMemberChange(member.id, {
                                role: v as AgentMemberConfig['role'],
                              })
                            }
                          >
                            <SelectTrigger id={`role-${member.id}`} className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ROLE_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                  {opt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs" htmlFor={`model-${member.id}`}>Model</Label>
                          <Select
                            value={member.model || 'gpt-4o-mini'}
                            onValueChange={(v) =>
                              handleMemberChange(member.id, { model: v })
                            }
                          >
                            <SelectTrigger id={`model-${member.id}`} className="h-7 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {MODEL_LIST.map((model) => (
                                <SelectItem key={model.id} value={model.id}>
                                  {model.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <ProviderStatus
                            modelId={member.model || 'gpt-4o-mini'}
                            isProviderConfigured={isProviderConfigured}
                          />
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between">
                            <Label className="text-xs">Temperature</Label>
                            <span className="text-xs text-muted-foreground">
                              {member.temperature?.toFixed(1) || '0.7'}
                            </span>
                          </div>
                          <Slider
                            value={[member.temperature ?? 0.7]}
                            onValueChange={(v) =>
                              handleMemberChange(member.id, { temperature: v[0] })
                            }
                            min={0}
                            max={2}
                            step={0.1}
                          />
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs" htmlFor={`prompt-${member.id}`}>System Prompt</Label>
                          <Textarea
                            id={`prompt-${member.id}`}
                            value={member.systemPrompt || ''}
                            onChange={(e) =>
                              handleMemberChange(member.id, {
                                systemPrompt: e.target.value,
                              })
                            }
                            placeholder="Instructions for this member..."
                            rows={2}
                            className="text-xs"
                          />
                        </div>

                        {/* MCP Tools per member */}
                        <MCPToolSelector
                          selectedTools={member.mcpTools || []}
                          onChange={(tools) => {
                            const updated = data.members.map((m) =>
                              m.id === member.id ? { ...m, mcpTools: tools } : m
                            );
                            onChange({ ...data, members: updated });
                          }}
                        />

                        <div className="space-y-1">
                          <Label className="text-xs" htmlFor={`capabilities-${member.id}`}>Capabilities</Label>
                          <Input
                            id={`capabilities-${member.id}`}
                            value={(member.capabilities || []).join(', ')}
                            onChange={(e) =>
                              handleMemberChange(member.id, {
                                capabilities: e.target.value
                                  .split(',')
                                  .map((c) => c.trim())
                                  .filter((c) => c),
                              })
                            }
                            placeholder="search, code, review"
                            className="h-7 text-xs"
                          />
                          <p className="text-xs text-muted-foreground">
                            Comma-separated list
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Template shortcut */}
            <button
              type="button"
              className="w-full mt-3 py-2 text-xs text-muted-foreground hover:text-primary border border-dashed rounded-md hover:border-primary transition-colors flex items-center justify-center gap-1.5"
              onClick={() => {
                onChange({ members: [] });
              }}
            >
              <Sparkles className="w-3 h-3" />
              Browse Templates
            </button>
          </>
        )}
      </div>
    </div>
  );
});
