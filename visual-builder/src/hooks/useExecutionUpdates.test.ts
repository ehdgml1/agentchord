import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useExecutionUpdates } from './useExecutionUpdates';

describe('useExecutionUpdates', () => {
  it('has correct initial state when executionId is null', () => {
    const { result } = renderHook(() => useExecutionUpdates(null));

    expect(result.current.execution).toBe(null);
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('returns execution state', () => {
    const { result } = renderHook(() => useExecutionUpdates('exec-123'));

    expect(result.current).toHaveProperty('execution');
    expect(result.current).toHaveProperty('isConnected');
    expect(result.current).toHaveProperty('error');
  });

  it('does not throw when executionId is provided', () => {
    expect(() => {
      renderHook(() => useExecutionUpdates('exec-123'));
    }).not.toThrow();
  });

  it('does not throw when executionId is null', () => {
    expect(() => {
      renderHook(() => useExecutionUpdates(null));
    }).not.toThrow();
  });
});
