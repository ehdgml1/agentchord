/**
 * Hook for caching LLM provider key status
 */

import { useState, useEffect, useCallback } from 'react';
import { api, type LLMKeyStatus } from '../services/api';

export function useLLMKeyStatus() {
  const [keys, setKeys] = useState<LLMKeyStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await api.llm.getKeyStatus();
      setKeys(result);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isProviderConfigured = useCallback(
    (provider: string) => {
      const key = keys.find((k) => k.provider === provider);
      return key?.configured ?? false;
    },
    [keys]
  );

  return { keys, loading, error, refresh, isProviderConfigured };
}
