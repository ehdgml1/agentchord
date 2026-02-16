import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

// Hoisted mock for useAuthStore with persist API
const { mockUseAuthStore } = vi.hoisted(() => {
  const fn = vi.fn() as any;
  fn.persist = {
    onFinishHydration: vi.fn(() => vi.fn()),
    hasHydrated: vi.fn(() => true),
  };
  return { mockUseAuthStore: fn };
});

vi.mock('./stores/authStore', () => ({
  useAuthStore: mockUseAuthStore,
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    BrowserRouter: ({ children }: any) => <div data-testid="browser-router">{children}</div>,
    Routes: ({ children }: any) => <div data-testid="routes">{children}</div>,
    Route: ({ element }: any) => <div data-testid="route">{element}</div>,
    Navigate: () => <div data-testid="navigate">Navigate</div>,
  };
});

// Mock sonner Toaster
vi.mock('sonner', () => ({
  Toaster: ({ position, richColors }: any) => (
    <div data-testid="toaster" data-position={position} data-rich-colors={richColors} />
  ),
}));

// Mock pages and components
vi.mock('./pages/WorkflowList', () => ({
  WorkflowList: () => <div data-testid="workflow-list">WorkflowList</div>,
}));
vi.mock('./pages/WorkflowEditor', () => ({
  WorkflowEditor: () => <div data-testid="workflow-editor">WorkflowEditor</div>,
}));
vi.mock('./components/Auth/AuthPage', () => ({
  AuthPage: () => <div data-testid="auth-page">AuthPage</div>,
}));
vi.mock('./components/Admin/AdminLayout', () => ({
  AdminLayout: () => <div data-testid="admin-layout">AdminLayout</div>,
}));

function setupMock(isAuthenticated: boolean, role = 'user') {
  mockUseAuthStore.mockImplementation((selector?: any) => {
    if (typeof selector === 'function') {
      return selector({
        isAuthenticated,
        user: isAuthenticated ? { role } : null,
      });
    }
    return isAuthenticated;
  });
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthStore.persist.hasHydrated.mockReturnValue(true);
    mockUseAuthStore.persist.onFinishHydration.mockReturnValue(vi.fn());
  });

  it('renders without crashing when not authenticated', () => {
    setupMock(false);
    const { container } = render(<App />);
    expect(container).toBeInTheDocument();
  });

  it('shows AuthPage when not authenticated', async () => {
    setupMock(false);
    render(<App />);
    expect(await screen.findByTestId('auth-page')).toBeInTheDocument();
  });

  it('shows Toaster when not authenticated', () => {
    setupMock(false);
    render(<App />);
    const toaster = screen.getByTestId('toaster');
    expect(toaster).toBeInTheDocument();
    expect(toaster).toHaveAttribute('data-position', 'bottom-right');
    expect(toaster).toHaveAttribute('data-rich-colors', 'true');
  });

  it('does not show routes when not authenticated', () => {
    setupMock(false);
    render(<App />);
    expect(screen.queryByTestId('routes')).not.toBeInTheDocument();
  });

  it('shows routes when authenticated', async () => {
    setupMock(true);
    render(<App />);
    expect(await screen.findByTestId('routes')).toBeInTheDocument();
  });

  it('does not show AuthPage when authenticated', async () => {
    setupMock(true);
    render(<App />);
    await screen.findByTestId('routes');
    expect(screen.queryByTestId('auth-page')).not.toBeInTheDocument();
  });

  it('shows Toaster when authenticated', () => {
    setupMock(true);
    render(<App />);
    const toaster = screen.getByTestId('toaster');
    expect(toaster).toBeInTheDocument();
  });

  it('wraps app with BrowserRouter', () => {
    setupMock(false);
    render(<App />);
    expect(screen.getByTestId('browser-router')).toBeInTheDocument();
  });

  it('shows loading spinner before hydration', () => {
    mockUseAuthStore.persist.hasHydrated.mockReturnValue(false);
    setupMock(false);
    const { container } = render(<App />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    expect(screen.queryByTestId('browser-router')).not.toBeInTheDocument();
  });
});
