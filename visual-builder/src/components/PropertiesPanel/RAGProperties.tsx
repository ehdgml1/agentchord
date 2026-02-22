/**
 * Properties editor for RAG blocks
 *
 * Provides form controls for configuring RAG document retrieval and generation.
 */

import { memo, useCallback, useMemo, useState } from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { DocumentUploader } from './DocumentUploader';
import type { DocumentFileInfo } from '../../types/blocks';
import { api } from '../../services/api';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Slider } from '../ui/slider';
import { Switch } from '../ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { RAGBlockData } from '../../types/blocks';
import {
  getEmbeddingModelsByProvider,
  getEmbeddingModelInfo,
  type EmbeddingProvider,
} from '../../constants/embeddingModels';
import { useLLMKeyStatus } from '../../hooks/useLLMKeyStatus';
import { MODEL_LIST } from '../../constants/models';
import { InputTemplateEditor } from './InputTemplateEditor';

function getProviderFromModel(modelId: string): string {
  if (modelId.startsWith('gpt-') || modelId.startsWith('o1')) {
    return 'openai';
  } else if (modelId.startsWith('claude-')) {
    return 'anthropic';
  } else if (modelId.startsWith('gemini-')) {
    return 'google';
  } else {
    return 'ollama';
  }
}

interface RAGPropertiesProps {
  nodeId: string;
  data: RAGBlockData;
  onChange: (data: Partial<RAGBlockData>) => void;
}

export const RAGProperties = memo(function RAGProperties({
  nodeId,
  data,
  onChange,
}: RAGPropertiesProps) {
  const { isProviderConfigured } = useLLMKeyStatus();

  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string>();

  const provider = useMemo(
    () => (data.model ? getProviderFromModel(data.model) : ''),
    [data.model]
  );
  const providerConfigured = useMemo(
    () => (provider ? isProviderConfigured(provider) : false),
    [isProviderConfigured, provider]
  );

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
    (value: string) => {
      onChange({ model: value });
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

  const handleEmbeddingProviderChange = useCallback(
    (value: string) => {
      if (value === 'default') {
        onChange({
          embeddingProvider: undefined,
          embeddingModel: undefined,
          embeddingDimensions: undefined,
        });
      } else {
        onChange({ embeddingProvider: value as EmbeddingProvider });
      }
    },
    [onChange]
  );

  const handleEmbeddingModelChange = useCallback(
    (value: string) => {
      const modelInfo = getEmbeddingModelInfo(value);
      onChange({
        embeddingModel: value,
        embeddingDimensions: modelInfo?.dimensions,
      });
    },
    [onChange]
  );

  const handleFileUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setUploadError(undefined);
      try {
        const meta = await api.documents.upload(file);
        const fileInfo: DocumentFileInfo = {
          id: meta.id,
          filename: meta.filename,
          size: meta.size,
          mimeType: meta.mimeType,
        };
        const currentFiles = data.documentFiles || [];
        onChange({ documentFiles: [...currentFiles, fileInfo] });
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : '업로드에 실패했습니다');
      } finally {
        setIsUploading(false);
      }
    },
    [data.documentFiles, onChange]
  );

  const handleFileDelete = useCallback(
    async (fileId: string) => {
      try {
        await api.documents.delete(fileId);
        const currentFiles = data.documentFiles || [];
        onChange({ documentFiles: currentFiles.filter(f => f.id !== fileId) });
      } catch {
        // File already deleted or not found, just remove from state
        const currentFiles = data.documentFiles || [];
        onChange({ documentFiles: currentFiles.filter(f => f.id !== fileId) });
      }
    },
    [data.documentFiles, onChange]
  );

  const documentsText = Array.isArray(data.documents)
    ? data.documents.join('\n')
    : '';

  const availableEmbeddingModels = data.embeddingProvider
    ? getEmbeddingModelsByProvider(data.embeddingProvider)
    : [];

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

      {/* Input Template */}
      <InputTemplateEditor
        nodeId={nodeId}
        value={(data.inputTemplate as string) || ''}
        onChange={(inputTemplate) => onChange({ inputTemplate })}
      />

      <div className="space-y-2">
        <Label>문서 파일 업로드</Label>
        <DocumentUploader
          files={data.documentFiles || []}
          onUpload={handleFileUpload}
          onDelete={handleFileDelete}
          isUploading={isUploading}
          error={uploadError}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="documents">또는 텍스트 직접 입력</Label>
        <Textarea
          id="documents"
          value={documentsText}
          onChange={handleDocumentsChange}
          placeholder="한 줄에 하나씩 텍스트를 입력하세요"
          rows={4}
        />
        <p className="text-xs text-muted-foreground">
          업로드 파일과 텍스트 입력 모두 RAG 인덱싱에 사용됩니다
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
        <Select value={data.model || ''} onValueChange={handleModelChange}>
          <SelectTrigger id="model">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {MODEL_LIST.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center gap-2">
                  <span>{model.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({model.provider})
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data.model && (
          providerConfigured ? (
            <div className="flex items-center gap-1.5 text-xs text-green-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Provider configured</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-yellow-600">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>No API key for {provider}. Set in LLM Settings.</span>
            </div>
          )
        )}
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

      <div className="space-y-4 border-t pt-4">
        <h3 className="text-sm font-medium">Embedding Configuration</h3>

        <div className="space-y-2">
          <Label htmlFor="embeddingProvider">Embedding Provider</Label>
          <Select
            value={data.embeddingProvider || 'default'}
            onValueChange={handleEmbeddingProviderChange}
          >
            <SelectTrigger id="embeddingProvider">
              <SelectValue placeholder="Global Default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Global Default</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="gemini">Gemini</SelectItem>
              <SelectItem value="ollama">Ollama</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Override global embedding provider
          </p>
        </div>

        {data.embeddingProvider && (
          <>
            <div className="space-y-2">
              <Label htmlFor="embeddingModel">Embedding Model</Label>
              <Select
                value={data.embeddingModel || ''}
                onValueChange={handleEmbeddingModelChange}
              >
                <SelectTrigger id="embeddingModel">
                  <SelectValue placeholder="Select embedding model" />
                </SelectTrigger>
                <SelectContent>
                  {availableEmbeddingModels.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex items-center gap-2">
                        <span>{model.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({model.dimensions}d)
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {data.embeddingModel
                  ? `Dimensions: ${data.embeddingDimensions || 'auto'}`
                  : 'Select a model to configure'}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
});
