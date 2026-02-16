/**
 * Tests for SchedulePanel component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SchedulePanel } from './SchedulePanel';
import { useScheduleStore } from '../../stores/scheduleStore';
import type { Schedule } from '../../types/schedule';

// Mock dependencies
vi.mock('../../stores/scheduleStore');

// Create a mock confirm function that can be overridden in tests
const mockConfirmFn = vi.fn().mockResolvedValue(true);
vi.mock('../ui/confirm-dialog', () => ({
  useConfirm: () => mockConfirmFn,
}));
vi.mock('./CronInput', () => ({
  CronInput: ({ value, onChange }: any) => (
    <div>
      <label htmlFor="cron-input">Cron Expression</label>
      <input
        id="cron-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Cron expression"
      />
    </div>
  ),
}));
vi.mock('../../lib/cronUtils', () => ({
  cronToHuman: (expr: string) => `Every day at 9am (${expr})`,
  formatNextRun: (date: Date) => date.toLocaleString(),
  getLocalTimezone: () => 'America/New_York',
  COMMON_TIMEZONES: ['America/New_York', 'Europe/London', 'Asia/Tokyo'],
  validateCron: (expr: string) => ({ valid: expr.length > 0 }),
}));

// Mock UI components
vi.mock('../ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));
vi.mock('../ui/label', () => ({
  Label: ({ children, htmlFor }: any) => <label htmlFor={htmlFor}>{children}</label>,
}));
vi.mock('../ui/switch', () => ({
  Switch: ({ checked, onCheckedChange }: any) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onCheckedChange(e.target.checked)}
      role="switch"
    />
  ),
}));
vi.mock('../ui/textarea', () => ({
  Textarea: (props: any) => <textarea {...props} />,
}));
vi.mock('../ui/select', () => ({
  Select: ({ value, onValueChange, children }: any) => (
    <select value={value} onChange={(e) => onValueChange(e.target.value)}>
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: any) => <>{children}</>,
  SelectValue: () => null,
  SelectContent: ({ children }: any) => <>{children}</>,
  SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
}));
vi.mock('../ui/dialog', () => ({
  Dialog: ({ open, children, onOpenChange }: any) => (
    open ? <div role="dialog" data-state="open">{children}</div> : null
  ),
  DialogContent: ({ children }: any) => <div data-testid="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Clock: () => <div>Clock Icon</div>,
  Plus: () => <div>Plus Icon</div>,
  Trash2: () => <div>Trash Icon</div>,
  Calendar: () => <div>Calendar Icon</div>,
  AlertCircle: () => <div>Alert Icon</div>,
  Loader2: () => <div>Loader Icon</div>,
}));

const mockSchedules: Schedule[] = [
  {
    id: 'schedule-1',
    workflowId: 'wf-1',
    expression: '0 9 * * *',
    timezone: 'America/New_York',
    enabled: true,
    nextRunAt: '2024-01-10T09:00:00Z',
    lastRunAt: '2024-01-09T09:00:00Z',
    input: '{"key": "value"}',
  },
  {
    id: 'schedule-2',
    workflowId: 'wf-1',
    expression: '0 0 * * 1',
    timezone: 'Europe/London',
    enabled: false,
    nextRunAt: null,
    lastRunAt: null,
    input: undefined,
  },
];

describe('SchedulePanel', () => {
  const mockWorkflowId = 'wf-1';

  beforeEach(() => {
    vi.clearAllMocks();
    mockConfirmFn.mockResolvedValue(true);
    vi.mocked(useScheduleStore).mockReturnValue({
      schedules: mockSchedules,
      loading: false,
      error: null,
      fetchSchedules: vi.fn(),
      createSchedule: vi.fn().mockResolvedValue(undefined),
      deleteSchedule: vi.fn().mockResolvedValue(undefined),
      toggleSchedule: vi.fn().mockResolvedValue(undefined),
      clearError: vi.fn(),
    });
  });

  describe('Header', () => {
    it('renders header with title', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText('Schedules')).toBeInTheDocument();
    });

    it('renders Add button', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText('Add')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('shows loading spinner when loading and no schedules', () => {
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: [],
        loading: true,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText('Loader Icon')).toBeInTheDocument();
    });

    it('does not show loading when schedules exist', () => {
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: true,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.queryByText('Loader Icon')).not.toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('renders error alert when error exists', () => {
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: 'Failed to fetch schedules',
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText('Failed to fetch schedules')).toBeInTheDocument();
      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('clears error when clicking Dismiss', async () => {
      const user = userEvent.setup();
      const mockClearError = vi.fn();
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: 'Failed to fetch schedules',
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: mockClearError,
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Dismiss'));

      expect(mockClearError).toHaveBeenCalled();
    });
  });

  describe('Schedule List', () => {
    it('renders all schedules', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      // Check for the cron expressions rendered in code blocks
      const codeElements = screen.getAllByText(/0 9 \* \* \*|0 0 \* \* 1/);
      expect(codeElements.length).toBeGreaterThan(0);
    });

    it('shows empty state when no schedules', () => {
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: [],
        loading: false,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText('No schedules configured')).toBeInTheDocument();
      expect(screen.getByText(/Add a schedule to run this workflow automatically/)).toBeInTheDocument();
    });

    it('displays human-readable cron expressions', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      // cronToHuman mock returns "Every day at 9am (expr)"
      const humanReadable = screen.getAllByText(/Every day at 9am/);
      expect(humanReadable.length).toBeGreaterThan(0);
    });

    it('displays timezone for each schedule', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText(/America\/New_York/)).toBeInTheDocument();
      expect(screen.getByText(/Europe\/London/)).toBeInTheDocument();
    });

    it('shows "Never" for null lastRunAt', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText(/Never/)).toBeInTheDocument();
    });

    it('shows "Not scheduled" for null nextRunAt', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getByText(/Not scheduled/)).toBeInTheDocument();
    });
  });

  describe('Toggle Schedule', () => {
    it('renders switch controls for each schedule', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const switches = screen.getAllByRole('switch');
      expect(switches).toHaveLength(2);
    });

    it('reflects enabled state in switch', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const switches = screen.getAllByRole('switch');
      expect(switches[0]).toBeChecked();
      expect(switches[1]).not.toBeChecked();
    });

    it('calls toggleSchedule when clicking switch', async () => {
      const user = userEvent.setup();
      const mockToggle = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: mockToggle,
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const switches = screen.getAllByRole('switch');
      await user.click(switches[0]);

      expect(mockToggle).toHaveBeenCalledWith('schedule-1');
    });
  });

  describe('Delete Schedule', () => {
    it('renders delete button for each schedule', () => {
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(screen.getAllByText('Trash Icon')).toHaveLength(2);
    });

    it('shows confirmation dialog when clicking delete', async () => {
      const user = userEvent.setup();

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const trashIcons = screen.getAllByText('Trash Icon');
      await user.click(trashIcons[0].closest('button')!);

      await waitFor(() => {
        expect(mockConfirmFn).toHaveBeenCalledWith({
          title: 'Delete Schedule',
          description: 'Are you sure you want to delete this schedule? This action cannot be undone.',
          confirmText: 'Delete',
          variant: 'destructive',
        });
      });
    });

    it('calls deleteSchedule when confirmed', async () => {
      const user = userEvent.setup();
      const mockDelete = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: mockDelete,
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const trashIcons = screen.getAllByText('Trash Icon');
      await user.click(trashIcons[0].closest('button')!);

      expect(mockDelete).toHaveBeenCalledWith('schedule-1');
    });

    it('does not delete when cancelled', async () => {
      const user = userEvent.setup();
      const mockDelete = vi.fn();
      mockConfirmFn.mockResolvedValue(false);
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: vi.fn(),
        deleteSchedule: mockDelete,
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      const trashIcons = screen.getAllByText('Trash Icon');
      await user.click(trashIcons[0].closest('button')!);

      await waitFor(() => {
        expect(mockConfirmFn).toHaveBeenCalled();
      });
      expect(mockDelete).not.toHaveBeenCalled();
    });
  });

  describe('Create Schedule Dialog', () => {
    it('opens dialog when clicking Add button', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
      expect(screen.getByRole('heading', { name: 'Create Schedule' })).toBeInTheDocument();
    });

    it('renders cron input in dialog', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      expect(screen.getByLabelText('Cron Expression')).toBeInTheDocument();
    });

    it('renders timezone selector in dialog', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      expect(screen.getByText('Timezone')).toBeInTheDocument();
      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('America/New_York');
    });

    it('renders input textarea in dialog', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      expect(screen.getByPlaceholderText('Workflow input data...')).toBeInTheDocument();
    });

    it('creates schedule with form values', async () => {
      const user = userEvent.setup();
      const mockCreate = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: vi.fn(),
        createSchedule: mockCreate,
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const cronInput = screen.getByLabelText('Cron Expression');
      await user.clear(cronInput);
      await user.type(cronInput, '0 10 * * *');

      const inputTextarea = screen.getByPlaceholderText('Workflow input data...');
      // Use paste instead of type for JSON to avoid special character issues
      await user.click(inputTextarea);
      await user.paste('{"test": true}');

      const createButton = screen.getByRole('button', { name: 'Create Schedule' });
      await user.click(createButton);

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledWith({
          workflowId: 'wf-1',
          expression: '0 10 * * *',
          input: '{"test": true}',
          timezone: 'America/New_York',
        });
      });
    });

    it('closes dialog after successful creation', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const createButton = screen.getByRole('button', { name: 'Create Schedule' });
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('disables create button when cron is invalid', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const cronInput = screen.getByLabelText('Cron Expression');
      await user.clear(cronInput);

      const createButton = screen.getByRole('button', { name: 'Create Schedule' });
      expect(createButton).toBeDisabled();
    });

    it('closes dialog when clicking Cancel', async () => {
      const user = userEvent.setup();
      render(<SchedulePanel workflowId={mockWorkflowId} />);

      await user.click(screen.getByText('Add'));

      await user.click(screen.getByText('Cancel'));

      expect(screen.queryByText('Create Schedule')).not.toBeInTheDocument();
    });
  });

  describe('Data Fetching', () => {
    it('fetches schedules on mount', () => {
      const mockFetch = vi.fn();
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: mockFetch,
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      render(<SchedulePanel workflowId={mockWorkflowId} />);

      expect(mockFetch).toHaveBeenCalledWith('wf-1');
    });

    it('refetches schedules when workflowId changes', () => {
      const mockFetch = vi.fn();
      vi.mocked(useScheduleStore).mockReturnValue({
        schedules: mockSchedules,
        loading: false,
        error: null,
        fetchSchedules: mockFetch,
        createSchedule: vi.fn(),
        deleteSchedule: vi.fn(),
        toggleSchedule: vi.fn(),
        clearError: vi.fn(),
      });

      const { rerender } = render(<SchedulePanel workflowId="wf-1" />);

      expect(mockFetch).toHaveBeenCalledWith('wf-1');

      rerender(<SchedulePanel workflowId="wf-2" />);

      expect(mockFetch).toHaveBeenCalledWith('wf-2');
    });
  });
});
