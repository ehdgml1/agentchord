import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useDebugWebSocket } from './useDebugWebSocket';

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(() => 'test-token-123'),
}));

describe('useDebugWebSocket', () => {
  it('has correct initial state when workflowId is null', () => {
    const { result } = renderHook(() => useDebugWebSocket(null));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.isDebugging).toBe(false);
    expect(result.current.isPaused).toBe(false);
    expect(result.current.currentNode).toBe(null);
    expect(result.current.events).toEqual([]);
  });

  it('provides connect function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.connect).toBe('function');
  });

  it('provides disconnect function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.disconnect).toBe('function');
  });

  it('provides start function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.start).toBe('function');
  });

  it('provides continue function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.continue).toBe('function');
  });

  it('provides step function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.step).toBe('function');
  });

  it('provides stop function', () => {
    const { result } = renderHook(() => useDebugWebSocket('workflow-123'));

    expect(typeof result.current.stop).toBe('function');
  });
});
