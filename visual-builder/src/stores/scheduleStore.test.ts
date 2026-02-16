import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useScheduleStore } from './scheduleStore';
import type { Schedule, CreateScheduleData, UpdateScheduleData } from '../types/schedule';

vi.mock('../services/api', () => ({
  api: {
    schedules: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      toggle: vi.fn(),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(msg: string) {
      super(msg);
    }
  },
}));

describe('scheduleStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useScheduleStore.setState({
      schedules: [],
      loading: false,
      error: null,
    });
  });

  describe('Initial state', () => {
    it('should have empty schedules and not loading', () => {
      const state = useScheduleStore.getState();
      expect(state.schedules).toEqual([]);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('fetchSchedules', () => {
    it('should fetch and store schedules on success', async () => {
      const mockSchedules: Schedule[] = [
        {
          id: 's1',
          workflowId: 'wf1',
          cronExpression: '0 0 * * *',
          enabled: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01',
        },
        {
          id: 's2',
          workflowId: 'wf1',
          cronExpression: '0 12 * * *',
          enabled: false,
          createdAt: '2024-01-02',
          updatedAt: '2024-01-02',
        },
      ];

      const { api } = await import('../services/api');
      vi.mocked(api.schedules.list).mockResolvedValue(mockSchedules);

      await useScheduleStore.getState().fetchSchedules('wf1');

      expect(useScheduleStore.getState().schedules).toEqual(mockSchedules);
      expect(useScheduleStore.getState().loading).toBe(false);
      expect(useScheduleStore.getState().error).toBeNull();
    });

    it('should handle error', async () => {
      const { api, ApiError } = await import('../services/api');
      vi.mocked(api.schedules.list).mockRejectedValue(
        new ApiError('Network error')
      );

      await useScheduleStore.getState().fetchSchedules('wf1');

      expect(useScheduleStore.getState().loading).toBe(false);
      expect(useScheduleStore.getState().error).toBe('Network error');
    });

    it('should set loading states correctly', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.schedules.list).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve([]), 50))
      );

      const promise = useScheduleStore.getState().fetchSchedules('wf1');
      expect(useScheduleStore.getState().loading).toBe(true);

      await promise;
      expect(useScheduleStore.getState().loading).toBe(false);
    });
  });

  describe('createSchedule', () => {
    it('should add schedule to array on success', async () => {
      const createData: CreateScheduleData = {
        workflowId: 'wf1',
        cronExpression: '0 0 * * *',
        enabled: true,
      };

      const newSchedule: Schedule = {
        id: 's1',
        ...createData,
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      };

      const { api } = await import('../services/api');
      vi.mocked(api.schedules.create).mockResolvedValue(newSchedule);

      const result = await useScheduleStore.getState().createSchedule(createData);

      expect(result).toEqual(newSchedule);
      expect(useScheduleStore.getState().schedules).toContainEqual(newSchedule);
      expect(useScheduleStore.getState().loading).toBe(false);
    });

    it('should throw on error', async () => {
      const { api, ApiError } = await import('../services/api');
      vi.mocked(api.schedules.create).mockRejectedValue(
        new ApiError('Validation error')
      );

      const createData: CreateScheduleData = {
        workflowId: 'wf1',
        cronExpression: 'invalid',
        enabled: true,
      };

      await expect(
        useScheduleStore.getState().createSchedule(createData)
      ).rejects.toThrow();

      expect(useScheduleStore.getState().error).toBe('Validation error');
    });
  });

  describe('updateSchedule', () => {
    it('should replace schedule in array on success', async () => {
      const existingSchedules: Schedule[] = [
        {
          id: 's1',
          workflowId: 'wf1',
          cronExpression: '0 0 * * *',
          enabled: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01',
        },
        {
          id: 's2',
          workflowId: 'wf1',
          cronExpression: '0 12 * * *',
          enabled: false,
          createdAt: '2024-01-02',
          updatedAt: '2024-01-02',
        },
      ];

      useScheduleStore.setState({ schedules: existingSchedules });

      const updateData: UpdateScheduleData = {
        cronExpression: '0 6 * * *',
      };

      const updatedSchedule: Schedule = {
        ...existingSchedules[0],
        cronExpression: '0 6 * * *',
        updatedAt: '2024-01-03',
      };

      const { api } = await import('../services/api');
      vi.mocked(api.schedules.update).mockResolvedValue(updatedSchedule);

      await useScheduleStore.getState().updateSchedule('s1', updateData);

      const schedules = useScheduleStore.getState().schedules;
      expect(schedules[0].cronExpression).toBe('0 6 * * *');
      expect(schedules[1].cronExpression).toBe('0 12 * * *');
    });

    it('should throw on error', async () => {
      const { api, ApiError } = await import('../services/api');
      vi.mocked(api.schedules.update).mockRejectedValue(
        new ApiError('Not found')
      );

      await expect(
        useScheduleStore.getState().updateSchedule('s1', {})
      ).rejects.toThrow();
    });
  });

  describe('deleteSchedule', () => {
    it('should remove schedule from array on success', async () => {
      const existingSchedules: Schedule[] = [
        {
          id: 's1',
          workflowId: 'wf1',
          cronExpression: '0 0 * * *',
          enabled: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01',
        },
        {
          id: 's2',
          workflowId: 'wf1',
          cronExpression: '0 12 * * *',
          enabled: false,
          createdAt: '2024-01-02',
          updatedAt: '2024-01-02',
        },
      ];

      useScheduleStore.setState({ schedules: existingSchedules });

      const { api } = await import('../services/api');
      vi.mocked(api.schedules.delete).mockResolvedValue(undefined);

      await useScheduleStore.getState().deleteSchedule('s1');

      const schedules = useScheduleStore.getState().schedules;
      expect(schedules).toHaveLength(1);
      expect(schedules[0].id).toBe('s2');
    });
  });

  describe('toggleSchedule', () => {
    it('should replace schedule in array on success', async () => {
      const existingSchedules: Schedule[] = [
        {
          id: 's1',
          workflowId: 'wf1',
          cronExpression: '0 0 * * *',
          enabled: true,
          createdAt: '2024-01-01',
          updatedAt: '2024-01-01',
        },
      ];

      useScheduleStore.setState({ schedules: existingSchedules });

      const toggledSchedule: Schedule = {
        ...existingSchedules[0],
        enabled: false,
      };

      const { api } = await import('../services/api');
      vi.mocked(api.schedules.toggle).mockResolvedValue(toggledSchedule);

      await useScheduleStore.getState().toggleSchedule('s1');

      const schedules = useScheduleStore.getState().schedules;
      expect(schedules[0].enabled).toBe(false);
    });

    it('should no-op when schedule not found', async () => {
      useScheduleStore.setState({ schedules: [] });

      await useScheduleStore.getState().toggleSchedule('s1');

      expect(useScheduleStore.getState().loading).toBe(false);
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useScheduleStore.setState({ error: 'Some error' });

      useScheduleStore.getState().clearError();

      expect(useScheduleStore.getState().error).toBeNull();
    });
  });

  describe('ApiError message extraction', () => {
    it('should extract message from ApiError', async () => {
      const { api, ApiError } = await import('../services/api');
      vi.mocked(api.schedules.list).mockRejectedValue(
        new ApiError('Custom API error')
      );

      await useScheduleStore.getState().fetchSchedules('wf1');

      expect(useScheduleStore.getState().error).toBe('Custom API error');
    });

    it('should use fallback message for non-ApiError', async () => {
      const { api } = await import('../services/api');
      vi.mocked(api.schedules.list).mockRejectedValue('string error');

      await useScheduleStore.getState().fetchSchedules('wf1');

      expect(useScheduleStore.getState().error).toBe('Failed to fetch schedules');
    });
  });
});
