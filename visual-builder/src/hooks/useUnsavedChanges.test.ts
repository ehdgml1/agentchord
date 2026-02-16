import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock workflowStore
const mockIsDirty = vi.fn(() => false);
vi.mock('../stores/workflowStore', () => ({
  useWorkflowStore: vi.fn((selector: any) => {
    const state = { isDirty: mockIsDirty() };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));


import { useUnsavedChanges } from './useUnsavedChanges';

describe('useUnsavedChanges', () => {
  let addSpy: ReturnType<typeof vi.spyOn>;
  let removeSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    addSpy = vi.spyOn(window, 'addEventListener');
    removeSpy = vi.spyOn(window, 'removeEventListener');
  });

  afterEach(() => {
    addSpy.mockRestore();
    removeSpy.mockRestore();
    vi.clearAllMocks();
  });

  it('does not add beforeunload when not dirty', () => {
    mockIsDirty.mockReturnValue(false);
    renderHook(() => useUnsavedChanges());
    expect(addSpy).not.toHaveBeenCalledWith('beforeunload', expect.any(Function));
  });

  it('adds beforeunload when dirty', () => {
    mockIsDirty.mockReturnValue(true);
    renderHook(() => useUnsavedChanges());
    expect(addSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function));
  });

  it('removes beforeunload on cleanup', () => {
    mockIsDirty.mockReturnValue(true);
    const { unmount } = renderHook(() => useUnsavedChanges());
    unmount();
    expect(removeSpy).toHaveBeenCalledWith('beforeunload', expect.any(Function));
  });
});
