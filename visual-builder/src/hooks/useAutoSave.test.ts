import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

const mockSaveWorkflow = vi.fn();
const mockUseWorkflowStore = vi.fn();

vi.mock('../stores/workflowStore', () => ({
  useWorkflowStore: (selector: any) => mockUseWorkflowStore(selector),
}));

import { useAutoSave } from './useAutoSave';

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockSaveWorkflow.mockClear();
    mockSaveWorkflow.mockResolvedValue(undefined);
    mockUseWorkflowStore.mockClear();
    // Default state
    mockUseWorkflowStore.mockImplementation((selector: any) => {
      const state = {
        isDirty: false,
        backendId: null,
        saveWorkflow: mockSaveWorkflow,
        isSaving: false,
      };
      return typeof selector === 'function' ? selector(state) : state;
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not save when not dirty', () => {
    renderHook(() => useAutoSave());
    vi.advanceTimersByTime(35000);
    expect(mockSaveWorkflow).not.toHaveBeenCalled();
  });

  it('does not save when no backendId', () => {
    mockUseWorkflowStore.mockImplementation((selector: any) => {
      const state = { isDirty: true, backendId: null, saveWorkflow: mockSaveWorkflow, isSaving: false };
      return typeof selector === 'function' ? selector(state) : state;
    });
    renderHook(() => useAutoSave());
    vi.advanceTimersByTime(35000);
    expect(mockSaveWorkflow).not.toHaveBeenCalled();
  });
});
