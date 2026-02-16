/**
 * Model configuration and pricing information
 *
 * This module provides metadata for all supported AI models including
 * provider information, capabilities, and cost estimates.
 */

import type { ModelId } from '../types/blocks';

/**
 * Complete information about an AI model
 */
export interface ModelInfo {
  /** Unique identifier for the model */
  id: ModelId;
  /** Display name for UI */
  name: string;
  /** Model provider (OpenAI, Anthropic, Ollama, or Google) */
  provider: 'openai' | 'anthropic' | 'ollama' | 'google';
  /** Human-readable description of model capabilities */
  description: string;
  /** Maximum context window in tokens */
  maxTokens: number;
  /** Cost per 1,000 input tokens in USD */
  costPer1kInput: number;
  /** Cost per 1,000 output tokens in USD */
  costPer1kOutput: number;
}

/**
 * Comprehensive model information database
 *
 * Includes current pricing as of 2025. Prices may change.
 */
export const MODELS: Record<ModelId, ModelInfo> = {
  'gpt-4o': {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most capable OpenAI model',
    maxTokens: 128000,
    costPer1kInput: 0.0025,
    costPer1kOutput: 0.01,
  },
  'gpt-4o-mini': {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Fast and affordable',
    maxTokens: 128000,
    costPer1kInput: 0.00015,
    costPer1kOutput: 0.0006,
  },
  'gpt-4.1': {
    id: 'gpt-4.1',
    name: 'GPT-4.1',
    provider: 'openai',
    description: 'Latest OpenAI flagship model with 1M context',
    maxTokens: 1000000,
    costPer1kInput: 0.002,
    costPer1kOutput: 0.008,
  },
  'gpt-4.1-mini': {
    id: 'gpt-4.1-mini',
    name: 'GPT-4.1 Mini',
    provider: 'openai',
    description: 'Fast and affordable with 1M context',
    maxTokens: 1000000,
    costPer1kInput: 0.0004,
    costPer1kOutput: 0.0016,
  },
  'o1': {
    id: 'o1',
    name: 'O1',
    provider: 'openai',
    description: 'Advanced reasoning model',
    maxTokens: 200000,
    costPer1kInput: 0.015,
    costPer1kOutput: 0.06,
  },
  'o1-mini': {
    id: 'o1-mini',
    name: 'O1 Mini',
    provider: 'openai',
    description: 'Efficient reasoning model',
    maxTokens: 128000,
    costPer1kInput: 0.003,
    costPer1kOutput: 0.012,
  },
  'claude-sonnet-4-5-20250929': {
    id: 'claude-sonnet-4-5-20250929',
    name: 'Claude Sonnet 4.5',
    provider: 'anthropic',
    description: 'Best balance of intelligence and speed',
    maxTokens: 200000,
    costPer1kInput: 0.003,
    costPer1kOutput: 0.015,
  },
  'claude-haiku-4-5-20251001': {
    id: 'claude-haiku-4-5-20251001',
    name: 'Claude Haiku 4.5',
    provider: 'anthropic',
    description: 'Fastest Anthropic model',
    maxTokens: 200000,
    costPer1kInput: 0.001,
    costPer1kOutput: 0.005,
  },
  'claude-opus-4-6': {
    id: 'claude-opus-4-6',
    name: 'Claude Opus 4.6',
    provider: 'anthropic',
    description: 'Most capable Anthropic model',
    maxTokens: 200000,
    costPer1kInput: 0.005,
    costPer1kOutput: 0.025,
  },
  'llama3.1': {
    id: 'llama3.1',
    name: 'Llama 3.1 (8B)',
    provider: 'ollama',
    description: 'Fast local model from Meta',
    maxTokens: 128000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  'llama3.1:70b': {
    id: 'llama3.1:70b',
    name: 'Llama 3.1 (70B)',
    provider: 'ollama',
    description: 'Powerful local model from Meta',
    maxTokens: 128000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  'mistral': {
    id: 'mistral',
    name: 'Mistral 7B',
    provider: 'ollama',
    description: 'Efficient local model from Mistral AI',
    maxTokens: 32000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  'codellama': {
    id: 'codellama',
    name: 'Code Llama',
    provider: 'ollama',
    description: 'Specialized for code generation',
    maxTokens: 16000,
    costPer1kInput: 0,
    costPer1kOutput: 0,
  },
  'gemini-2.0-flash': {
    id: 'gemini-2.0-flash',
    name: 'Gemini 2.0 Flash',
    provider: 'google',
    description: 'Fast and efficient Google model',
    maxTokens: 1048576,
    costPer1kInput: 0.0001,
    costPer1kOutput: 0.0004,
  },
  'gemini-2.5-pro': {
    id: 'gemini-2.5-pro',
    name: 'Gemini 2.5 Pro',
    provider: 'google',
    description: 'Most capable Google model',
    maxTokens: 1048576,
    costPer1kInput: 0.00125,
    costPer1kOutput: 0.005,
  },
};

/**
 * Array of all available models for iteration
 */
export const MODEL_LIST = Object.values(MODELS);

/**
 * Get model information by ID
 *
 * @param modelId - The model identifier
 * @returns Model information or undefined if not found
 */
export const getModelInfo = (modelId: ModelId): ModelInfo | undefined =>
  MODELS[modelId];

/**
 * Get all models for a specific provider
 *
 * @param provider - The provider to filter by
 * @returns Array of models from that provider
 */
export const getModelsByProvider = (
  provider: 'openai' | 'anthropic' | 'ollama' | 'google'
): ModelInfo[] => MODEL_LIST.filter((model) => model.provider === provider);
