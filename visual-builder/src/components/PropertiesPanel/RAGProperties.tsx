/**
 * Properties editor for RAG blocks
 *
 * Provides form controls for configuring RAG document retrieval and generation.
 */

import { memo, useCallback } from 'react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Slider } from '../ui/slider';
import { Switch } from '../ui/switch';
import type { RAGBlockData } from '../../types/blocks';

interface RAGPropertiesProps {
  data: RAGBlockData;
  onChange: (data: Partial<RAGBlockData>) => void;
}

export const RAGProperties = memo(function RAGProperties({
  data,
  onChange,
}: RAGPropertiesProps) {
  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ name: e.target.value });
    },
    [onChange]
  );

  const handleDocumentsChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      // Parse newline-separated list or JSON array
      const value = e.target.value.trim();
      let documents: string[] = [];

      if (value) {
        try {
          // Try parsing as JSON array first
          const parsed = JSON.parse(value);
          if (Array.isArray(parsed)) {
            documents = parsed.filter(d => typeof d === 'string');
          }
        } catch {
          // Fall back to newline-separated list
          documents = value.split('\n').map(d => d.trim()).filter(d => d);
        }
      }

      onChange({ documents });
    },
    [onChange]
  );

  const handleSearchLimitChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value > 0) {
        onChange({ searchLimit: value });
      }
    },
    [onChange]
  );

  const handleBm25Change = useCallback(
    (checked: boolean) => {
      onChange({ enableBm25: checked });
    },
    [onChange]
  );

  const handleChunkSizeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value > 0) {
        onChange({ chunkSize: value });
      }
    },
    [onChange]
  );

  const handleChunkOverlapChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value >= 0) {
        onChange({ chunkOverlap: value });
      }
    },
    [onChange]
  );

  const handleSystemPromptChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange({ systemPrompt: e.target.value });
    },
    [onChange]
  );

  const handleModelChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ model: e.target.value });
    },
    [onChange]
  );

  const handleTemperatureChange = useCallback(
    (value: number[]) => {
      onChange({ temperature: value[0] });
    },
    [onChange]
  );

  const handleMaxTokensChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value) && value > 0) {
        onChange({ maxTokens: value });
      }
    },
    [onChange]
  );

  const documentsText = Array.isArray(data.documents)
    ? data.documents.join('\n')
    : '';

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          value={data.name || ''}
          onChange={handleNameChange}
          placeholder="rag_node"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="documents">Documents</Label>
        <Textarea
          id="documents"
          value={documentsText}
          onChange={handleDocumentsChange}
          placeholder="One document path per line, or JSON array"
          rows={4}
        />
        <p className="text-xs text-muted-foreground">
          Enter document paths one per line
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="searchLimit">Search Limit</Label>
        <Input
          id="searchLimit"
          type="number"
          value={data.searchLimit || 5}
          onChange={handleSearchLimitChange}
          min={1}
          max={50}
          placeholder="5"
        />
        <p className="text-xs text-muted-foreground">
          Number of documents to retrieve
        </p>
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="enableBm25">Enable BM25 keyword search</Label>
        <Switch
          id="enableBm25"
          checked={data.enableBm25 ?? true}
          onCheckedChange={handleBm25Change}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="chunkSize">Chunk Size</Label>
        <Input
          id="chunkSize"
          type="number"
          value={data.chunkSize || 500}
          onChange={handleChunkSizeChange}
          min={100}
          max={4000}
          placeholder="500"
        />
        <p className="text-xs text-muted-foreground">
          Size of text chunks in characters
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="chunkOverlap">Chunk Overlap</Label>
        <Input
          id="chunkOverlap"
          type="number"
          value={data.chunkOverlap || 50}
          onChange={handleChunkOverlapChange}
          min={0}
          max={500}
          placeholder="50"
        />
        <p className="text-xs text-muted-foreground">
          Overlap between consecutive chunks
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="systemPrompt">System Prompt</Label>
        <Textarea
          id="systemPrompt"
          value={data.systemPrompt || ''}
          onChange={handleSystemPromptChange}
          placeholder="Optional instructions for generation..."
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="model">Model</Label>
        <Input
          id="model"
          value={data.model || ''}
          onChange={handleModelChange}
          placeholder="gpt-4o-mini"
        />
        <p className="text-xs text-muted-foreground">
          AI model for answer generation
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between">
          <Label>Temperature</Label>
          <span className="text-sm text-muted-foreground">
            {data.temperature?.toFixed(1) || '0.3'}
          </span>
        </div>
        <Slider
          value={[data.temperature ?? 0.3]}
          onValueChange={handleTemperatureChange}
          min={0}
          max={1}
          step={0.1}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="maxTokens">Max Tokens</Label>
        <Input
          id="maxTokens"
          type="number"
          value={data.maxTokens || 1024}
          onChange={handleMaxTokensChange}
          min={1}
          max={200000}
          placeholder="1024"
        />
        <p className="text-xs text-muted-foreground">
          Maximum tokens for generation
        </p>
      </div>
    </div>
  );
});
