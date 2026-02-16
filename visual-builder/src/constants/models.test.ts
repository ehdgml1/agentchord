import { describe, it, expect } from 'vitest';
import {
  MODELS,
  MODEL_LIST,
  getModelInfo,
  getModelsByProvider,
} from './models';

describe('models constants', () => {
  describe('MODELS', () => {
    it('should have 15 entries', () => {
      expect(Object.keys(MODELS)).toHaveLength(15);
    });

    it('should include gpt-4o', () => {
      expect(MODELS['gpt-4o']).toBeDefined();
    });

    it('should include gpt-4o-mini', () => {
      expect(MODELS['gpt-4o-mini']).toBeDefined();
    });

    it('should include gpt-4.1', () => {
      expect(MODELS['gpt-4.1']).toBeDefined();
    });

    it('should include gpt-4.1-mini', () => {
      expect(MODELS['gpt-4.1-mini']).toBeDefined();
    });

    it('should include o1', () => {
      expect(MODELS['o1']).toBeDefined();
    });

    it('should include o1-mini', () => {
      expect(MODELS['o1-mini']).toBeDefined();
    });

    it('should include claude-sonnet-4-5-20250929', () => {
      expect(MODELS['claude-sonnet-4-5-20250929']).toBeDefined();
    });

    it('should include claude-haiku-4-5-20251001', () => {
      expect(MODELS['claude-haiku-4-5-20251001']).toBeDefined();
    });

    it('should include claude-opus-4-6', () => {
      expect(MODELS['claude-opus-4-6']).toBeDefined();
    });

    it('should have required fields in each model', () => {
      Object.values(MODELS).forEach((model) => {
        expect(model).toHaveProperty('id');
        expect(model).toHaveProperty('name');
        expect(model).toHaveProperty('provider');
        expect(typeof model.id).toBe('string');
        expect(typeof model.name).toBe('string');
        expect(['openai', 'anthropic', 'ollama', 'google']).toContain(model.provider);
      });
    });
  });

  describe('MODEL_LIST', () => {
    it('should have 15 entries', () => {
      expect(MODEL_LIST).toHaveLength(15);
    });
  });

  describe('getModelInfo', () => {
    it('should return correct model for gpt-4o', () => {
      const model = getModelInfo('gpt-4o');
      expect(model).toBeDefined();
      expect(model?.id).toBe('gpt-4o');
      expect(model?.name).toBe('GPT-4o');
      expect(model?.provider).toBe('openai');
    });

    it('should return undefined for invalid id', () => {
      const model = getModelInfo('invalid-model' as any);
      expect(model).toBeUndefined();
    });
  });

  describe('getModelsByProvider', () => {
    it('should return 6 models for openai', () => {
      const openaiModels = getModelsByProvider('openai');
      expect(openaiModels).toHaveLength(6);
      expect(openaiModels.every((m) => m.provider === 'openai')).toBe(true);
    });

    it('should return 3 models for anthropic', () => {
      const anthropicModels = getModelsByProvider('anthropic');
      expect(anthropicModels).toHaveLength(3);
      expect(anthropicModels.every((m) => m.provider === 'anthropic')).toBe(
        true
      );
    });

    it('should return 4 models for ollama', () => {
      const ollamaModels = getModelsByProvider('ollama');
      expect(ollamaModels).toHaveLength(4);
      expect(ollamaModels.every((m) => m.provider === 'ollama')).toBe(true);
    });

    it('should return 2 models for google', () => {
      const googleModels = getModelsByProvider('google');
      expect(googleModels).toHaveLength(2);
      expect(googleModels.every((m) => m.provider === 'google')).toBe(true);
    });

    it('should have openai provider for OpenAI models', () => {
      const gpt4o = MODELS['gpt-4o'];
      const gpt4oMini = MODELS['gpt-4o-mini'];
      const gpt41 = MODELS['gpt-4.1'];
      const gpt41Mini = MODELS['gpt-4.1-mini'];
      expect(gpt4o.provider).toBe('openai');
      expect(gpt4oMini.provider).toBe('openai');
      expect(gpt41.provider).toBe('openai');
      expect(gpt41Mini.provider).toBe('openai');
    });

    it('should have anthropic provider for Anthropic models', () => {
      const claudeSonnet = MODELS['claude-sonnet-4-5-20250929'];
      const claudeHaiku = MODELS['claude-haiku-4-5-20251001'];
      const claudeOpus = MODELS['claude-opus-4-6'];
      expect(claudeSonnet.provider).toBe('anthropic');
      expect(claudeHaiku.provider).toBe('anthropic');
      expect(claudeOpus.provider).toBe('anthropic');
    });
  });
});
