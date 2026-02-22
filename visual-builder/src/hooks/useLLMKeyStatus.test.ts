/**
 * Tests for useLLMKeyStatus hook
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useLLMKeyStatus } from './useLLMKeyStatus';
import type { LLMKeyStatus } from '../services/api';

// Mock the API
vi.mock('../services/api', () => ({
  api: {
    llm: {
      getKeyStatus: vi.fn(),
    },
  },
}));

// Import mocked API
import { api } from '../services/api';
const mockGetKeyStatus = vi.mocked(api.llm.getKeyStatus);

describe('useLLMKeyStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches key status on mount', async () => {
    const mockKeys: LLMKeyStatus[] = [
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'anthropic', hasUserKey: false, hasServerKey: true, configured: true },
    ];

    mockGetKeyStatus.mockResolvedValueOnce(mockKeys);

    const { result } = renderHook(() => useLLMKeyStatus());

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.keys).toEqual([]);

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockGetKeyStatus).toHaveBeenCalledOnce();
    expect(result.current.keys).toEqual(mockKeys);
    expect(result.current.error).toBe(false);
  });

  it('returns loading=true initially', () => {
    mockGetKeyStatus.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useLLMKeyStatus());

    expect(result.current.loading).toBe(true);
    expect(result.current.keys).toEqual([]);
    expect(result.current.error).toBe(false);
  });

  it('returns error on API failure', async () => {
    mockGetKeyStatus.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useLLMKeyStatus());

    // Wait for error state
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe(true);
    expect(result.current.keys).toEqual([]);
  });

  it('refresh() triggers a re-fetch', async () => {
    const mockKeys1: LLMKeyStatus[] = [
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
    ];
    const mockKeys2: LLMKeyStatus[] = [
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'gemini', hasUserKey: true, hasServerKey: false, configured: true },
    ];

    mockGetKeyStatus
      .mockResolvedValueOnce(mockKeys1)
      .mockResolvedValueOnce(mockKeys2);

    const { result } = renderHook(() => useLLMKeyStatus());

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.keys).toEqual(mockKeys1);

    // Call refresh
    await act(async () => {
      await result.current.refresh();
    });

    expect(mockGetKeyStatus).toHaveBeenCalledTimes(2);
    expect(result.current.keys).toEqual(mockKeys2);
    expect(result.current.error).toBe(false);
  });

  it('isProviderConfigured returns true when provider has key', async () => {
    const mockKeys: LLMKeyStatus[] = [
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'anthropic', hasUserKey: false, hasServerKey: true, configured: true },
    ];

    mockGetKeyStatus.mockResolvedValueOnce(mockKeys);

    const { result } = renderHook(() => useLLMKeyStatus());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.isProviderConfigured('openai')).toBe(true);
    expect(result.current.isProviderConfigured('anthropic')).toBe(true);
  });

  it('isProviderConfigured returns false when provider has no key', async () => {
    const mockKeys: LLMKeyStatus[] = [
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'anthropic', hasUserKey: false, hasServerKey: false, configured: false },
    ];

    mockGetKeyStatus.mockResolvedValueOnce(mockKeys);

    const { result } = renderHook(() => useLLMKeyStatus());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Provider not configured
    expect(result.current.isProviderConfigured('anthropic')).toBe(false);

    // Provider not in keys array
    expect(result.current.isProviderConfigured('gemini')).toBe(false);
  });
});
