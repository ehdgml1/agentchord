import { memo, useCallback, useEffect, useState } from 'react';
import { Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { api, type LLMProviderStatus, type LLMKeyStatus } from '../../services/api';
import { ProviderKeyRow } from './ProviderKeyRow';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../ui/popover';

interface LLMStatusProps {
  className?: string;
}

export const LLMStatus = memo(function LLMStatus({ className }: LLMStatusProps) {
  const [providers, setProviders] = useState<LLMProviderStatus[]>([]);
  const [keys, setKeys] = useState<LLMKeyStatus[]>([]);
  const [defaultModel, setDefaultModel] = useState<string>('');
  const [error, setError] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const [provRes, keyRes] = await Promise.all([
        api.llm.listProviders(),
        api.llm.getKeyStatus(),
      ]);
      setProviders(provRes.providers);
      setDefaultModel(provRes.defaultModel);
      setKeys(keyRes);
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

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={cn(
            'flex items-center gap-1.5 px-2 py-1 rounded text-xs cursor-pointer transition-colors',
            'hover:opacity-80',
            hasAny
              ? 'text-green-600 bg-green-50 dark:bg-green-950/30'
              : 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30',
            error && 'text-red-600 bg-red-50 dark:bg-red-950/30',
            className
          )}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span className="font-medium">
            {error ? 'LLM Error' : `${configuredCount}/${providers.length} LLM`}
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-3" align="end">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">LLM Providers</h4>
            {defaultModel && (
              <span className="text-[10px] text-muted-foreground">
                Default: {defaultModel}
              </span>
            )}
          </div>
          <div className="space-y-3">
            {keys.map((key) => (
              <ProviderKeyRow
                key={key.provider}
                status={key}
                onUpdate={fetchStatus}
              />
            ))}
          </div>
          {keys.length === 0 && !error && (
            <p className="text-xs text-muted-foreground text-center py-2">
              Loading providers...
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
});
