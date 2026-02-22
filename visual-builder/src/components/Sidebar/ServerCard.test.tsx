import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ServerCard } from './ServerCard';
import type { MCPServerInfo } from '../../data/mcpCatalog';

// Mock UI components
vi.mock('../ui', () => ({
  Button: ({ children, onClick, disabled, size, className }: any) => (
    <button onClick={onClick} disabled={disabled} data-size={size} className={className}>
      {children}
    </button>
  ),
  Badge: ({ children, variant, className }: any) => (
    <span data-variant={variant} className={className}>
      {children}
    </span>
  ),
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children, className }: any) => (
    <div data-testid="card-title" className={className}>
      {children}
    </div>
  ),
  CardDescription: ({ children, className }: any) => (
    <div data-testid="card-description" className={className}>
      {children}
    </div>
  ),
  CardContent: ({ children }: any) => <div data-testid="card-content">{children}</div>,
  CardFooter: ({ children }: any) => <div data-testid="card-footer">{children}</div>,
  Input: ({ type, placeholder, value, onChange, className }: any) => (
    <input type={type} placeholder={placeholder} value={value} onChange={onChange} className={className} />
  ),
}));

describe('ServerCard', () => {
  const mockOnInstall = vi.fn();

  const mockServer: MCPServerInfo = {
    id: 'test-server',
    name: 'Test Server',
    description: 'A test MCP server',
    category: 'Development',
    stars: 42,
    command: 'npx',
    args: ['test-server'],
    official: false,
  };

  it('renders server name', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('Test Server')).toBeInTheDocument();
  });

  it('renders server description', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('A test MCP server')).toBeInTheDocument();
  });

  it('displays category badge', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('Development')).toBeInTheDocument();
  });

  it('displays star count', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('shows official badge for official servers', () => {
    const officialServer = { ...mockServer, official: true };
    render(<ServerCard server={officialServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('Official')).toBeInTheDocument();
  });

  it('does not show official badge for non-official servers', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.queryByText('Official')).not.toBeInTheDocument();
  });

  it('shows install button when not installed', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    const installButton = screen.getByText('Install');
    expect(installButton).toBeInTheDocument();
    expect(installButton).not.toBeDisabled();
  });

  it('shows installed state when installed', () => {
    render(<ServerCard server={mockServer} isInstalled={true} onInstall={mockOnInstall} />);

    const installedButton = screen.getByText('Installed');
    expect(installedButton).toBeInTheDocument();
    expect(installedButton).toBeDisabled();
  });

  it('calls onInstall when install button is clicked', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    const installButton = screen.getByText('Install');
    fireEvent.click(installButton);

    expect(mockOnInstall).toHaveBeenCalledWith(mockServer, {});
  });

  it('displays API key input fields when secrets required', () => {
    const serverWithSecrets = {
      ...mockServer,
      requiredSecrets: ['API_KEY', 'SECRET_TOKEN'],
    };
    render(<ServerCard server={serverWithSecrets} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByText('API Keys')).toBeInTheDocument();
    expect(screen.getByText('API_KEY')).toBeInTheDocument();
    expect(screen.getByText('SECRET_TOKEN')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter API_KEY')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter SECRET_TOKEN')).toBeInTheDocument();
  });

  it('does not display API key section when no secrets required', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.queryByText('API Keys')).not.toBeInTheDocument();
  });

  it('disables install button when required secrets are not filled', () => {
    const serverWithSecrets = {
      ...mockServer,
      requiredSecrets: ['API_KEY'],
    };
    render(<ServerCard server={serverWithSecrets} isInstalled={false} onInstall={mockOnInstall} />);

    const installButton = screen.getByText('Install');
    expect(installButton).toBeDisabled();
  });

  it('renders card structure', () => {
    render(<ServerCard server={mockServer} isInstalled={false} onInstall={mockOnInstall} />);

    expect(screen.getByTestId('card')).toBeInTheDocument();
    expect(screen.getByTestId('card-header')).toBeInTheDocument();
    expect(screen.getByTestId('card-footer')).toBeInTheDocument();
  });
});
