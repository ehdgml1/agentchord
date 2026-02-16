import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SecretsPanel } from './SecretsPanel';
import { api } from '../../services/api';

// Mock the API
vi.mock('../../services/api', () => ({
  api: {
    secrets: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

describe('SecretsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders secrets panel with title', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);

    render(<SecretsPanel />);

    expect(screen.getByText('Secrets')).toBeInTheDocument();
    expect(screen.getByText('Manage environment variables and API keys')).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    vi.mocked(api.secrets.list).mockImplementation(() => new Promise(() => {}));

    render(<SecretsPanel />);

    expect(screen.getByText('Loading secrets...')).toBeInTheDocument();
  });

  it('displays empty state when no secrets exist', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);

    render(<SecretsPanel />);

    await waitFor(() => {
      expect(screen.getByText('No secrets configured')).toBeInTheDocument();
    });
  });

  it('displays list of secrets', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue(['API_KEY', 'DATABASE_URL']);

    render(<SecretsPanel />);

    await waitFor(() => {
      expect(screen.getByText('API_KEY')).toBeInTheDocument();
      expect(screen.getByText('DATABASE_URL')).toBeInTheDocument();
    });
  });

  it('validates secret names with UPPER_SNAKE_CASE', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('No secrets configured')).toBeInTheDocument();
    });

    // Open add dialog
    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    // Type invalid name with special characters that aren't allowed
    const nameInput = screen.getByLabelText('Secret name');
    await user.type(nameInput, 'MY-KEY');  // Hyphens are not allowed, only underscores

    // Should show validation error
    await waitFor(
      () => {
        expect(screen.getByText('Use UPPER_SNAKE_CASE (e.g., MY_API_KEY)')).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it('auto-converts input to uppercase', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    const nameInput = screen.getByLabelText('Secret name') as HTMLInputElement;
    await user.type(nameInput, 'my_key');

    expect(nameInput.value).toBe('MY_KEY');
  });

  it('accepts valid UPPER_SNAKE_CASE names', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    const nameInput = screen.getByLabelText('Secret name');
    await user.type(nameInput, 'MY_API_KEY');

    // Should not show error
    await waitFor(() => {
      expect(screen.queryByText(/use upper_snake_case/i)).not.toBeInTheDocument();
    });
  });

  it('rejects names that do not start with uppercase letter', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    const nameInput = screen.getByLabelText('Secret name');
    await user.type(nameInput, '_MY_KEY');

    await waitFor(() => {
      expect(screen.getByText('Use UPPER_SNAKE_CASE (e.g., MY_API_KEY)')).toBeInTheDocument();
    });
  });

  it('prevents duplicate secret names', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue(['EXISTING_KEY']);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await waitFor(() => {
      expect(screen.getByText('EXISTING_KEY')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    const nameInput = screen.getByLabelText('Secret name');
    await user.type(nameInput, 'EXISTING_KEY');

    await waitFor(() => {
      expect(screen.getByText('Secret already exists')).toBeInTheDocument();
    });
  });

  it('creates secret with valid data', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    vi.mocked(api.secrets.create).mockResolvedValue();
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    await user.type(screen.getByLabelText('Secret name'), 'NEW_KEY');
    await user.type(screen.getByLabelText('Secret value'), 'secret123');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    await waitFor(() => {
      expect(api.secrets.create).toHaveBeenCalledWith('NEW_KEY', 'secret123');
    });
  });

  it('masks secret values in display', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue(['MY_SECRET']);

    render(<SecretsPanel />);

    await waitFor(() => {
      expect(screen.getByText('MY_SECRET')).toBeInTheDocument();
      expect(screen.getByText('****************')).toBeInTheDocument();
      expect(screen.getByText('Masked')).toBeInTheDocument();
    });
  });

  it('toggles password visibility in dialog', async () => {
    vi.mocked(api.secrets.list).mockResolvedValue([]);
    const user = userEvent.setup();

    render(<SecretsPanel />);

    await user.click(screen.getByRole('button', { name: /add new secret/i }));

    const valueInput = screen.getByLabelText('Secret value') as HTMLInputElement;
    await user.type(valueInput, 'mysecret');

    expect(valueInput.type).toBe('password');

    const toggleButton = screen.getByRole('button', { name: /show value/i });
    await user.click(toggleButton);

    expect(valueInput.type).toBe('text');
  });
});
