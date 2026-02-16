import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, setAuthToken } from './api';

describe('api.llm', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    setAuthToken('test-token');
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    setAuthToken(null);
  });

  describe('listProviders', () => {
    it('fetches providers from /api/llm/providers', async () => {
      const mockResponse = {
        providers: [
          { name: 'openai', configured: true, models: ['gpt-4o'] },
          { name: 'anthropic', configured: false, models: [] },
        ],
        defaultModel: 'gpt-4o',
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.llm.listProviders();

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/llm/providers',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
      expect(result.providers).toHaveLength(2);
      expect(result.providers[0].name).toBe('openai');
      expect(result.defaultModel).toBe('gpt-4o');
    });

    it('throws on API error', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({ message: 'Not authenticated' }),
      });

      await expect(api.llm.listProviders()).rejects.toThrow();
    });
  });

  describe('listModels', () => {
    it('fetches and unwraps models from /api/llm/models', async () => {
      const mockResponse = {
        models: [
          {
            id: 'gpt-4o',
            provider: 'openai',
            displayName: 'GPT-4o',
            contextWindow: 128000,
            costPer1kInput: 0.0025,
            costPer1kOutput: 0.01,
          },
          {
            id: 'claude-sonnet-4-5-20250929',
            provider: 'anthropic',
            displayName: 'Claude Sonnet 4.5',
            contextWindow: 200000,
            costPer1kInput: 0.003,
            costPer1kOutput: 0.015,
          },
        ],
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await api.llm.listModels();

      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/llm/models',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
      expect(result).toHaveLength(2);
      expect(result[0].id).toBe('gpt-4o');
      expect(result[1].provider).toBe('anthropic');
    });

    it('returns empty array when no models', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ models: [] }),
      });

      const result = await api.llm.listModels();
      expect(result).toHaveLength(0);
    });
  });
});
