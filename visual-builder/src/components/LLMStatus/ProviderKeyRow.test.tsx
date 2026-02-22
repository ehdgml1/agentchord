import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProviderKeyRow } from './ProviderKeyRow';
import { api } from '../../services/api';
import type { LLMKeyStatus } from '../../services/api';

vi.mock('../../services/api', () => ({
  api: {
    llm: {
      validateKey: vi.fn(),
      setKey: vi.fn(),
      deleteKey: vi.fn(),
    },
  },
}));

const mockValidateKey = vi.mocked(api.llm.validateKey);
const mockSetKey = vi.mocked(api.llm.setKey);
const mockDeleteKey = vi.mocked(api.llm.deleteKey);

describe('ProviderKeyRow', () => {
  const mockOnUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders provider name correctly', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    expect(screen.getByText('OpenAI')).toBeInTheDocument();
  });

  it('shows green dot when provider is configured (hasUserKey)', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: true,
      hasServerKey: false,
      configured: true,
    };

    const { container } = render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const dot = container.querySelector('.bg-green-500');
    expect(dot).toBeInTheDocument();
  });

  it('shows green dot when provider is configured (hasServerKey)', () => {
    const status: LLMKeyStatus = {
      provider: 'anthropic',
      hasUserKey: false,
      hasServerKey: true,
      configured: true,
    };

    const { container } = render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const dot = container.querySelector('.bg-green-500');
    expect(dot).toBeInTheDocument();
  });

  it('shows gray dot when provider is not configured', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    const { container } = render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const dot = container.querySelector('.bg-gray-300');
    expect(dot).toBeInTheDocument();
  });

  it('shows "Server" badge when hasServerKey is true', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: true,
      configured: true,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    expect(screen.getByText('Server')).toBeInTheDocument();
  });

  it('shows "User" badge when hasUserKey is true', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: true,
      hasServerKey: false,
      configured: true,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    expect(screen.getByText('User')).toBeInTheDocument();
  });

  it('password input starts hidden (type="password")', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter API key...') as HTMLInputElement;
    expect(input.type).toBe('password');
  });

  it('eye toggle switches input between password and text type', () => {
    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter API key...') as HTMLInputElement;
    const eyeButton = input.parentElement?.querySelector('button');

    expect(input.type).toBe('password');

    fireEvent.click(eyeButton!);
    expect(input.type).toBe('text');

    fireEvent.click(eyeButton!);
    expect(input.type).toBe('password');
  });

  it('validate button calls api.llm.validateKey and shows green check on success', async () => {
    mockValidateKey.mockResolvedValue({ valid: true });

    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter API key...');
    fireEvent.change(input, { target: { value: 'sk-test-key-123' } });

    const validateButton = screen.getByText('Test');
    fireEvent.click(validateButton);

    await waitFor(() => {
      expect(mockValidateKey).toHaveBeenCalledWith('openai', 'sk-test-key-123');
    });

    // Check for green check icon (Check component from lucide-react)
    await waitFor(() => {
      const checkIcon = validateButton.querySelector('svg');
      expect(checkIcon).toBeInTheDocument();
      expect(checkIcon).toHaveClass('text-green-500');
    });
  });

  it('validate button shows red X on failure', async () => {
    mockValidateKey.mockResolvedValue({ valid: false, error: 'Invalid API key' });

    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter API key...');
    fireEvent.change(input, { target: { value: 'invalid-key' } });

    const validateButton = screen.getByText('Test');
    fireEvent.click(validateButton);

    await waitFor(() => {
      expect(mockValidateKey).toHaveBeenCalledWith('openai', 'invalid-key');
    });

    // Check for red X icon
    await waitFor(() => {
      const xIcon = validateButton.querySelector('svg');
      expect(xIcon).toBeInTheDocument();
      expect(xIcon).toHaveClass('text-red-500');
    });

    // Check for error message
    expect(screen.getByText('Invalid API key')).toBeInTheDocument();
  });

  it('save button calls api.llm.setKey and triggers onUpdate callback', async () => {
    mockSetKey.mockResolvedValue();

    const status: LLMKeyStatus = {
      provider: 'anthropic',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter API key...');
    fireEvent.change(input, { target: { value: 'sk-ant-key-123' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockSetKey).toHaveBeenCalledWith('anthropic', 'sk-ant-key-123');
    });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledOnce();
    });
  });

  it('delete button calls api.llm.deleteKey and triggers onUpdate callback', async () => {
    mockDeleteKey.mockResolvedValue();

    const status: LLMKeyStatus = {
      provider: 'openai',
      hasUserKey: true,
      hasServerKey: false,
      configured: true,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    // Find delete button (Trash2 icon)
    const deleteButton = screen.getByTitle('Delete key');
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockDeleteKey).toHaveBeenCalledWith('openai');
    });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledOnce();
    });
  });

  it('ollama provider shows URL placeholder instead of "API Key"', () => {
    const status: LLMKeyStatus = {
      provider: 'ollama',
      hasUserKey: false,
      hasServerKey: false,
      configured: false,
    };

    render(<ProviderKeyRow status={status} onUpdate={mockOnUpdate} />);

    expect(screen.getByPlaceholderText('http://localhost:11434')).toBeInTheDocument();
  });
});
