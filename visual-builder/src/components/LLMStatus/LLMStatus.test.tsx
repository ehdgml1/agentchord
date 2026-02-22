import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { LLMStatus } from './LLMStatus';
import { api } from '../../services/api';

vi.mock('../../services/api', () => ({
  api: {
    llm: {
      listProviders: vi.fn(),
      getKeyStatus: vi.fn(),
    },
  },
}));

const mockListProviders = vi.mocked(api.llm.listProviders);
const mockGetKeyStatus = vi.mocked(api.llm.getKeyStatus);

describe('LLMStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with provider count when both configured', async () => {
    mockListProviders.mockResolvedValue({
      providers: [
        { name: 'openai', configured: true, models: ['gpt-4o', 'gpt-4o-mini'] },
        { name: 'anthropic', configured: true, models: ['claude-sonnet-4-5-20250929'] },
      ],
      defaultModel: 'gpt-4o',
    });
    mockGetKeyStatus.mockResolvedValue([
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'anthropic', hasUserKey: true, hasServerKey: false, configured: true },
    ]);

    render(<LLMStatus />);

    await waitFor(() => {
      expect(screen.getByText('2/2 LLM')).toBeInTheDocument();
    });
  });

  it('renders with partial provider count', async () => {
    mockListProviders.mockResolvedValue({
      providers: [
        { name: 'openai', configured: true, models: ['gpt-4o'] },
        { name: 'anthropic', configured: false, models: [] },
      ],
      defaultModel: 'gpt-4o',
    });
    mockGetKeyStatus.mockResolvedValue([
      { provider: 'openai', hasUserKey: true, hasServerKey: false, configured: true },
      { provider: 'anthropic', hasUserKey: false, hasServerKey: false, configured: false },
    ]);

    render(<LLMStatus />);

    await waitFor(() => {
      expect(screen.getByText('1/2 LLM')).toBeInTheDocument();
    });
  });

  it('renders with zero configured providers', async () => {
    mockListProviders.mockResolvedValue({
      providers: [
        { name: 'openai', configured: false, models: [] },
        { name: 'anthropic', configured: false, models: [] },
      ],
      defaultModel: 'gpt-4o-mini',
    });
    mockGetKeyStatus.mockResolvedValue([
      { provider: 'openai', hasUserKey: false, hasServerKey: false, configured: false },
      { provider: 'anthropic', hasUserKey: false, hasServerKey: false, configured: false },
    ]);

    render(<LLMStatus />);

    await waitFor(() => {
      expect(screen.getByText('0/2 LLM')).toBeInTheDocument();
    });
  });

  it('renders error state when API fails', async () => {
    mockListProviders.mockRejectedValue(new Error('Network error'));
    mockGetKeyStatus.mockRejectedValue(new Error('Network error'));

    render(<LLMStatus />);

    await waitFor(() => {
      expect(screen.getByText('LLM Error')).toBeInTheDocument();
    });
  });

  it('calls listProviders on mount', async () => {
    mockListProviders.mockResolvedValue({
      providers: [],
      defaultModel: '',
    });
    mockGetKeyStatus.mockResolvedValue([]);

    render(<LLMStatus />);

    await waitFor(() => {
      expect(mockListProviders).toHaveBeenCalledOnce();
      expect(mockGetKeyStatus).toHaveBeenCalledOnce();
    });
  });

  it('applies custom className', async () => {
    mockListProviders.mockResolvedValue({
      providers: [],
      defaultModel: '',
    });
    mockGetKeyStatus.mockResolvedValue([]);

    const { container } = render(<LLMStatus className="custom-class" />);

    await waitFor(() => {
      const button = container.querySelector('button');
      expect(button).toHaveClass('custom-class');
    });
  });
});
