/**
 * Properties editor for Multi-Agent Team blocks
 *
 * Provides form controls for configuring team name, strategy, max rounds,
 * cost budget, and individual team member agents.
 */

import { memo, useCallback } from 'react';
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
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
import type { MultiAgentBlockData, AgentMemberConfig } from '../../types/blocks';

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
  return `member_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export const MultiAgentProperties = memo(function MultiAgentProperties({
  data,
  onChange,
}: MultiAgentPropertiesProps) {
  const [expandedMembers, setExpandedMembers] = useState<Set<string>>(new Set());

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

      {/* Team Members */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-3">
          <Label>Team Members ({members.length})</Label>
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

        {members.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No members yet. Add agents to your team.
          </p>
        )}

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
      </div>
    </div>
  );
});
