/**
 * Zustand store for schedule state
 *
 * Manages workflow schedules including creation, updates, and deletion.
 */

import { create } from 'zustand';
import type { Schedule, CreateScheduleData, UpdateScheduleData } from '../types/schedule';
import { api, ApiError } from '../services/api';

/**
 * Schedule store state and actions interface
 */
interface ScheduleState {
  /** List of schedules */
  schedules: Schedule[];
  /** Loading state for async operations */
  loading: boolean;
  /** Error message from last failed operation */
  error: string | null;

  /** Fetch schedules for a workflow */
  fetchSchedules: (workflowId: string) => Promise<void>;
  /** Create a new schedule */
  createSchedule: (data: CreateScheduleData) => Promise<Schedule>;
  /** Update an existing schedule */
  updateSchedule: (id: string, data: UpdateScheduleData) => Promise<void>;
  /** Delete a schedule */
  deleteSchedule: (id: string) => Promise<void>;
  /** Toggle schedule enabled/disabled */
  toggleSchedule: (id: string) => Promise<void>;
  /** Clear error message */
  clearError: () => void;
}

/**
 * Main schedule store
 */
export const useScheduleStore = create<ScheduleState>((set, get) => ({
  schedules: [],
  loading: false,
  error: null,

  fetchSchedules: async (workflowId: string) => {
    set({ loading: true, error: null });

    try {
      const schedules = await api.schedules.list(workflowId);
      set({ schedules, loading: false });
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to fetch schedules';
      set({ error: message, loading: false });
    }
  },

  createSchedule: async (data: CreateScheduleData) => {
    set({ loading: true, error: null });

    try {
      const schedule = await api.schedules.create(data);

      set((state) => ({
        schedules: [...state.schedules, schedule],
        loading: false,
      }));

      return schedule;
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to create schedule';
      set({ error: message, loading: false });
      throw error;
    }
  },

  updateSchedule: async (id: string, data: UpdateScheduleData) => {
    set({ loading: true, error: null });

    try {
      const updated = await api.schedules.update(id, data);

      set((state) => ({
        schedules: state.schedules.map((s) =>
          s.id === id ? updated : s
        ),
        loading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to update schedule';
      set({ error: message, loading: false });
      throw error;
    }
  },

  deleteSchedule: async (id: string) => {
    set({ loading: true, error: null });

    try {
      await api.schedules.delete(id);

      set((state) => ({
        schedules: state.schedules.filter((s) => s.id !== id),
        loading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to delete schedule';
      set({ error: message, loading: false });
    }
  },

  toggleSchedule: async (id: string) => {
    const schedule = get().schedules.find((s) => s.id === id);
    if (!schedule) return;

    set({ loading: true, error: null });

    try {
      const updated = await api.schedules.toggle(id);

      set((state) => ({
        schedules: state.schedules.map((s) =>
          s.id === id ? updated : s
        ),
        loading: false,
      }));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to toggle schedule';
      set({ error: message, loading: false });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));

/**
 * Selector hook for schedules list
 */
export const useSchedules = () =>
  useScheduleStore((state) => state.schedules);

/**
 * Selector hook for enabled schedules only
 */
export const useEnabledSchedules = () =>
  useScheduleStore((state) => state.schedules.filter((s) => s.enabled));

/**
 * Selector hook for loading state
 */
export const useScheduleLoading = () =>
  useScheduleStore((state) => state.loading);

/**
 * Selector hook for error state
 */
export const useScheduleError = () =>
  useScheduleStore((state) => state.error);
