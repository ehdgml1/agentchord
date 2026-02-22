/**
 * Single provider row for LLM key management popover
 */

import { memo, useCallback, useState } from 'react';
import { Check, Eye, EyeOff, Loader2, Trash2, X } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';
import { api } from '../../services/api';
import type { LLMKeyStatus } from '../../services/api';

interface ProviderKeyRowProps {
  status: LLMKeyStatus;
  onUpdate: () => void;
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Gemini',
  ollama: 'Ollama',
};

export const ProviderKeyRow = memo(function ProviderKeyRow({
  status,
  onUpdate,
}: ProviderKeyRowProps) {
  const [keyValue, setKeyValue] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validated, setValidated] = useState<boolean | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleValidate = useCallback(async () => {
    if (!keyValue.trim()) return;
    setValidating(true);
    setValidated(null);
    setValidationError(null);
    try {
      const result = await api.llm.validateKey(status.provider, keyValue);
      setValidated(result.valid);
      if (!result.valid) {
        setValidationError(result.error || 'Validation failed');
      }
    } catch {
      setValidated(false);
      setValidationError('Validation failed');
    } finally {
      setValidating(false);
    }
  }, [keyValue, status.provider]);

  const handleSave = useCallback(async () => {
    if (!keyValue.trim()) return;
    setSaving(true);
    try {
      await api.llm.setKey(status.provider, keyValue);
      setKeyValue('');
      setValidated(null);
      onUpdate();
    } catch {
      // Error handled by API layer
    } finally {
      setSaving(false);
    }
  }, [keyValue, status.provider, onUpdate]);

  const handleDelete = useCallback(async () => {
    try {
      await api.llm.deleteKey(status.provider);
      onUpdate();
    } catch {
      // Error handled by API layer
    }
  }, [status.provider, onUpdate]);

  const label = PROVIDER_LABELS[status.provider] || status.provider;
  const isOllama = status.provider === 'ollama';

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'w-2 h-2 rounded-full',
              status.configured ? 'bg-green-500' : 'bg-gray-300'
            )}
          />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <div className="flex items-center gap-1">
          {status.hasServerKey && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
              Server
            </span>
          )}
          {status.hasUserKey && (
            <>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300">
                User
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5"
                onClick={handleDelete}
                title="Delete key"
              >
                <Trash2 className="w-3 h-3 text-red-500" />
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="flex gap-1">
        <div className="relative flex-1">
          <Input
            type={showKey ? 'text' : 'password'}
            value={keyValue}
            onChange={(e) => {
              setKeyValue(e.target.value);
              setValidated(null);
              setValidationError(null);
            }}
            placeholder={isOllama ? 'http://localhost:11434' : 'Enter API key...'}
            className="h-7 text-xs pr-7"
          />
          <button
            type="button"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowKey(!showKey)}
          >
            {showKey ? (
              <EyeOff className="w-3.5 h-3.5" />
            ) : (
              <Eye className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs px-2"
          onClick={handleValidate}
          disabled={!keyValue.trim() || validating}
        >
          {validating ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : validated === true ? (
            <Check className="w-3 h-3 text-green-500" />
          ) : validated === false ? (
            <X className="w-3 h-3 text-red-500" />
          ) : (
            'Test'
          )}
        </Button>
        <Button
          variant="default"
          size="sm"
          className="h-7 text-xs px-2"
          onClick={handleSave}
          disabled={!keyValue.trim() || saving}
        >
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Save'}
        </Button>
      </div>
      {validationError && (
        <p className="text-[10px] text-red-500">{validationError}</p>
      )}
    </div>
  );
});
