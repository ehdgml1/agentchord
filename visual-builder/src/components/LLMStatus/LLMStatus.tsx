import { memo, useCallback, useEffect, useState } from 'react';
import { Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { api, type LLMProviderStatus } from '../../services/api';

interface LLMStatusProps {
  className?: string;
}

export const LLMStatus = memo(function LLMStatus({ className }: LLMStatusProps) {
  const [providers, setProviders] = useState<LLMProviderStatus[]>([]);
  const [defaultModel, setDefaultModel] = useState<string>('');
  const [error, setError] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.llm.listProviders();
      setProviders(res.providers);
      setDefaultModel(res.defaultModel);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 60_000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const configuredCount = providers.filter((p) => p.configured).length;
  const hasAny = configuredCount > 0;

  const tooltipText = error
    ? 'Error fetching LLM status'
    : providers
        .map(
          (p) =>
            `${p.name}: ${
              p.configured ? `${p.models.length} models` : 'not configured'
            }`
        )
        .join('\n') + (defaultModel ? `\nDefault: ${defaultModel}` : '');

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-1 rounded text-xs cursor-default',
        hasAny
          ? 'text-green-600 bg-green-50 dark:bg-green-950/30'
          : 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30',
        error && 'text-red-600 bg-red-50 dark:bg-red-950/30',
        className
      )}
      title={tooltipText}
    >
      <Cpu className="w-3.5 h-3.5" />
      <span className="font-medium">
        {error ? 'LLM Error' : `${configuredCount}/${providers.length} LLM`}
      </span>
    </div>
  );
});
