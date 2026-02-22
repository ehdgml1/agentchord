/**
 * Embedding model configuration for RAG blocks
 *
 * Defines available embedding models with their provider, dimensions,
 * and display information.
 */

export type EmbeddingProvider = 'openai' | 'gemini' | 'ollama';

export interface EmbeddingModelInfo {
  /** Model identifier */
  id: string;
  /** Display name for UI */
  name: string;
  /** Embedding provider */
  provider: EmbeddingProvider;
  /** Output embedding dimensions */
  dimensions: number;
  /** Human-readable description */
  description: string;
}

/**
 * Available embedding models organized by provider
 */
export const EMBEDDING_MODELS: EmbeddingModelInfo[] = [
  {
    id: 'text-embedding-3-small',
    name: 'Text Embedding 3 Small',
    provider: 'openai',
    dimensions: 1536,
    description: 'Fast and affordable OpenAI embeddings',
  },
  {
    id: 'text-embedding-3-large',
    name: 'Text Embedding 3 Large',
    provider: 'openai',
    dimensions: 3072,
    description: 'Highest quality OpenAI embeddings',
  },
  {
    id: 'gemini-embedding-001',
    name: 'Gemini Embedding 001',
    provider: 'gemini',
    dimensions: 3072,
    description: 'Latest Google embedding model',
  },
  {
    id: 'nomic-embed-text',
    name: 'Nomic Embed Text',
    provider: 'ollama',
    dimensions: 768,
    description: 'Local embedding via Ollama',
  },
];

/**
 * Get embedding models for a specific provider
 */
export const getEmbeddingModelsByProvider = (
  provider: EmbeddingProvider
): EmbeddingModelInfo[] =>
  EMBEDDING_MODELS.filter((m) => m.provider === provider);

/**
 * Get embedding model info by ID
 */
export const getEmbeddingModelInfo = (
  modelId: string
): EmbeddingModelInfo | undefined =>
  EMBEDDING_MODELS.find((m) => m.id === modelId);
