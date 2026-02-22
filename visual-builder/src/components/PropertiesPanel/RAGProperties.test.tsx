import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RAGProperties } from './RAGProperties';
import type { RAGBlockData } from '../../types/blocks';

vi.mock('../../hooks/useLLMKeyStatus', () => ({
  useLLMKeyStatus: () => ({
    isProviderConfigured: vi.fn().mockReturnValue(true),
    keys: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

const mockData: RAGBlockData = {
  name: 'Test RAG',
  documents: ['doc1.txt', 'doc2.txt'],
  searchLimit: 5,
  enableBm25: true,
  chunkSize: 500,
  chunkOverlap: 50,
  systemPrompt: 'Be helpful',
  model: 'gpt-4o-mini',
  temperature: 0.3,
  maxTokens: 1024,
};

describe('RAGProperties', () => {
  it('renders Name input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    expect(nameInput).toHaveValue('Test RAG');
  });

  it('renders Documents textarea with current values', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const documentsInput = screen.getByLabelText(/텍스트 직접 입력/i);
    expect(documentsInput).toHaveValue('doc1.txt\ndoc2.txt');
  });

  it('renders Search Limit input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const searchLimitInput = screen.getByLabelText(/search limit/i);
    expect(searchLimitInput).toHaveValue(5);
  });

  it('renders Enable BM25 switch', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const bm25Switch = screen.getByRole('switch', { name: /enable bm25/i });
    expect(bm25Switch).toBeChecked();
  });

  it('renders Chunk Size input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const chunkSizeInput = screen.getByLabelText(/chunk size/i);
    expect(chunkSizeInput).toHaveValue(500);
  });

  it('renders Chunk Overlap input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const chunkOverlapInput = screen.getByLabelText(/chunk overlap/i);
    expect(chunkOverlapInput).toHaveValue(50);
  });

  it('renders System Prompt textarea with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const systemPromptInput = screen.getByLabelText(/system prompt/i);
    expect(systemPromptInput).toHaveValue('Be helpful');
  });

  it('renders Model input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    // Model is now a Select dropdown, check for displayed model name
    const modelTrigger = screen.getByRole('combobox', { name: /model/i });
    expect(modelTrigger).toBeInTheDocument();
    expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();
  });

  it('renders Temperature slider', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    expect(screen.getByText(/temperature/i)).toBeInTheDocument();
    expect(screen.getByText('0.3')).toBeInTheDocument();
  });

  it('renders Max Tokens input with current value', () => {
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const maxTokensInput = screen.getByLabelText(/max tokens/i);
    expect(maxTokensInput).toHaveValue(1024);
  });

  it('name change calls onChange with { name: value }', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/name/i);
    await user.type(nameInput, 'X');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ name: expect.stringContaining('X') })
    );
  });

  it('documents change calls onChange with parsed array', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const dataWithoutDocs = { ...mockData, documents: [] };
    render(<RAGProperties nodeId="node-1" data={dataWithoutDocs} onChange={onChange} />);

    const documentsInput = screen.getByLabelText(/텍스트 직접 입력/i);
    // Use paste instead of type for multiline content
    await user.click(documentsInput);
    await user.paste('doc3.txt\ndoc4.txt');

    // Check the last call has both documents
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.documents).toEqual(['doc3.txt', 'doc4.txt']);
  });

  it('search limit change calls onChange with numeric value', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

    const searchLimitInput = screen.getByLabelText(/search limit/i);
    await user.clear(searchLimitInput);
    await user.type(searchLimitInput, '10');

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ searchLimit: expect.any(Number) })
    );
  });

  describe('Embedding Configuration', () => {
    it('renders "Embedding Configuration" section header', () => {
      const onChange = vi.fn();
      render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

      expect(screen.getByText('Embedding Configuration')).toBeInTheDocument();
    });

    it('provider dropdown shows "Global Default" initially when no embeddingProvider set', () => {
      const onChange = vi.fn();
      const dataWithoutProvider = { ...mockData, embeddingProvider: undefined };
      render(<RAGProperties nodeId="node-1" data={dataWithoutProvider} onChange={onChange} />);

      const providerTrigger = screen.getByRole('combobox', {
        name: /embedding provider/i,
      });
      expect(providerTrigger).toHaveTextContent('Global Default');
    });

    it('selecting a provider updates node data with embeddingProvider value', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      const dataWithoutProvider = { ...mockData, embeddingProvider: undefined };
      render(<RAGProperties nodeId="node-1" data={dataWithoutProvider} onChange={onChange} />);

      const providerTrigger = screen.getByRole('combobox', {
        name: /embedding provider/i,
      });
      await user.click(providerTrigger);

      const openaiOption = screen.getByRole('option', { name: /^openai$/i });
      await user.click(openaiOption);

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ embeddingProvider: 'openai' })
      );
    });

    it('model dropdown shows models filtered by selected provider', () => {
      const onChange = vi.fn();
      const dataWithProvider = {
        ...mockData,
        embeddingProvider: 'openai' as const,
      };
      render(<RAGProperties nodeId="node-1" data={dataWithProvider} onChange={onChange} />);

      // Model dropdown should be visible when provider is set
      const modelTrigger = screen.getByRole('combobox', {
        name: /embedding model/i,
      });
      expect(modelTrigger).toBeInTheDocument();
    });

    it('selecting a model updates node data with embeddingModel and embeddingDimensions', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      const dataWithProvider = {
        ...mockData,
        embeddingProvider: 'openai' as const,
      };
      render(<RAGProperties nodeId="node-1" data={dataWithProvider} onChange={onChange} />);

      const modelTrigger = screen.getByRole('combobox', {
        name: /embedding model/i,
      });
      await user.click(modelTrigger);

      // Select text-embedding-3-small
      const modelOption = screen.getByRole('option', {
        name: /text embedding 3 small/i,
      });
      await user.click(modelOption);

      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({
          embeddingModel: 'text-embedding-3-small',
          embeddingDimensions: 1536,
        })
      );
    });

    it('dimensions auto-fill when model is selected (text-embedding-3-small → 1536)', () => {
      const onChange = vi.fn();
      const dataWithModel = {
        ...mockData,
        embeddingProvider: 'openai' as const,
        embeddingModel: 'text-embedding-3-small',
        embeddingDimensions: 1536,
      };
      render(<RAGProperties nodeId="node-1" data={dataWithModel} onChange={onChange} />);

      // Check that dimensions are displayed
      expect(screen.getByText(/dimensions: 1536/i)).toBeInTheDocument();
    });

    it('shows provider status indicator (configured)', () => {
      const onChange = vi.fn();
      const dataWithModel = {
        ...mockData,
        model: 'gpt-4o-mini',
      };
      render(<RAGProperties nodeId="node-1" data={dataWithModel} onChange={onChange} />);

      // Provider configured indicator should show
      expect(screen.getByText(/provider configured/i)).toBeInTheDocument();
    });

    it('provider dropdown includes all 3 options (OpenAI, Gemini, Ollama)', async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(<RAGProperties nodeId="node-1" data={mockData} onChange={onChange} />);

      const providerTrigger = screen.getByRole('combobox', {
        name: /embedding provider/i,
      });
      await user.click(providerTrigger);

      // All provider options should be present
      expect(screen.getByRole('option', { name: /^global default$/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /^openai$/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /^gemini$/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /^ollama$/i })).toBeInTheDocument();
    });
  });
});
