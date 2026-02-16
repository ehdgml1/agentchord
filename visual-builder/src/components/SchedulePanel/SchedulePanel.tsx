/**
 * SchedulePanel component for Visual Builder
 *
 * Panel to manage workflow schedules including creation,
 * enabling/disabling, and deletion.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  Plus,
  Trash2,
  Calendar,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { CronInput } from './CronInput';
import { useScheduleStore } from '../../stores/scheduleStore';
import {
  cronToHuman,
  formatNextRun,
  getLocalTimezone,
  COMMON_TIMEZONES,
  validateCron,
} from '../../lib/cronUtils';
import type { Schedule } from '../../types/schedule';
import { useConfirm } from '../ui/confirm-dialog';

interface SchedulePanelProps {
  /** Workflow ID to manage schedules for */
  workflowId: string;
}

export function SchedulePanel({ workflowId }: SchedulePanelProps) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newExpression, setNewExpression] = useState('0 9 * * *');
  const [newInput, setNewInput] = useState('');
  const [newTimezone, setNewTimezone] = useState(getLocalTimezone());
  const confirm = useConfirm();

  const {
    schedules,
    loading,
    error,
    fetchSchedules,
    createSchedule,
    deleteSchedule,
    toggleSchedule,
    clearError,
  } = useScheduleStore();

  // Fetch schedules on mount or workflow change
  useEffect(() => {
    fetchSchedules(workflowId);
  }, [workflowId, fetchSchedules]);

  // Handle creating a new schedule
  const handleCreate = useCallback(async () => {
    const validation = validateCron(newExpression);
    if (!validation.valid) return;

    try {
      await createSchedule({
        workflowId,
        expression: newExpression,
        input: newInput || undefined,
        timezone: newTimezone,
      });
      setIsCreateOpen(false);
      setNewExpression('0 9 * * *');
      setNewInput('');
    } catch {
      // Error is handled by the store
    }
  }, [workflowId, newExpression, newInput, newTimezone, createSchedule]);

  // Handle deleting a schedule
  const handleDelete = useCallback(
    async (id: string) => {
      const ok = await confirm({
        title: 'Delete Schedule',
        description: 'Are you sure you want to delete this schedule? This action cannot be undone.',
        confirmText: 'Delete',
        variant: 'destructive',
      });
      if (ok) await deleteSchedule(id);
    },
    [deleteSchedule, confirm]
  );

  // Handle toggling a schedule
  const handleToggle = useCallback(
    async (id: string) => {
      await toggleSchedule(id);
    },
    [toggleSchedule]
  );

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-purple-600" />
          <h2 className="font-semibold">Schedules</h2>
        </div>
        <Button size="sm" onClick={() => setIsCreateOpen(true)}>
          <Plus className="w-4 h-4 mr-1" />
          Add
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="text-sm text-red-700 flex-1">{error}</span>
          <Button variant="ghost" size="sm" onClick={clearError}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Schedule List */}
      <div className="flex-1 overflow-auto p-4">
        {loading && schedules.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : schedules.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No schedules configured</p>
            <p className="text-sm">
              Add a schedule to run this workflow automatically
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {schedules.map((schedule) => (
              <ScheduleItem
                key={schedule.id}
                schedule={schedule}
                onToggle={() => handleToggle(schedule.id)}
                onDelete={() => handleDelete(schedule.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Schedule Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create Schedule</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <CronInput
              value={newExpression}
              onChange={setNewExpression}
              timezone={newTimezone}
            />

            <div className="space-y-1.5">
              <Label htmlFor="timezone">Timezone</Label>
              <Select value={newTimezone} onValueChange={setNewTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {COMMON_TIMEZONES.map((tz) => (
                    <SelectItem key={tz} value={tz}>
                      {tz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="input">Input (optional)</Label>
              <Textarea
                id="input"
                value={newInput}
                onChange={(e) => setNewInput(e.target.value)}
                placeholder="Workflow input data..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={loading || !validateCron(newExpression).valid}
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Create Schedule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/**
 * Individual schedule item component
 */
interface ScheduleItemProps {
  schedule: Schedule;
  onToggle: () => void;
  onDelete: () => void;
}

function ScheduleItem({ schedule, onToggle, onDelete }: ScheduleItemProps) {
  const humanReadable = cronToHuman(schedule.expression);
  const nextRun = schedule.nextRunAt
    ? formatNextRun(new Date(schedule.nextRunAt), schedule.timezone)
    : 'Not scheduled';
  const lastRun = schedule.lastRunAt
    ? formatNextRun(new Date(schedule.lastRunAt), schedule.timezone)
    : 'Never';

  return (
    <div className="border rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Switch
            checked={schedule.enabled}
            onCheckedChange={onToggle}
            aria-label="Toggle schedule"
          />
          <span
            className={`text-sm font-medium ${
              schedule.enabled ? '' : 'text-muted-foreground'
            }`}
          >
            {humanReadable}
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          className="h-8 w-8 text-muted-foreground hover:text-red-500"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <code className="block text-xs bg-gray-100 rounded px-2 py-1 font-mono">
        {schedule.expression}
      </code>

      <div className="flex gap-4 text-xs text-muted-foreground">
        <div>
          <span className="font-medium">Next:</span> {nextRun}
        </div>
        <div>
          <span className="font-medium">Last:</span> {lastRun}
        </div>
      </div>

      <div className="text-xs text-muted-foreground">
        Timezone: {schedule.timezone}
      </div>
    </div>
  );
}
